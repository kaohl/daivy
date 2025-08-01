#!/bin/env python3

import argparse
import os
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
    #hs_rt_cp = ivy.cache().resolve_dependencies(ivy.ID('dacapo', 'harness', '1.0'), ['runtime'])
    #
    #bm.extend_compile_classpath(ivy.cache().resolve_dependencies(ivy.ID('dacapo', 'harness', '1.0'), ['compile']))
    #bm.extend_runtime_classpath(hs_rt_cp)

    stem = Path(bm.artifact()).stem

    classpath = ' '.join(
        # Paths are relative bm launcher deployed in:
        #   <context>/<bm-artifact-name>/
        [ str(Path(stem) / 'jar' / Path(x).name) for x in bm_rt_cp ]
        #+ [ str(Path(stem) / 'jhs' / Path(x).name) for x in hs_rt_cp ]
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

    #harness_runtime = ivy.cache().resolve_dependencies(ivy.ID('dacapo', 'harness', '1.0'), ['runtime'])
    #for d in harness_runtime:
    #    shutil.copy2(d, jhs / Path(d).name)
    #    print("jhs:", jhs / Path(d).name)

    batik_runtime = ivy.cache().resolve_dependencies(ivy.ID('dacapo', bm_name, '1.0'), ['runtime'])
    for d in batik_runtime:
        shutil.copy2(d, jar / Path(d).name)
        print("jar:", jar / Path(d).name)

    ## Copy benchmark data into context
    #data = project.path / 'data' / 'dat'
    #dat_bm_name = dat / bm_name
    ##print("Copy", data, dat_bm_name)
    #shutil.copytree(data, dat_bm_name, dirs_exist_ok = True)

    # Symlink unpacked data archive into deployment.
    data_link_src = Path.cwd() / Path('build') / (bm_name + '-data')
    data_link_dst = dat / bm_name
    print("Linking data into deployment")
    print(" ", data_link_src)
    print(" =>", data_link_dst)
    os.symlink(
        data_link_src,
        data_link_dst,
        target_is_directory = True
    )

    # Deploy artifact from build cache
    shutil.copy2(ivy.cache().location(project.id) / 'jars' / bm_artifact, path.parent)
    
    context_art = path.parent / bm_artifact

    # TODO: Fix later if needed.
    with zipfile.ZipFile(context_art, 'a') as f:
        # For now, add empty files to make the harness run.
        f.writestr('META-INF/md5/' + bm_name + '.MD5', bytes())
        f.writestr('META-INF/yml/' + bm_name + '.yml', bytes())

def bm_build(name):
    id = ivy.ID('dacapo', name, '1.0')
    bm = Project('projects/' + name, id)

    bm.deployment = bm_deploy

    bm.extend_compile_classpath(ivy.cache().resolve_dependencies(id, ['compile']))
    bm.extend_runtime_classpath(ivy.cache().resolve_dependencies(id, ['runtime']))

    add_harness(bm)

    bm.sources(
        bm.path / 'harness/src',
        include = ['*.java']
    )

    if (bm.path / 'src').exists():
        bm.sources(
            bm.path / 'src',
            include = ['*.java']
        )

    bm.resources_copy_to(
        bm.path / 'build/src/main/resources/META-INF/cnf',
        bm.path,
        include = [name + '.cnf'],
        exclude = ['build/src/main/resources/META-INF/cnf/' + name + '.cnf'],
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
        "Created-By"              : "Daivy",
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

def lucene_9_10_0(module):
    id       = ivy.ID('org.apache.lucene', 'lucene-' + module, '9.10.0')
    project  = Project('projects/lucene-' + module + '-9.10.0', id)
    project.set_source_version(11)
    project.set_target_version(11)
    project.sources(
        project.path / "src/main/java",
        include = ['*.java']
    )
    project.resources(
        project.path / "src/main/resources",
        include = ['*']
    )
    compile_deps = ivy.cache().resolve_dependencies(id, ['compile'])
    runtime_deps = ivy.cache().resolve_dependencies(id, ['runtime'])
    project.extend_compile_classpath(compile_deps)
    project.extend_runtime_classpath(runtime_deps)
    # NOTE: Had to add runtime deps to module path to get module-info for binary runtime dependencies during compile.
    # com.carrotsearch.hppc module-info is missing and not a compile dependency.
    # The provided jar defines an "Automatic-Module-Name" in manifest.
    project.extend_compile_modulepath(compile_deps)
    project.extend_compile_modulepath(runtime_deps)
    project.manifest = Manifest({
        'Manifest-Version'      : '1.0',
        'Extension-Name'        : 'org.apache.lucene',
        'Implementation-Vendor' : 'The Apache Software Foundation',
        'Implementation-Title'  : 'org.apache.lucene',
        'Specification-Vendor'  : 'The Apache Software Foundation',
        'Specification-Version' : '9.10.0',
        'Specification-Title'   : 'Lucene Search Engine: ' + module,
        # TODO (META-INF/versions/*)
        # BLOCKER: (Maybe) Multi-Release source trees can't be handled by refactoring framework yet.
        # 'Multi-Release'         : 'true'
    })
    return project

def xalan_2_7_2():
    xalan_id = ivy.ID('xalan', 'xalan', '2.7.2')
    xalan    = Project('projects/xalan-2.7.2', xalan_id)
    xalan.resources(
        xalan.path / "src/main/java",
        include = ['*'],
        exclude = ['*.java', '*.html', '*.src', '*.lex', '*.inc', '*.cup']
    )
    xalan.resources(
        xalan.path / "src/main/resources",
        include = ['*'],
    )
    xalan.sources(
        xalan.path / "src/main/java",
        include = ['*.java']
    )
    libs = [
        Path(os.getcwd()) / xalan.path / 'lib/BCEL.jar',
        Path(os.getcwd()) / xalan.path / 'lib/runtime.jar',
        Path(os.getcwd()) / xalan.path / 'lib/java_cup.jar',
        Path(os.getcwd()) / xalan.path / 'lib/regexp.jar'
    ]
    # TODO: Move this check somewhere where we can validate classpath entries.
    # TODO: Add these as transitive project build properties:
    #       - classpath.compile.extras  // Add only to compile classpath
    #       - classpath.runtime.extras  // Add only to runtime classpath
    #       - classpath.extras          // Add to compile and runtime classpaths
    for l in libs:
        if not l.exists():
            raise ValueError('File not found!', str(l))
    libs = [ str(l) for l in libs ]
    xalan.extend_compile_classpath(ivy.cache().resolve_dependencies(xalan_id, ['compile,optional']) + libs)
    xalan.extend_runtime_classpath(ivy.cache().resolve_dependencies(xalan_id, ['runtime,optional']) + libs)
    xalan.manifest = Manifest({
        "Manifest-Version"        : "1.0",
        "Created-By"              : "Daivy",
        "Implementation-Title"    : "org.apache.xalan",
        "Implementation-Version"  : "2.7.2",
        "Implementation-Vendor-Id": "org.apache.xalan",
        "Implementation-Vendor"   : "Apache Software Foundation",
        "Main-Class"              : "org.apache.xalan.xslt.Process",
        'Class-Path'              : xalan.classpath_attribute_value()
        # Depends on runtime classpath being set.
        # TODO: We can compute Class-Path here instead, no need to set runtime dependencies on project.
        #       Also, we don't need this manifest since we are not going to invoke as standalone jar.
    })
    return xalan

def jacop_4_10_0():
    jacop_id = ivy.ID('org.jacop', 'jacop', '4.10.0')
    jacop    = Project('projects/jacop-4.10.0', jacop_id)
    jacop.sources(
        jacop.path / "src/main/java",
        include = ['*.java']
    )
    # Include test sources. Requires 'test' dependencies. (TODO: Should we split compilation into main and test?)
    #jacop.sources(
    #    jacop.path / "src/test/java",
    #    include = ['*.java']
    #)
    jacop.extend_compile_classpath(ivy.cache().resolve_dependencies(jacop_id, ['compile', 'test']))
    jacop.extend_runtime_classpath(ivy.cache().resolve_dependencies(jacop_id, ['runtime']))
    jacop.manifest = Manifest({
        "Manifest-Version"        : "1.0",
        "Created-By"              : "Daivy",
        "Implementation-Title"    : "org.jacop:jacop",
        "Implementation-Version"  : "4.10.0",
        "url"                     : "http://jacop.osolpro.com"
    })
    return jacop

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required = True,
        help = "Coordinate of project to operate on")
    parser.add_argument('--context', required = True,
        help = "Build context folder for export/import")
    parser.add_argument('--export' , required = False, action = "store_true",
        help = "Export project source code and eclipse configuration")
    parser.add_argument('--export-path', required = False,
        help = "Path to folder into which the export archive is written.")
    parser.add_argument('--clean', required = False, action = "store_true",
        help = "Clean project before building")
    parser.add_argument('--verbose', required = False, action = "store_true",
        help = "Print extra information during execution")
    parser.add_argument('--info', required = False,
        help = "Folder into which 'build-order.txt' and 'source-projects.txt' are written if specified")
    parser.add_argument('--import-path', required = False,
        help = "Import folder with patched '-build.zip' files.")
    parser.add_argument('--target-version', required = False,
        help = "The target version to use when compiling source code")
    args = parser.parse_args()

    if args.verbose:
        print("Using build context")
        print("  path = " + args.context)

    Project._global_build_context = BuildContext(args.context, args)

    projects = {
        # Note
        # The 'dacapo' prefix in the following project coordinates is intended
        # to show that the project is a benchmark based on the benchmark harness
        # provided by dacapobench, which means that the executable benchmark jar
        # files have the same command line interface.
        #
        # Benchmark modules are served from a local provider overriding external providers.
        #
        # Note
        # If it is not possible to find a project through an external provider,
        # an override can be placed in the local provider. I have used this on
        # occasions where upstream ivy or pom files have errors which prevents
        # ivy from installing the module.

        # The following benchmarks are also provided by the referenced dacapobench version:
        'dacapo:batik:1.0'                                : lambda: bm_build('batik'),
        'dacapo:luindex:1.0'                              : lambda: bm_build('luindex'),
        'dacapo:lusearch:1.0'                             : lambda: bm_build('lusearch'),
        'dacapo:xalan:1.0'                                : lambda: bm_build('xalan'),

        # The following benchmarks are provided by this suite.
        'dacapo:jacop:1.0'                                : lambda: bm_build('jacop'),

        # The following projects are libraries referenced by benchmark projects.
        'org.apache.xmlgraphics:batik-all:1.16'           : batik_1_16,
        'org.apache.lucene:lucene-analysis-common:9.10.0' : lambda: lucene_9_10_0('analysis-common'),
        'org.apache.lucene:lucene-backward-codecs:9.10.0' : lambda: lucene_9_10_0('backward-codecs'),
        'org.apache.lucene:lucene-core:9.10.0'            : lambda: lucene_9_10_0('core'),
        'org.apache.lucene:lucene-codecs:9.10.0'          : lambda: lucene_9_10_0('codecs'),
        'org.apache.lucene:lucene-demo:9.10.0'            : lambda: lucene_9_10_0('demo'),
        'org.apache.lucene:lucene-expressions:9.10.0'     : lambda: lucene_9_10_0('expressions'),
        'org.apache.lucene:lucene-facet:9.10.0'           : lambda: lucene_9_10_0('facet'),
        'org.apache.lucene:lucene-queries:9.10.0'         : lambda: lucene_9_10_0('queries'),
        'org.apache.lucene:lucene-queryparser:9.10.0'     : lambda: lucene_9_10_0('queryparser'),
        'org.apache.lucene:lucene-sandbox:9.10.0'         : lambda: lucene_9_10_0('sandbox'),
        'xalan:xalan:2.7.2'                               : xalan_2_7_2,
        'org.jacop:jacop:4.10.0'                          : jacop_4_10_0,
    }

    if not args.project in projects:
        raise ValueError("Missing build for specified project", args.project)

    if args.verbose:
        print("Computing build order ...")

    build_order = ivy.cache().compute_build_order(
        ivy.ID.from_coord(args.project),
        verbose = args.verbose,
        depth_limit = 6
    )

    if args.verbose:
        print("Build order" + os.linesep + os.linesep.join([
            "  " + p.coord() for p in build_order if p.coord() in projects
        ]))

    if args.info:
        info_dir = Path(args.info)
        if not info_dir.is_dir():
            raise ValueError("Expected info to be a directory", args.info)
        with open(info_dir / 'build-order.txt', 'w') as build_order_txt:
            with open(info_dir / 'source-projects.txt', 'w') as source_projects_txt:
                for p in build_order:
                    pc = p.coord()
                    build_order_txt.write(pc + os.linesep)
                    if pc in projects:
                        source_projects_txt.write(pc + os.linesep)

    for coord in [id.coord() for id in build_order]:
        if coord in projects:
            project = projects[coord]()
            project.build(args.clean)

    # Note that 'export' depends on 'build' to generate 'build.zip'
    # in each source project. All source projects associated with
    # the specified project are held by build_order.
    if args.export:
        if args.export_path:
            ep = Path(args.export_path)
            if not ep.is_dir():
                raise ValueError("Export path must be a directory.")
            for p in build_order:
                pc = p.coord()
                if args.verbose:
                    if pc in projects:
                        print("[export] Exporting", pc, "into", str(ep))
                    else:
                        print("[export] No source available for project", pc)
                if pc in projects:
                    projects[pc]().export(ep)
        else:
            raise ValueError('The --export action requires option --export-path <folder>')

