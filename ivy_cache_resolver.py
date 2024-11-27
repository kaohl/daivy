#!/bin/env python3

import argparse
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

class XMLHelper:
    def get_attribute(xml, name, default_values):
        return xml.get(name) if name in xml.attrib else (default_values[name] if name in default_values else None)

class MasterConfig:

    _default_attribute_values = {
        'visibility' : 'public',
        'transitive' : 'true'
    }

    def _get_attribute(conf_xml, name):
        return XMLHelper.get_attribute(conf_xml, name, MasterConfig._default_attribute_values)

    def default_xml():
        confs = ET.Element('configurations')
        conf  = ET.SubElement(a, 'conf', {
            'name'        : 'default',
            'visibility'  : MasterConfig._default_attribute_values['visibility'],
            'transitive'  : MasterConfig._default_attribute_values['transitive']
        })
        return confs

    def default_config():
        return MasterConfig(MasterConfig.default_xml())

    def __init__(self, conf_xml):
        self._conf_xml   = conf_xml

        if not 'name' in conf_xml.attrib:
            print("attribs", conf_xml.attrib)
            raise ValueError('Missing reqired name attribute in conf xml')

        self.name        = MasterConfig._get_attribute(conf_xml, 'name')
        self.description = MasterConfig._get_attribute(conf_xml, 'description')
        self.visibility  = MasterConfig._get_attribute(conf_xml, 'visibility')
        self.extends     = MasterConfig._get_attribute(conf_xml, 'extends')
        self.transitive  = MasterConfig._get_attribute(conf_xml, 'transitive')
        self.deprecated  = MasterConfig._get_attribute(conf_xml, 'deprecated')

    def get_attribute(self, name):
        return MasterConfig._get_attribute(self._conf_xml, name)

class MasterConfigs:
    def __init__(self, configs, configurations_xml):
        self._configs = configs if len(configs) > 0 else { 'default' : MasterConfig.default_config() }
        self._configurations_xml = configurations_xml

    def defaultconf(self):
        return XMLHelper.get_attribute(self._configurations_xml, 'defaultconf')

    def defaultconfmapping(self):
        return XMLHelper.get_attribute(self._configurations_xml, 'defaultconfmapping')

    def confmappingoverride(self):
        return 'true' == XMLHelper.get_attribute(self._configurations_xml, 'confmappingoverride')

    def config(self, name = 'default'):
        if not name in self._configs:
            raise ValueError('No such configuration', '"' + name + '"')
        return self._configs[name]

    def from_xml(configurations_xml):
        print("Configurations xml", configurations_xml)
        configs = {}
        if configurations_xml is not None:
            for child in configurations_xml:
                print("Child", child)
                if child.tag == 'conf':
                    config = MasterConfig(child)
                    configs[config.name] = config
                elif child.tag == 'include':
                    # Handle when/if needed.
                    # Here it sounds like such files are inlined automatically(?):
                    #   https://ant.apache.org/ivy/history/latest-milestone/ivyfile/include.html
                    raise ValueError('Unimplemented: Parse included configuration file', child.attrib.file)
                else:
                    raise ValueError('Unhandled configuration child tag', child.tag)
        return MasterConfigs(configs, configurations_xml)

class ID:
    def __init__(self, org, mod, rev):
        self.org = org
        self.mod = mod
        self.rev = rev

    def from_coord(coord):
        parts = coord.split(":")
        org   = parts[0]
        mod   = parts[1]
        rev   = parts[2]
        return ID(org, mod, rev)

class Dependency:
    def __init__(self, id, conf):
        self.id   = id
        self.conf = conf

class Module:
    def __init__(self, id, configs, dependencies):
        self.id            = id
        self.configs       = configs
        self._dependencies = {
            None: dependencies
            # [<conf>] = [<dependency>]
            # [ None ] = <all dependencies unfiltered>
        }

    def dependencies(self, conf = None):
        if not conf in self._dependencies:
            dependencies = []
            for dep in self._dependencies[None]:
                # TODO: Implement configuration matching.
                dependencies.append(dep)
            self._dependencies[conf] = dependencies
        return self._dependencies[conf]

class Cache:
    def __init__(self, cachepath = 'ivy-cache'):
        self._cachepath = cachepath
        self._modules   = dict()

    def resolve_ivy_xml_from_coord(self, coord):
        return self.resolve_ivy_xml(ID.from_coord(coord))

    def resolve_ivy_xml(self, id):
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
                "-cache",
                self._cachepath,
                "-dependency",
                id.org,
                id.mod,
                id.rev
            ])
            subprocess.run(cmd, shell = True)
        return ivy_xml

    def resolve_module(self, id, recurse = False):
        if not id in self._modules:
            self._modules[id] = self._load_ivy_xml(
                self.resolve_ivy_xml(id),
                recurse
            )
        return self._modules[id]

    # Intended for standalone files.
    # Does not cache and register the loaded module.
    # Use 'resolve_module()' to resolve module via ivy.
    def module_from_file(self, path, recurse = False):
        return self._load_ivy_xml(path, recurse)

    def _load_ivy_xml(self, path, recurse = False):
        root = ET.parse(path).getroot()
        info = root.find('info')
        deps = root.find('dependencies')
        conf = root.find('configurations')

        id = ID(
            info.get('organisation'),
            info.get('module'),
            info.get('revision')
        )

        dependencies = []
        if deps is not None:
            for dep in deps.findall('dependency'):
                d_org     = dep.get('org')
                d_name    = dep.get('name')
                d_rev     = dep.get('rev')
                d_conf    = dep.get('conf')
                d_include = dep.get('include')

                d_id = ID(d_org, d_name, d_rev)
                dependencies.append(Dependency(d_id, d_conf))

                if recurse:
                    self.resolve_module(d_id, recurse)

        configs = MasterConfigs.from_xml(conf)
        return Module(id, configs, dependencies)

    def print_dependencies(self, module, visited = set(), indent = ''):
        org = module.id.org
        mod = module.id.mod
        rev = module.id.rev
        key = (org, mod, rev)
        # print(indent + org, mod, rev)
        for dep in module.dependencies():
            dep_m = self.resolve_module(dep.id)
            visited.add(":".join([org, mod, rev]))
            self.print_dependencies(dep_m, visited, indent + ' '*2)

        if indent == '':
            print("Dependencies")
            for key in sorted(visited):
                print(" ", key)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cache"    , required = False, help = "Ivy cache directory")
    parser.add_argument("-r", "--recursive", required = False, action = "store_true", help = "Whether to traverse down recursively")
    parser.add_argument("-m", "--module"   , required = False, help = "Read `ivy.xml` module from cache by name")
    parser.add_argument("-f", "--file"     , required = False, help = "Read `ivy.xml` file")

    args  = parser.parse_args()
    cache = Cache(args.cache) if args.cache else Cache()

    module = None
    if args.file:
        module = cache.module_from_file(args.file, args.recursive)
    elif args.module:
        module = cache.resolve_module(ID.from_coord(args.module), args.recursive)
    else:
        pass

    cache.print_dependencies(module)

