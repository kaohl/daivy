from pathlib import Path
import shutil

import tools
import ivy_cache_resolver as ivy


def extract_lib_lucene():
    url = 'https://archive.apache.org/dist/lucene/java/9.10.0'
    src = 'lucene-9.10.0-src.tgz'
    md5 = '1d8b8bcc374c1aeb77de1da7393352cc'

    # Download and unpack into build

    build = Path('build')

    if not build.exists():
        build.mkdir()

    source = tools.fetch(url + '/' + src, src, md5)
    root   = tools.untar(source, build)

    mods = [
        ('analysis-common', 'analysis/common'),
        ('backward-codecs', None),
        ('core'           , None),
        ('codecs'         , None),
        ('demo'           , None),
        ('expressions'    , None),
        ('facet'          , None),
        ('queries'        , None),
        ('queryparser'    , None),
        ('sandbox'        , None)
    ]

    ivy_cache = ivy.Cache()
    projects  = Path('projects')

    for mod, modpath in mods:
        modpath = modpath if not modpath is None else mod
        module_root = root / 'lucene-9.10.0' / 'lucene' / modpath
        module_src  = module_root / 'src/java'
        module_rrc  = module_root / 'src/resources'
        module_id   = ivy.ID('org.apache.lucene', 'lucene-' + mod, '9.10.0')
        module      = ivy_cache.resolve(module_id)

        dst_mod     = projects / ('lucene-' + mod + '-9.10.0')
        dst_mod_src = dst_mod / 'src/main/java'
        dst_mod_rrc = dst_mod / 'src/main/resources'

        if dst_mod.exists():
            shutil.rmtree(dst_mod)

        if not dst_mod_src.exists():
            dst_mod_src.mkdir(parents = True)

        print("Copy", module_src, dst_mod_src)
        shutil.copytree(module_src, dst_mod_src, dirs_exist_ok = True)

        if module_rrc.exists():
            if not dst_mod_rrc.exists():
                dst_mod_rrc.mkdir(parents = True)

            print("Copy", module_rrc, dst_mod_rrc)
            shutil.copytree(module_rrc, dst_mod_rrc, dirs_exist_ok = True)

