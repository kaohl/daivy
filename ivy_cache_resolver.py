#!/bin/env python3

import argparse
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

class IvyId:
    def __init__(self, org, mod, rev):
        self.org = org
        self.mod = mod
        self.rev = rev

    def from_coord(coord):
        parts = coord.split(":")
        org   = parts[0]
        mod   = parts[1]
        rev   = parts[2]
        return IvyId(org, mod, rev)

class Dependency:
    def __init__(self, id, conf):
        self.id   = id
        self.conf = conf

class Module:
    def __init__(self, id, dependencies):
        self.id            = id
        self._dependencies = {
            None: dependencies
            # [<conf>] = [<dependency>]
            # [ None ] = <all dependencies unfiltered>
        }

    def dependencies(self, conf = None):
        if not conf in self._dependencies:
            dependencies = []
            for dep in self._dependencies[None]:
                # TODO: Implement configuration matching
                if dep.conf.find(conf) != -1:
                    dependencies.append(dep)
            self._dependencies[conf] = dependencies
        return self._dependencies[conf]

class IvyCache:
    def __init__(self, cachepath = 'ivy-cache'):
        self._cachepath = cachepath
        self._modules   = dict()

    def resolve_ivy_xml_from_coord(self, coord):
        return self.resolve_ivy_xml(IvyId.from_coord(coord))

    def resolve_ivy_xml(self, id):
        ivyXML = Path(os.path.sep.join([
            self._cachepath,
            id.org,
            id.mod,
            "-".join(["ivy", id.rev + ".xml"])
        ]))
        if not ivyXML.exists():
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
        return ivyXML

    def resolve_module(self, id, recurse = False):
        if not id in self._modules:
            self._modules[id] = self.loadIvyXML(
                self.resolve_ivy_xml(id),
                recurse
            )
        return self._modules[id]

    # Intended for standalone files.
    # Does not cache the loaded module.
    def module_from_file(self, path, recurse = False):
        return self.loadIvyXML(path, recurse)

    def loadIvyXML(self, path, recurse = False):
        root = ET.parse(path).getroot()
        info = root.find('info')
        deps = root.find('dependencies')

        id = IvyId(
            info.get('organisation'),
            info.get('module'),
            info.get('revision')
        )

        dependencies = []
        if deps is not None:
            for dep in root.find('dependencies').findall('dependency'):
                org  = dep.get('org')
                name = dep.get('name')
                rev  = dep.get('rev')
                conf = dep.get('conf')
                include = dep.get('include')

                dep_id = IvyId(org, name, rev)
                dependencies.append(Dependency(dep_id, conf))

                if recurse:
                    self.resolve_module(dep_id, recurse)

        return Module(id, dependencies)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cache", required = False, help = "Ivy cache directory")
    parser.add_argument("-r", "--recursive", action="store_true", required = False, help = "Whether to traverse down recursively")
    parser.add_argument("-m", "--module", required = False, help = "Read `ivy.xml` module from cache by name")
    parser.add_argument("-f", "--file", required = False, help = "Read `ivy.xml` file")

    args  = parser.parse_args()
    cache = IvyCache(args.cache) if args.cache else IvyCache()

    module = None
    if args.file:
        module = cache.module_from_file(args.file, args.recursive)
    elif args.module:
        module = cache.resolve_module(IvyId.from_coord(args.module), args.recursive)
    else:
        pass

