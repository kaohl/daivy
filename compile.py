#!/bin/env python

import argparse
import itertools
import os
import pathlib
import shutil
import subprocess
import tempfile
import ivy_cache_resolver as ivy

def javac_fn(cwd, options_file, sources_file):

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
        "javac",
        "@" + options_file,
        "@" + sources_file
    ])
    subprocess.run(cmd, shell = True, cwd=cwd)

def compile(cwd, options, source_sets):
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

            javac_fn(cwd, options_file.name, sources_file.name)

class Files:
    def __init__(self, context, src, include, exclude):
        self._context = pathlib.Path(context)
        self._src     = pathlib.Path(src)
        self._include = include or []
        self._exclude = exclude or []

    def include(context, src, include):
        return Files(src, include, None)

    def of(context, src, include, exclude):
        return Files(context, src, include, exclude)

    def match(self, path):
        if self._exclude is not None:
            for p in self._exclude:
                if path.match(p):
                    #print('Exclude', p, path)
                    return False
        if self._include is not None:
            for p in self._include:
                if path.match(p):
                    #print('Include', p, path)
                    return True
        #print('Exclude (no pattern)', path)
        return False

    def __iter__(self):
        return (
            (pathlib.Path(d).relative_to(self._context) / file for file in files if self.match(pathlib.Path(d).relative_to(self._context) / file))
            for d, dirs, files in os.walk(self._context / self._src)
        )

class Javac:
    def __init__(self, context):
        self._context     = pathlib.Path(context)
        self._classes     = None
        self._sources     = []
        self._classpath   = []
        self._sourcepaths = []

    def classes(self, path):
        self._classes = pathlib.Path(path)

    def sources(self, sources):
        self._sources.extend(sources)

    def classpath(self, paths):
        self._classpath.extend(paths)

    def compile(self):
        options = []

        if self._classes is not None:
            options.append(('-d', self._classes))

        if len(self._classpath) > 0:
            options.append(('-classpath', ':'.join(self._classpath)))

        if len(self._sourcepaths) > 0:
            options.append(('-sourcepath', ':'.join(self._sourcepaths)))

        compile(self._context, options, self._sources)

class Project:
    def __init__(self, path):
        self._path              = pathlib.Path(path)
        self._sources           = []
        self._resources         = []
        self._resources_copy_to = []
        self._classpath_entries = []
        self._manifest_text     = None

    def manifest(self, text):
        self._manifest_text = text

    def sources(self, src, include, exclude):
        self._sources.append(Files.of(self._path, src, include, exclude))

    def resources(self, src, include, exclude):
        self._resources.append(Files.of(self._path, src, include, exclude))

    def resources_copy_to(self, src, dst, include, exclude):
        self._resources_copy_to.append((dst, Files.of(self._path, src, include, exclude)))

    def classpath(self, ids):
        self._classpath_entries.extend(ids)

    def _assemble_classpath(self, context_path_prefix = pathlib.Path('.')):
        ivy_jars = ivy.cache().resolve_classpath(self._classpath_entries)
        return [ str(context_path_prefix / jar_path) for jar_path in ivy_jars ]

    def _compile(self):
        classes = self._path / 'dist'

        if not classes.exists():
            classes.mkdir()

        javac = Javac(self._path)
        javac.sources(self._sources)
        javac.classes("dist")
        javac.classpath(
            self._assemble_classpath(pathlib.Path('../../'))
        )
        javac.compile()

    def _copy_resources(self):
        for gs in self._resources:
            for g in gs:
                for f in g:
                    src = self._path / f
                    dst = self._path / pathlib.Path('dist') / f.relative_to(gs._src)
                    if not dst.parent.exists():
                        dst.parent.mkdir(parents = True, exist_ok = True)
                    #print("Copy", src, dst)
                    shutil.copy2(src, dst)

        for (d, gs) in self._resources_copy_to:
            for g in gs:
                for f in g:
                    src = self._path / f
                    dst = self._path / d / f.relative_to(gs._src)
                    #print("Copy to", src, dst)
                    shutil.copy2(src, dst)

        # Always write manifest in case text changes.
        manifest_path = self._path / pathlib.Path('dist/META-INF/MANIFEST.MF')
        with open(manifest_path, 'w') as mf:
            mf.write(self._manifest_text)

    def _package(self):
        jar_filename = self._path / 'project-test'
        dir_path     = self._path / 'dist'
        shutil.make_archive(jar_filename, 'zip', dir_path)

    def build(self):
        self._compile()
        self._copy_resources()
        self._package()

    def test(self):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args   = parser.parse_args()

    batik = Project('projects/batik-1.16')
    batik.resources(
        "src/main/java",
        include = ['*'],
        exclude = ['*.java', '**/jacl/*', '*.html', 'org/apache/batik/gvt/filter/filterDesc.txt']
    )
    batik.resources(
        "src/main/resources",
        include = ['*'],
        exclude = ['NOTICE', 'LICENSE']
    )
    batik.resources_copy_to(
        "src/main/resources",
        "dist/META-INF",
        include = ['NOTICE', 'LICENSE'],
        exclude = []
    )
    batik.sources(
        "src/main/java",
        include = ['*.java'],
        exclude = ['**/jacl/*'] # See 'batik-script/pom.xml'.
    )
    batik.classpath([
        ivy.ID("xml-apis", "xml-apis", "1.4.01"),
	ivy.ID("xml-apis", "xml-apis-ext", "1.3.04"),
	ivy.ID("org.apache.xmlgraphics", "xmlgraphics-commons", "2.7"),
	ivy.ID("commons-io", "commons-io", "1.3.1"),
	ivy.ID("commons-logging", "commons-logging", "1.0.4"),
        ivy.ID("org.mozilla", "rhino", "1.7.7"),
        ivy.ID("org.python", "jython", "2.7.0")
    ])
    batik.manifest("""Manifest-Version: 1.0
Created-By: Alfine
Implementation-Title: org.apache.xmlgraphics:batik-all
Implementation-Version: 1.16
Implementation-Vendor-Id: org.apache.xmlgraphics
Implementation-Vendor: Apache Software Foundation
Main-Class: org.apache.batik.apps.svgbrowser.Main
""")

    # NOTE
    # Checksums between ivy-provided and locally built jars fail even if manifest
    # is the same because all class-files differ according to "diff -q -r -N -a tmp1 tmp2",
    # where I unpacked ivy-provided and local builds, (probably) due to different javac versions (?).
    #
    # My util 'cmpzip.py' reports that they atleast have the same zipfile namelists.
    # I guess that is the best we can do for now. It should not affect results.
    #

    batik.build()

