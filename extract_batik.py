from pathlib import Path
import shutil

import ivy_cache_resolver as ivy
import tools

def extract_lib_batik():
    url = 'https://archive.apache.org/dist/xmlgraphics/batik/source'
    src = 'batik-src-1.16.zip'
    md5 = 'b40dedda815115a98aa334d90c6c312c'

    # Download and unpack into build

    build = Path('build')

    if not build.exists():
        build.mkdir()

    source = tools.fetch(url + '/' + src, src, md5)
    root   = tools.unzip(source, build)

    # Extract resources from source tree

    mods = [
        'batik-all',
        'batik-anim',
        'batik-awt-util',
        'batik-bridge',
        'batik-codec',
        'batik-constants',
        'batik-css',
        'batik-dom',
        'batik-ext',
        'batik-extension',
        'batik-gui-util',
        'batik-gvt',
        'batik-i18n',
        'batik-parser',
        'batik-rasterizer',
        'batik-rasterizer-ext',
        'batik-script',
        'batik-shared-resources',
        'batik-slideshow',
        'batik-squiggle',
        'batik-squiggle-ext',
        'batik-svgbrowser',
        'batik-svg-dom',
        'batik-svggen',
        'batik-svgpp',
        'batik-svgrasterizer',
        'batik-swing',
        'batik-transcoder',
        'batik-ttf2svg',
        'batik-util',
        'batik-xml'
    ]

    projects = Path('projects')

    batik_1_16     = projects / 'batik-1.16'
    batik_1_16_src = batik_1_16 / 'src'

    if not projects.exists():
        projects.mkdir()

    if not batik_1_16.exists():
        batik_1_16.mkdir()

    if not batik_1_16_src.exists():
        batik_1_16_src.mkdir()

    ivy_cache = ivy.Cache()

    for mod in mods:
        module_root = root / 'batik-1.16' / mod
        module_src  = module_root / 'src'
        #module_id   = ivy.ID('org.apache.xmlgraphics', mod, '1.16')
        #module      = ivy_cache.resolve(module_id)

        # TODO: Consider this...
        #for dep_xml in module.load_xml().findall('.//dependency'):
        #    if dep_xml.get('mod').startswith('batik-'):
        #        continue
        #    d_id = ivy.ID(dep_xml.get('org'), dep_xml.get('mod'), dep_xml.get('rev'))
        #    non_batik_dependencies.append(copy.deepcopy(dep_xml))

        print("Copy", module_src, batik_1_16_src)
        shutil.copytree(module_src, batik_1_16_src, dirs_exist_ok = True)

    bp = ivy.blueprint()
    bp.id(ivy.ID('org.apache.xmlgraphics', 'batik-all', '1.16'))
    bp.artifact({ 'name' : "batik-all", 'type' : "jar", 'ext' : "jar", 'conf' : "master" })

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
        ivy.ID("xml-apis", "xml-apis", "1.4.01"),
        ivy.ID("xml-apis", "xml-apis-ext", "1.3.04"),
        ivy.ID("org.apache.xmlgraphics", "xmlgraphics-commons", "2.7"),
        ivy.ID("commons-io", "commons-io", "1.3.1"),
        ivy.ID("commons-logging", "commons-logging", "1.0.4"),
        # TODO: Optional configuration (not handled in 'build.py' yet)
        ivy.ID("org.mozilla", "rhino", "1.7.7"),
        ivy.ID("org.python", "jython", "2.7.0")
    ]
    for dep_id in dependencies:
        bp.dep(dep_id, { 'force': 'true', 'conf': 'compile->master(*);runtime->master(*),runtime(*);test->master(*),runtime(*)' })

    ivy.ResolverModule.add_module(bp.build())

    # TODO
    #   See build/batik-1.16/lib/ and 'build.xml'.
    #   Some extra dependencies are provided and used in the build script.
    #
    #   xalan:serializer:2.7.2 (MD5 e8325763fd4235f174ab7b72ed815db1)
    #
