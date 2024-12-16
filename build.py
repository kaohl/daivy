#!/bin/env python3

import argparse
from pathlib import Path
import shutil
import zipfile

from manifest import Manifest
import tools
from compile import Project, BuildContext
import ivy_cache_resolver as ivy


def add_harness(bm):
    dacapo  = Path('dacapo/dacapo')
    harness = Path('dacapo/harness')

    # TODO
    # We don't expect the harness to change so this could
    # be done once when the harness is extracted from dacapo...
    tools.javacc_7_0_12(
        harness,
        { 'OUTPUT_DIRECTORY': 'src/org/dacapo/parser' },
        [ 'src/org/dacapo/parser/ConfigFile.jj' ]
    )
    
    bm.sources(
        harness / 'src',
        include = ['*.java']
    )
    bm.sources(
        dacapo / 'src',
        include = ['*.java']
    )
    bm.resources(
        dacapo / 'src',
        include = ['*'],
        exclude = ['*.java']
    )

    # Benchmark driver runtime dependencies.
    bm_rt_cp = [x for x in bm._runtime_classpath]

    # Harness runtime dependencies
    hs_rt_cp = ivy.cache().resolve_dependencies(ivy.ID('dacapo', 'harness', '1.0'), ['runtime'])

    bm.extend_compile_classpath(ivy.cache().resolve_dependencies(ivy.ID('dacapo', 'harness', '1.0'), ['compile']))
    bm.extend_runtime_classpath(hs_rt_cp)

    stem = Path(bm.artifact()).stem

    classpath = ' '.join(
        # Paths are relative bm launcher deployed in:
        #   <context>/<bm-artifact-name>/
        [ str(Path(stem) / 'jar' / Path(x).name) for x in bm_rt_cp ] +
        [ str(Path(stem) / 'jhs' / Path(x).name) for x in hs_rt_cp ]
    )

    bm.manifest = Manifest({
        'Manifest-Version'     : '1.0',
        'Specification-Vendor' : 'DaCapo',
        'Main-Class'           : 'Harness',
        'Class-Path'           : classpath
    })

def bm_deploy(context, project):
    # Deployment layout of benchmarks:
    # <cxt>/
    #   <bm-artifact>.jar    # Manifest Class-Path: <bm-artifact-stem>/{jar,jhs}/*.jar
    #   <bm-artifact-stem>/  # Example: batik-1.0.jar => batik-1.0/
    #     dat/
    #       - Benchmark data
    #     jar/
    #       - Benchmark dependencies
    #     jhs/
    #       - Harness dependencies
    #     
    # That the launcher artifact is placed in <cxt>/ so that
    # the data folder is where the harness expects.
    #   - The Class-Path attribute is adapted accordingly.
    #
    bm_artifact = project.artifact()
    bm_name = project.id.mod
    path = context.path / Path(bm_artifact).stem
    dat  = path / 'dat'
    jar  = path / 'jar'
    jhs  = path / 'jhs'

    print("Deploy", path)

    if path.exists():
        shutil.rmtree(path)
    path.mkdir()

    dat.mkdir()
    jar.mkdir()
    jhs.mkdir()

    harness_runtime = ivy.cache().resolve_dependencies(ivy.ID('dacapo', 'harness', '1.0'), ['runtime'])
    for d in harness_runtime:
        shutil.copy2(d, jhs / Path(d).name)
        print("jhs:", jhs / Path(d).name)

    batik_runtime = ivy.cache().resolve_dependencies(ivy.ID('dacapo', bm_name, '1.0'), ['runtime'])
    for d in batik_runtime:
        shutil.copy2(d, jar / Path(d).name)
        print("jar:", jar / Path(d).name)

    # Copy benchmark data into context
    data = project.path / 'data' / 'dat'
    dat_bm_name = dat / bm_name

    #print("Copy", data, dat_bm_name)
    shutil.copytree(data, dat_bm_name, dirs_exist_ok = True)
    shutil.copy2(ivy.cache().location(project.id) / 'jars' / bm_artifact, path.parent)

    context_art = path.parent / bm_artifact

    # TODO: Fix later if needed.
    with zipfile.ZipFile(context_art, 'a') as f:
        # For now, add empty files to make the harness run.
        f.writestr('META-INF/md5/' + bm_name + '.MD5', bytes())
        f.writestr('META-INF/yml/' + bm_name + '.yml', bytes())

def bm_batik():
    id = ivy.ID('dacapo', 'batik', '1.0')
    bm = Project('projects/batik', id)

    bm.deployment = bm_deploy

    bm.extend_compile_classpath(ivy.cache().resolve_dependencies(id, ['compile']))
    bm.extend_runtime_classpath(ivy.cache().resolve_dependencies(id, ['runtime']))

    add_harness(bm)

    bm.sources(
        bm.path / 'harness/src',
        include = ['*.java']
    )
    bm.resources_copy_to(
        bm.path / 'build/src/main/resources/META-INF/cnf',
        bm.path,
        include = ['batik.cnf'],
        exclude = ['build/src/main/resources/META-INF/cnf/batik.cnf'],
        options = {'verbose' : True }
    )
    return bm

def batik_1_16():
    batik_id = ivy.ID('org.apache.xmlgraphics', 'batik-all', '1.16')
    batik    = Project('projects/batik-1.16', batik_id)
    batik.resources(
        batik.path / "src/main/java",
        include = ['*'],
        exclude = ['*.java', '**/jacl/*', '*.html', 'org/apache/batik/gvt/filter/filterDesc.txt']
    )
    batik.resources(
        batik.path / "src/main/resources",
        include = ['*'],
        exclude = ['NOTICE', 'LICENSE']
    )
    # TODO: Something weird with mapping
    #batik.resources_copy_to(
    #    batik.path / "build/dist/META-INF",
    #    batik.path / "src/main/resources",
    #    include = ['NOTICE', 'LICENSE'],
    #    exclude = []
    #)
    batik.sources(
        batik.path / "src/main/java",
        include = ['*.java'],
        exclude = ['**/jacl/*'] # See 'batik-script/pom.xml'.
    )
    batik.extend_compile_classpath(ivy.cache().resolve_dependencies(batik_id, ['compile']))
    batik.extend_runtime_classpath(ivy.cache().resolve_dependencies(batik_id, ['runtime']))
    batik.manifest = Manifest({
        "Manifest-Version"        : "1.0",
        "Created-By"              : "Alfine",
        "Implementation-Title"    : "org.apache.xmlgraphics:batik-all",
        "Implementation-Version"  : "1.16",
        "Implementation-Vendor-Id": "org.apache.xmlgraphics",
        "Implementation-Vendor"   : "Apache Software Foundation",
        "Main-Class"              : "org.apache.batik.apps.svgbrowser.Main",
        'Class-Path'              : batik.classpath_attribute_value()
        # Depends on runtime classpath being set.
        # TODO: We can compute Class-Path here instead, no need to set runtime dependencies on project.
        #       Also, we don't need this manifest since we are not going to invoke as standalone jar.
    })
    return batik

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required = True,
        help = "Coordinate of project to operate on")
    parser.add_argument('--context', required = True,
        help = "Build context folder for export/import")
    parser.add_argument('--export' , required = False, action = "store_true",
        help = "Export project source code and eclipse configuration")
    parser.add_argument('--clean', required = False, action = "store_true",
        help = "Clean project before building")
    args = parser.parse_args()

    # ATTENTION
    # The user must build all relevant projects "manually" (scripted).
    # Implementing recursive builds is TODO at the moment (see notes/).
    print("ATTENTION", "Do not forget to build dependencies first")

    Project._global_build_context = BuildContext(args.context)

    projects = {
        'dacapo:batik:1.0'                      : bm_batik,
        'org.apache.xmlgraphics:batik-all:1.16' : batik_1_16
    }

    project = projects[args.project]()

    if args.export:
        raise ValueError('Export is unimplemented')

    project.build(args.clean)

