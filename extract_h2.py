from pathlib import Path
import shutil

import ivy_cache_resolver as ivy
import tools

def extract_lib_h2():
    url = 'https://github.com/h2database/h2database/archive/refs/tags/version-2.2.220.tar.gz'
    src = 'h2database-version-2.2.220.tar.gz'
    md5 = 'f27d1e2839c602b305991f1efc324bbf'

    # Download and unpack into build

    build = Path('build')

    if not build.exists():
        build.mkdir()

    source = tools.fetch(url, src, md5)
    root   = tools.untar(source, build) / 'h2database-version-2.2.220'

    print(str(root))

    ivy_cache = ivy.Cache()

    h2  = root / 'h2'
    src = h2   / 'src'

    id = ivy.ID('com.h2database', 'h2', '2.2.220')

    projects = Path('projects')
    dst     = projects / 'h2-2.2.220'
    dst_src = dst      / 'src/main/java'
    dst_rrc = dst      / 'src/main/resources'

    if dst.exists():
        shutil.rmtree(dst)

    dst_src.mkdir(parents = True)
    dst_rrc.mkdir(parents = True)

    for sdir in [ 'org' ]:
        s = src / 'main' / sdir
        d = dst_src / sdir
        print("Copy", s, d)
        shutil.copytree(s, d, dirs_exist_ok = True)

    src_meta_inf = src / 'main' / 'META-INF'
    dst_meta_inf = dst_rrc / 'META-INF'
    print("Copy", src_meta_inf, dst_meta_inf)
    shutil.copytree(src_meta_inf, dst_meta_inf, dirs_exist_ok = True)

    bp = ivy.blueprint()
    bp.id(ivy.ID('com.h2database', 'h2', '2.2.220'))
    bp.artifact({ 'name' : "h2", 'type' : "jar", 'ext' : "jar", 'conf' : "master" })

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
        ivy.ID('javax.servlet', 'javax.servlet-api', '4.0.1'),
        ivy.ID('jakarta.servlet', 'jakarta.servlet-api', '5.0.0'),
        ivy.ID('org.apache.lucene', 'lucene-core', '8.5.2'),
        ivy.ID('org.apache.lucene', 'lucene-analyzers-common', '8.5.2'),
        ivy.ID('org.apache.lucene', 'lucene-queryparser', '8.5.2'),
        ivy.ID('org.slf4j', 'slf4j-api', '1.7.30'),
        ivy.ID('org.osgi', 'org.osgi.core', '5.0.0'),
        ivy.ID('org.osgi', 'org.osgi.service.jdbc', '1.1.0'),
        ivy.ID('org.locationtech.jts', 'jts-core', '1.17.0'),
        ivy.ID('org.ow2.asm', 'asm', '9.4')
    ]
    # These are only needed for compile.
    for dep_id in dependencies:
        bp.dep(dep_id, { 'force': 'true', 'conf': 'compile->master(*)' }) #;runtime->master(*),runtime(*);test->master(*),runtime(*)' })

    ivy.install_local_module(bp.build())

