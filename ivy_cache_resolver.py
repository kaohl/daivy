#!/bin/env python3

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

class ResolverModule:
    _resources = Path('ivy-daivy-resolver-cache')

    # Add specified module to 'daivy' resolver.
    def add_module(module):
        tree = ET.ElementTree(module.load_xml())
        tree.write(ResolverModule(module.id, clear = True).ivy_xml_path)
    
    def __init__(self, id, clear):
        if id is None or len(id.org) == 0 or len(id.mod) == 0 or len(id.rev) == 0:
            raise ValueError('Bad module ID', id)
        
        self.path         = ResolverModule._resources / id.org / id.mod
        self.ivy_xml_path = self.path / ('-'.join(['ivy', id.rev]) + '.xml')

        if clear:
            self.clear_location()

    def clear_location(self):
        if self.path.exists():
            shutil.rmtree(self.path)
        self.path.mkdir(parents = True)

# Use this function to install a locally provided
# module definition via the ivy-daivy resolver.
# This will override the remote definition due
# to how the resolver chain is defined in the
# local ivy settings.
def install_local_module(module):
    ResolverModule.add_module(module)

class ID:
    def __init__(self, org, mod, rev):
        self.org    = org
        self.mod    = mod
        self.rev    = rev
        self._key   = None
        self._coord = None

    def key(self):
        if self._key is None:
            self._key = (self.org, self.mod, self.rev)
        return self._key

    def coord(self):
        if self._coord is None:
            self._coord = ":".join(self.key())
        return self._coord

    def from_coord(coord):
        parts = coord.split(":")
        org   = parts[0]
        mod   = parts[1]
        rev   = parts[2]
        return ID(org, mod, rev)

class IvyXMLQueries:

    def id(root):
        info = root.find('info')
        return ID(
            info.get('organisation'),
            info.get('module'),
            info.get('revision')
        )

    def artifacts(root):
        id = IvyXMLQueries.id(root)
        xs = root.findall('.//artifact')
        if xs is None or len(xs) == 0:
            return [ '-'.join([id.mod, id.rev]) + '.jar' ]
        result = []
        for x in xs:
            name = x.get('name') if 'name' in x.attrib else id.mod
            ext  = x.get('ext') if 'ext' in x.attrib else (x.get('type') if 'type' in x.attrib else '.jar')
            result.append('-'.join([name, id.rev]) + '.' + ext)
        return result

class XMLLoader:
    def __init__(self, root):
        self._root = root

    def load_xml(self):
        raise ValueError('unimplemented')

class XMLFileLoader(XMLLoader):
    def __init__(self, path, root = None):
        super().__init__(root)
        self.path  = path

    def load_xml(self):
        if self._root is None:
            self._root = ET.parse(self.path).getroot()
        return self._root

class XMLTextLoader(XMLLoader):
    def __init__(self, text, root):
        super().__init__(root)
        self.text  = text

    def load_xml(self):
        if self._root is None:
            self._root = ET.fromstring(self.text)
        return self._root

class Module:
    def __init__(self, cache, id, xml_loader):
        self.id          = id
        self._cache      = cache
        self._xml_loader = xml_loader

    def register(self, cache):
        if not self._cache is None:
            raise ValueError('The module is already registered in cache', self._cache)
        self._cache = cache

    def load_xml(self):
        return self._xml_loader.load_xml()

    # Resolve dependencies for specified configurations using ivy.
    # Return a list of paths to resolved artifacts in the ivy cache.
    def resolve_dependencies(self, confs = ['default']):
        return self._cache.resolve_dependencies(self.id, confs)

    # Return list of IDs of declared dependencies.
    def declared_dependencies(self):
        dependencies_xml = self.load_xml().find('dependencies')
        dependencies     = []
        if dependencies_xml is not None:
            for dependency_xml in dependencies_xml.findall('dependency'):
                d_org     = dependency_xml.get('org')
                d_name    = dependency_xml.get('name')
                d_rev     = dependency_xml.get('rev')
                d_id      = ID(d_org, d_name, d_rev)
                dependencies.append(d_id)
        return dependencies

    def blueprint(self):
        return ModuleBlueprint.from_module(self)

class ModuleBlueprint:
    def __init__(self):
        self._id         = None
        self._cnfs       = []
        self._deps       = []
        self._cnfsattrib = {}
        self._depsattrib = {}
        self._artifacts  = []
        self._cnfs_element = None

    def artifact(self, attrib):
        if attrib is None:
            self._artifacts = None
        else:
            self._artifacts.append(attrib)

    def attrib(self, cnfs = {}, deps = {}):
        self._cnfsattrib = cnfs
        self._depsattrib = deps
        return self

    def confsattrib(self, attrib):
        self._cnfsattrib = attrib
        return self

    def depsattrib(self, attrib):
        self._depsattrib = attrib
        return self

    def conf(self, attrib):
        self._cnfs.append(attrib)
        return self

    def dep(self, id, attrib):
        if not id is None:
            attrib['org']  = id.org
            attrib['name'] = id.mod
            attrib['rev']  = id.rev
        self._deps.append(attrib)
        return self

    def id(self, id):
        self._id = id
        return self

    def build(self):
        id = self._id
        m = ET.Element('ivy-module', { 'version' : '2.0' })
        i = ET.Element('info', {
            'organisation' : id.org,
            'module'       : id.mod,
            'revision'     : id.rev
        })
        cs = ET.Element('configurations', self._cnfsattrib)
        ps = ET.Element('publications', {})
        ds = ET.Element('dependencies', self._depsattrib)

        for c in self._cnfs:
            ET.SubElement(cs, 'conf', c)

        for d in self._deps:
            ET.SubElement(ds, 'dependency', d)

        m.append(i)
        m.append(cs)
        if self._artifacts is None:
            m.append(ps) # Default to empty element to remove default artifact.
        else:
            if len(self._artifacts) > 0:
                for art_attrib in self._artifacts:
                    ps.append(ET.Element('artifact', art_attrib))
                m.append(ps)
            else:
                # Don't add 'publications' to use default artifact
                # which is a jar named after fields in module info.
                pass
        m.append(ds)

        # Skip to/fromstring by providing module xml root.
        # A text representation can always be produced from the tree later if needed.
        module = Module(None, id, XMLTextLoader(None, m))

        return module

    # Create a module blueprint based on an existing
    # module definition found in the cache.
    def from_module(module):
        raise ValueError('unimplemented')

class CacheConstants:
    _default_cache_name = 'ivy-cache'
    _default_cache      = None

class Cache:
    # Private constructor.
    # Use Cache.create_cache(<name>) instead.
    def __init__(self, cachepath = CacheConstants._default_cache_name):
        self._cachepath = cachepath
        self._modules   = dict()
        self._dependency_resolver_cache = dict()

    def create_cache(name = None):
        is_default_cache_name = name == CacheConstants._default_cache_name
        if CacheConstants._default_cache is None and is_default_cache_name:
            CacheConstants._default_cache = Cache(CacheConstants._default_cache_name)
        return CacheConstants._default_cache if is_default_cache_name else Cache(name)

    def register(self, module, override = False):
        id = module.id
        if not override and id.coord() in self._modules:
            raise ValueError(
                'A definition of module',
                id.coord(),
                'is already cached.',
                'Please set the override flag to override the existing definition, if intended.'
            )
        module.register(self)
        self._modules[id.coord()] = module

    def resolve_ivy_xml_from_coord(self, coord):
        return self.resolve_ivy_xml(ID.from_coord(coord))

    def resolve_ivy_xml(self, id):
        if self._cachepath is None:
            # Note: In-memory caches are mostly intended for testing purposes.
            raise ValueError(
                'In-memory cache.',
                'Cannot resolve ivy xml for module "' + id.coord() + '".',
                'Please declare all modules before attempting to resolve dependencies.'
            )

        ivy_xml = Path(os.path.sep.join([
            self._cachepath,
            id.org,
            id.mod,
            "-".join(["ivy", id.rev + ".xml"])
        ]))
        if not ivy_xml.exists():
            cmd = " ".join([
                "java",
                "-jar",
                "tools/ivy-2.5.2.jar",
                "-warn",
                "-settings",
                "settings/ivysettings.xml", # Use custom settings to add the local 'daivy' resolver.
                "-cache",
                self._cachepath,
                "-dependency",
                id.org,
                id.mod,
                id.rev
            ])
            subprocess.run(cmd, shell = True)
        return ivy_xml

    def location(self, id):
        return self.resolve_ivy_xml(id).parent

    # Return list of paths to resolved jar files.
    # NOTE: It is possible to resolve the 'ivy.xml'
    #       file from the artifact paths, which can
    #       be used to resolve module IDs of dependencies
    #       for specific configurations.
    def resolve_dependencies(self, id, confs):
        cache_id = ';'.join([id.coord()] + confs)
        if cache_id in self._dependency_resolver_cache:
            return self._dependency_resolver_cache[cache_id]
        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
            fp.close()
            cmd = " ".join([
                "java",
                "-jar",
                "tools/ivy-2.5.2.jar",
                "-warn",
                "-settings",
                "settings/ivysettings.xml", # Use custom settings to add the local 'daivy' resolver.
                "-cache",
                self._cachepath,
                "-types",
                "jar",
                "bundle", # TODO: Add types as parameter (need bundle to get HdrHistogram)
                "-dependency",
                id.org,
                id.mod,
                id.rev,
                "-cachepath",
                fp.name,
                "-confs",
                " ".join(confs)
            ])
            subprocess.run(cmd, shell = True)

            with open(fp.name, 'r') as f:
                lines = f.readlines()
                if len(lines) < 2:
                    line  = lines[0] if len(lines) > 0 else ""
                    value = line.strip().split(':')
                    self._dependency_resolver_cache[cache_id] = value
                    print(" --- Resolved dependencies --- [", id.coord(), "] (", confs, ")")
                    for d in value:
                        print(" ", d)
                    print("-----------------------------------")
                    return value
                else:
                    raise ValueError('Unexpected classpath file. Ivy dependency resolution may have failed. Lines = ', lines)

    def resolve(self, id):
        # Always make a recursive descent on all declared dependencies.
        # In effect, if a module is present, then so is all its
        # dependencies in all configurations. This will pull down
        # more resources than needed (e.g. test dependencies), but
        # change if/when it becomes a problem.
        coord = id.coord()
        if not coord in self._modules:
            path   = self.resolve_ivy_xml(id)
            module = Module(self, id, XMLFileLoader(path))
            self._modules[coord] = module
            for dep_id in module.declared_dependencies():
                self.resolve(dep_id)
        return self._modules[coord]

    # Intended for standalone files.
    # Does not cache and register the loaded module.
    # Use 'resolve()' to resolve module via ivy.
    def module_from_path(self, path):
        root = ET.parse(path).getroot()
        info = root.find('info')
        id = ID(
            info.get('organisation'),
            info.get('module'),
            info.get('revision')
        )
        return Module(None, id, XMLFileLoader(path, root))

    def module_from_text(self, text):
        root = ET.fromstring(text)
        info = root.find('info')
        id = ID(
            info.get('organisation'),
            info.get('module'),
            info.get('revision')
        )
        return Module(None, id, XMLTextLoader(text, root))

    def print_dependencies(self, module, verbose = False, visited = set(), indent = ''):
        visited.add(module.id.coord())

        if verbose:
            print(indent + module.id.coord())

        for dep in module.declared_dependencies():
            if not dep.coord() in visited:
                self.print_dependencies(
                    self.resolve(dep),
                    verbose,
                    visited,
                    indent + ' '*2
                )
            elif verbose:
                print((indent + ' '*2) + "skip visited", dep.coord())

        if indent == '':
            print("Dependencies")
            for key in sorted(visited):
                print(" ", key)

    def compute_build_order(self, id, verbose = False):
        visitor = GraphVisitor()
        visitor.visit(self.resolve(id), verbose)
        return visitor._build_order

class GraphVisitor:
    def __init__(self):
        self._visited      = set()
        self._visited_from = dict() # { <coord> : [ <dependee> ] }
        self._dependencies = dict() # { <coord> : { <coord> } }
        self._build_order  = []     # [ <id> ]

    def _enter(self, module, verbose, indent, trace):
        coord = module.id.coord()
        if coord not in self._visited_from:
            self._visited_from[coord] = []
        self._visited_from[coord].append([x for x in trace])

        if coord in self._visited:
            if verbose:
                print(indent[:-2] + "^ " + coord)
            return False
        if verbose:
            print(indent + coord)
        self._visited.add(coord)
        return True

    def _leave(self, module, trace):
        self._build_order.append(module.id)

    def visit(self, module, verbose = False, indent = '', trace = []):
        coord = module.id.coord()
        if not self._enter(module, verbose, indent, trace):
            return
        dependencies              = module.declared_dependencies()
        self._dependencies[coord] = dependencies
        trace.append(module.id)
        for dep in dependencies:
            self.visit(
                module._cache.resolve(dep),
                verbose,
                indent + ' '*2,
                trace
            )
        trace.pop()
        self._leave(module, trace)

def blueprint():
    return ModuleBlueprint()

# Return an ivy cache with specified name.
# The cache will be backed by an ivy-cache on disk whose top-level folder
# name is the specified name, unless the name is None, in which case the
# returned cache is a pure in-memory cache. If the specified name is
# 'Cache._default_cache_name' a default shared cache instance is returned
# which is backed by disk.
def cache(name = CacheConstants._default_cache_name):
    return Cache.create_cache(name)

def in_memory_cache():
    return cache(None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cache"    , required = False,
                        help = "Ivy cache directory")
    parser.add_argument("-m", "--module"   , required = False,
                        help = "Read `ivy.xml` module from cache by name")
    parser.add_argument("-f", "--file"     , required = False,
                        help = "Read `ivy.xml` file")
    parser.add_argument("-v", "--verbose"  , required = False, action = "store_true",
                        help = "Print extra information to stdout where applicable.")
    parser.add_argument("--print"          , required = False, action = "store_true",
                        help = "Print all dependencies if specified")
    parser.add_argument("--classpath"      , required = False, action = "store_true",
                        help = "Print classpath if specified")
    parser.add_argument("--confs"          ,  required = False, nargs = "+",
                        help = "Enabled master configurations")

    args  = parser.parse_args()
    cache = Cache(args.cache) if args.cache else Cache()

    module = None
    if args.file:
        module = cache.module_from_file(args.file)
    elif args.module:
        module = cache.resolve(ID.from_coord(args.module))
    else:
        pass

    if args.print:
        cache.print_dependencies(module, args.verbose)

    if args.classpath and args.confs:
        conf_deps = cache.resolve_dependencies(ID.from_coord(args.module), args.confs)
        print("Classpath", args.confs)
        for d in conf_deps:
            print('  ' + d)

