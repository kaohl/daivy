import os
from pathlib import Path
import shutil

import ivy_cache_resolver as ivy
import tools

def install_dependencies():
    # The following dependency is missing:
    #
    #   org.apache.logging.log4j/log4j-api-java9/ivy-2.11.2.xml
    #
    # The issue seems to be that the java9 version is not
    # distributed separately on this coordinate. Instead,
    # there is a multi-release jar available here:
    #
    #   org.apache.logging.log4j/log4j-api/ivy-2.11.2.xml
    #
    # To solve this issue we generate a fake interface
    # dependency using the missing coordinate that then
    # transitively add the correct dependency.

    bp = ivy.blueprint()
    bp.id(ivy.ID('org.apache.logging.log4j', 'log4j-api-java9', '2.11.2'))
    bp.artifact(None)
    # Configuration (copy-paste; see original batik-all 'ivy.xml')
    bp.conf({ 'name' : "default", 'visibility' : "public", 'extends' : "runtime,master",
              'description' : "runtime dependencies and master artifact can be used with this conf" })
    bp.conf({ 'name' : "master", 'visibility' : "public",
              'description' : "contains only the artifact published by this module itself, with no transitive dependencies" })
    bp.conf({ 'name' : "compile", 'visibility' : "public",
              'description' : "this is the default scope, used if none is specified. Compile dependencies are available in all classpaths." })
    bp.conf({ 'name' : "provided", 'visibility' : "public",
              'description' : "this is much like compile, but indicates you expect the JDK or a container to provide it. It is only available on the compilation classpath, and is not transitive." })
    bp.conf({ 'name' : "runtime", 'visibility' : "public", 'extends' : "compile",
              'description' : "this scope indicates that the dependency is not required for compilation, but is for execution. It is in the runtime and test classpaths, but not the compile classpath."})
    bp.conf({ 'name' : "test", 'visibility' : "public", 'extends' : "runtime",
              'description' : "this scope indicates that the dependency is not required for normal use of the application, and is only available for the test compilation and execution phases." })
    bp.conf({ 'name' : "system", 'visibility' : "public",
              'description' : "this scope is similar to provided except that you have to provide the JAR which contains it explicitly. The artifact is always available and is not looked up in a repository." })
    bp.conf({ 'name' : "sources", 'visibility' : "public",
              'description' : "this configuration contains the source artifact of this module, if any." })
    bp.conf({ 'name' : "javadoc", 'visibility' : "public",
              'description' : "this configuration contains the javadoc artifact of this module, if any." })
    bp.conf({ 'name' : "optional", 'visibility' : "public",
              'description' : "contains all optional dependencies" })
    dependencies = [
        ivy.ID('org.apache.logging.log4j', 'log4j-api', '2.11.2')
    ]
    for dep_id in dependencies:
        bp.dep(dep_id, { 'force': 'true', 'conf': 'compile->master(*);runtime->master(*),runtime(*);test->master(*),runtime(*)' })

    ivy.ResolverModule.add_module(bp.build())

def extract_lib_jacop():
    url = 'https://github.com/radsz/jacop/archive/refs/tags/4.10.0.zip'
    #url = 'https://github.com/radsz/jacop/archive/refs/tags/4.10.0.tar.gz'
    src = 'jacop-4.10.0.zip'
    md5 = '8d5438dae2581540d7431799d6934bb8'

    build = Path('build')

    if not build.exists():
        build.mkdir()

    # TODO: Is this needed now that we limit depth of recursive dependency loading?
    install_dependencies()

    source = tools.fetch(url, src, md5)
    root   = tools.unzip(source, build) / 'jacop-4.10.0'

    ivy_cache = ivy.Cache()
    projects  = Path('projects')

    src = root / 'src/main/java'
    tst = root / 'src/test/java'
    jjt = root / 'src/main/jjtree'

    id  = ivy.ID('org.jacop', 'jacop', '4.10.0')
    mod = ivy_cache.resolve(id)

    dst     = projects / ('jacop-' + id.rev)
    dst_src = dst      / 'src/main/java'
    dst_tst = dst      / 'src/test/java'
    dst_jjt = dst      / 'src/main/jjtree'

    if dst.exists():
        shutil.rmtree(dst)

    dst_src.mkdir(parents = True)
    dst_tst.mkdir(parents = True)
    dst_jjt.mkdir(parents = True)

    shutil.copytree(src, dst_src, dirs_exist_ok = True)
    shutil.copytree(tst, dst_tst, dirs_exist_ok = True)
    shutil.copytree(jjt, dst_jjt, dirs_exist_ok = True)

    # NOTE
    # When running jjtree and then javacc I get warnings that some files already exist.
    # If I remove those files and try to generate the parser from scratch I get compilation errors.
    # Is the .jjt and .jj files out of sync with pregenerated classes?
    # This is not a blocker, it works fine by just running the tools, but I'm curious where those pregenerated classes came from? 
    #
    #files = [
    #    'SimpleNode.java',
    #    'ASTVarDeclItem.java',
    #    'ASTConstElem.java',
    #    'ASTSolveKind.java',
    #    'ASTIntTiExprTail.java',
    #    'ASTAnnExpr.java',
    #    'ASTScalarFlatExpr.java',
    #    'ASTIntFlatExpr.java',
    #    'ASTVariableExpr.java',
    #    'ASTSolveExpr.java',
    #    'ASTIntLiterals.java',
    #    'ASTSetLiteral.java',
    #    'ASTAnnotation.java'
    #]
    #for file in files:
    #    os.remove(dst_src / 'org/jacop/fz' / file)

    # Run parser generator to generate missing files.
    # JavaCC 5.0 is the version used by javacc maven plugin 2.6
    # which is referenced by jacop-4.10.0 pom.xml.
    tools.javacc_jjtree_5_0(
        projects / 'jacop-4.10.0',
        { 'OUTPUT_DIRECTORY': 'src/main/java/org/jacop/fz' },
        [ 'src/main/jjtree/org/jacop/fz/Parser.jjt' ]
    )
    tools.javacc_5_0(
        projects / 'jacop-4.10.0',
        { 'OUTPUT_DIRECTORY': 'src/main/java/org/jacop/fz' },
        [ 'src/main/java/org/jacop/fz/Parser.jj' ]
    )

