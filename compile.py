#!/bin/env python

import argparse
import itertools
from manifest import Manifest
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import ivy_cache_resolver as ivy
import tools

def javac_fn(options_file, sources_file):

    with open(options_file, 'r') as f:
        print("Options")
        for line in f.readlines():
            print(line.strip())

    #with open(sources_file, 'r') as f:
    #    print("Sources")
    #    for line in f.readlines():
    #        print(line.strip())

    cmd = " ".join([
        'echo pwd=`pwd`;',
        "${JAVA_HOME}/bin/javac -version;",
        "${JAVA_HOME}/bin/javac",
        "@" + options_file,
        "@" + sources_file
    ])
    print("Command", cmd)
    subprocess.run(cmd, shell = True, check = True)

def compile(options, source_sets):
    with tempfile.NamedTemporaryFile(delete_on_close=False) as options_file:
        for (option, value) in options:
            options_file.write(bytes(option + " " + str(value) + os.linesep, encoding='utf-8'))
        options_file.close()

        with tempfile.NamedTemporaryFile(delete_on_close=False) as sources_file:
            for gs in source_sets:
                for g in gs:
                    for s in g:
                        sources_file.write(bytes(str(s) + os.linesep, encoding='utf-8'))
            sources_file.close()

            javac_fn(options_file.name, sources_file.name)

class Files:
    def __init__(self, folder, include, exclude, options = {}):
        self._src     = Path(folder)
        self._include = include or []
        self._exclude = exclude or []
        self._verbose = options['verbose'] if 'verbose' in options else False

    def include(folder, include, options = {}):
        return Files(folder, include, None, options)

    def exclude(folder, exclude, options = {}):
        return Files(folder, ['*'], exclude, options)

    def of(folder, include, exclude, options = {}):
        return Files(folder, include, exclude, options)

    def match(self, path):
        if self._exclude is not None:
            for p in self._exclude:
                if path.match(p):
                    if self._verbose:
                        print('Exclude', p, path)
                    return False
        if self._include is not None:
            for p in self._include:
                if path.match(p):
                    if self._verbose:
                        print('Include', p, path)
                    return True
        if self._verbose:
            print('Exclude (no pattern)', path)
        return False

    def __iter__(self):
        return (
            (Path(d) / file for file in files if self.match(Path(d).relative_to(self._src) / file))
            for d, dirs, files in os.walk(self._src)
        )

class Javac:
    def __init__(self, target_version):
        self._target_version = target_version
        self._classes        = None
        self._sources        = []
        self._classpath      = []
        self._modulepath     = []

    def classes(self, path):
        self._classes = Path(path)

    def sources(self, sources):
        self._sources.extend(sources)

    def classpath(self, paths):
        paths = [ p.strip() for p in paths ]
        self._classpath.extend([ p for p in paths if p != "" ])

    def modulepath(self, paths):
        paths = [ p.strip() for p in paths ]
        self._modulepath.extend([ p for p in paths if p != "" ])

    def compile(self):
        options = []

        if self._target_version != None:
            options.append(('-target', self._target_version))

        if self._classes is not None:
            options.append(('-d', self._classes))

        if len(self._classpath) > 0:
            cp = ':'.join(self._classpath)
            options.append(('-classpath', cp))

        if len(self._modulepath) > 0:
            cp = ':'.join(self._modulepath)
            options.append(('--module-path', cp))

        compile(options, self._sources)

class Config:

    # TODO: Configuration needs some more thought...

    _JDK8  = 'jdk8'
    _JDK11 = 'jdk11'
    _JDK17 = 'jdk17'
    _SOURCE_VERSION = 'source-version'
    _TARGET_VERSION = 'target-version'

    _global_properties = None
    def _load_global_properties(context_path):
        if Config._global_properties is None:
            props = Config._load_properties_file(context_path / 'global.properties')
            print("using", Config._JDK8 , props.get(Config._JDK8))
            print("using", Config._JDK11, props.get(Config._JDK11))
            Config._global_properties = props
        return Config._global_properties

    _project_properties = dict()
    def _load_project_properties(context, project):
        coord = project.id.coord()
        stem  = coord.replace(':', "_").replace('.', '_')
        path  = context.path / stem + '.properties'
        if not coord in Config._project_properties:
            props                         = Config._load_properties_file(path, True) or dict()
            props[Config._SOURCE_VERSION] = props.get(Config._SOURCE_VERSION) or project._source_version
            props[Config._TARGET_VERSION] = props.get(Config._TARGET_VERSION) or project._target_version
            Config._project_properties[coord] = props
        return Config._project_properties[coord]

    def _load_properties_file(path, optional = False):
        if not path.exists():
            if optional:
                print("Failed to load optional properties file. Path does not exist:", str(path))
                return None
            raise ValueError('Required properties file does not exist', str(path))
        print("Loading properties file", str(path))
        properties = dict()
        with open(path, 'r') as f:
            for line in f:
                kv = [ x.strip() for x in line.split('=') ]
                properties[kv[0]] = kv[1]
        return properties

    def __init__(self, context, project):
        self.id      = project.id
        self.context = context
        self.project = project
        self.verbose = context.args.verbose

    def properties(self):
        return Config._load_project_properties(self.context, self.project)

    def import_location(self):
        if not self.context.args.import_path is None:
            return Path(self.context.args.import_path)
        return None

    def target_version(self):
        if not self.context.args.target_version is None:
            return self.context.args.target_version
        return None

class BuildContext:
    def __init__(self, path, args):
        self.path = Path(path)
        self.args = args

    def config(self, project):
        return Config(self, project)

class Project:

    # This variable is set by the command line interface.
    # The build context holds import/export/deployment
    # resources.
    _global_build_context = None

    def __init__(self, path, id = None):
        self.id                  = id
        self.path                = Path(path)
        self._sources            = []
        self._resources          = []
        self._resources_copy_to  = []
        self._compile_modulepath = []
        self._compile_classpath  = []
        self._runtime_classpath  = [] # TODO: We don't seem to need the runtime classpath here if we add the manifest classpath in 'build.py'
        self.manifest            = None
        self.manifest_changes    = None
        self.deployment          = None
        self._source_version     = 8
        self._target_version     = 8

        if not self.path.exists():
            raise ValueError('Project path does not exist', str(self.path))

    def set_source_version(self, vnum):
        self._source_version = int(vnum)

    def set_target_version(self, vnum):
        self._target_version = int(vnum)

    def context(self):
        return Project._global_build_context

    def config(self):
        if Project._global_build_context is None:
            return None
        return Project._global_build_context.config(self)

    def artifact(self):
        return '-'.join([self.id.mod, self.id.rev]) + '.jar'

    def sources(self, folder, include, exclude = [], options = {}):
        self._sources.append(Files.of(folder, include, exclude, options))

    def resources(self, folder, include, exclude = [], options = {}):
        self._resources.append(Files.of(folder, include, exclude, options))

    def resources_copy_to(self, dst, src, include, exclude, options = {}):
        self._resources_copy_to.append((dst, Files.of(src, include, exclude, options)))

    def extend_compile_modulepath(self, entries):
        self._compile_modulepath.extend(entries)

    def extend_compile_classpath(self, entries):
        self._compile_classpath.extend(entries)

    def extend_runtime_classpath(self, entries):
        self._runtime_classpath.extend(entries)

    def _copy_sources(self):
        build     = self.path / 'build'
        main_java = build / 'src/main/java'
        test_java = build / 'src/test/java'

        if not main_java.exists():
            main_java.mkdir(parents = True)

        if not test_java.exists():
            test_java.mkdir(parents = True)
 
        for gs in self._sources:
            for g in gs:
                for src in g:
                    dst =  main_java / src.relative_to(gs._src)
                    if not dst.parent.exists():
                        dst.parent.mkdir(parents = True, exist_ok = True)
                    #print("Copy", src, dst)
                    shutil.copy2(src, dst)

    def _copy_resources(self):
        targets = [
            Path('build/dist'),
            Path('build/src/main/resources')
        ]
        for gs in self._resources:
            for g in gs:
                for src in g:
                    for target in targets:
                        dst = self.path / target / src.relative_to(gs._src)
                        if not dst.parent.exists():
                            dst.parent.mkdir(parents = True, exist_ok = True)
                        #print("Copy", src, dst)
                        shutil.copy2(src, dst)

        for (dst, gs) in self._resources_copy_to:
            for g in gs:
                for src in g:
                    dst = dst / src.relative_to(gs._src)
                    if not dst.parent.exists():
                        dst.parent.mkdir(parents = True, exist_ok = True)
                    #print("Copy to", src, dst)
                    shutil.copy2(src, dst)

    def classpath_attribute_value(self):
        rcp = [ str(Path(e).relative_to(Path(os.getcwd()))) for e in self._runtime_classpath ]
        cp  = ' '.join(rcp)
        return cp

    def _write_manifest(self, mfpath):
        # Select specified manifest or from file if changes exists.
        manifest = self.manifest if not self.manifest is None else (
            Manifest.load(mfpath) if not self.manifest_changes is None else None
        )

        # Write manifest (otherwise it is expected to be added as a resource).
        if not manifest is None:
            if not self.manifest_changes is None:
                manifest.update(self.manifest_changes)
            if not mfpath.parent.exists():
                mfpath.parent.mkdir(parents = True)
            manifest.store(mfpath)


    # Assemble 'build/' or deploy from zip.
    #
    # Build layout:
    #   - Use one project per artifact when possible
    #   - Use one build folder per artifact when not 
    #
    # build/
    #   src/{main,test}/java/
    #   src/{main,test}/resources/
    #   dist/
    def _create_source_tree(self):
        build_zip       = self.path / 'build.zip'
        build           = self.path / 'build'
        import_location = self.config().import_location()

        if build.exists():
            shutil.rmtree(build)

        if not import_location is None and (import_location / self.export_name()).exists():
            build.mkdir()
            p = tools.unzip(import_location / self.export_name(), build)
            print("Unzipped to", p)
        elif not build_zip.exists():
            print("Create build.zip")
            self._copy_sources()
            self._copy_resources()
            # TODO: Should we really do this here? Not instead when compiling?
            self._write_manifest(build / 'src/main/resources/META-INF/MANIFEST.MF')
            tools.zip(build, build_zip)
        else:
            build.mkdir()
            p = tools.unzip(build_zip, build)
            print("Unzipped to", p)

    def _create_binary_tree(self):
        build = self.path / 'build'
        dist  = build / 'dist'

        if not dist.exists():
            dist.mkdir(parents = True)

        # TODO: Copy resources from 'build/src/{main,test}/resources'
        # TODO: Need test resource declarations (conf specific actions)

        # The goal here is to copy resources that should be packaged into the jar.
        # Deployment data is handled in the deployment function.

        _src = build / 'src/main/resources'
        for g in Files.include(_src, include = ['*']):
            for src in g:
                dst = dist / src.relative_to(_src)
                if not dst.parent.exists():
                    dst.parent.mkdir(parents = True, exist_ok = True)
                #print("Copy (binary resources)", src, dst)
                shutil.copy2(src, dst)

    def _compile(self):
        self._create_source_tree()
        self._create_binary_tree()

        build     = self.path / 'build'
        dist      = build / 'dist'
        main_java = build / 'src/main/java'

        javac = Javac(self.config().target_version())
        javac.sources([ Files.include(main_java, ['*.java']) ])
        javac.classes(str(dist))
        javac.classpath(self._compile_classpath)
        javac.modulepath(self._compile_modulepath)
        javac.compile()

    def _package(self, artifact):
        self._compile()
        jar_src = self.path / 'build/dist'
        jar_dst = artifact
        tools.jar(jar_src, jar_dst)

    def _deploy(self):
        artifact        = None
        import_location = self.config().import_location()
        if not import_location is None and (import_location / self.export_name()).exists():
            patch      = import_location / self.export_name()
            patch_hash = tools.digest(patch, 'md5')
            artifact   = self.path / 'var' / patch_hash / self.artifact()
        else:
            artifact = self.path / 'var' / self.artifact()

        if not artifact.exists():
            self._package(artifact)

        self._update_build_cache(artifact)

        # Deploy application using custom logic.
        # Deploy benchmarks into the build context.
        if not self.deployment is None:
            self.deployment(self.context(), self)

    def _update_build_cache(self, artifact):
        # We assume that all modules have already been pulled from providers.
        jars  = ivy.cache().location(self.id) / 'jars'
        jar   = jars / artifact.name
        print("Update build cache", jar, "<=", artifact)
        if not jars.exists():
            jars.mkdir()
        shutil.copy2(artifact, jar)

    def build(self, clean):
        if clean:
            self.clean()
        self._deploy()

    def clean(self):
        var       = self.path / 'var'
        build     = self.path / 'build'
        build_zip = self.path / 'build.zip'
        if var.exists():
            shutil.rmtree(var)
        if build.exists():
            shutil.rmtree(build)
        if build_zip.exists():
            os.remove(build_zip)

    def export_name(self):
        return Path(self.artifact()).stem + "-build.zip"

    def export(self, folder):
        if not folder.is_dir():
            raise ValueError("Expected directory")
        src = self.path / 'build.zip'
        dst = folder / self.export_name()
        print("Copy", src, dst)
        shutil.copy2(src, dst)

    def test(self):
        raise ValueError('Unimplemented')

