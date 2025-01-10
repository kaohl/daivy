from pathlib import Path
import shutil

import ivy_cache_resolver as ivy
import tools

def extract_lib_xalan():
    url = 'https://archive.apache.org/dist/xalan/xalan-j/source'
    src = 'xalan-j_2_7_2-src.tar.gz'
    md5 = '74e6ab12dda778a4b26da67438880736'

    # Download and unpack into build

    build = Path('build')

    if not build.exists():
        build.mkdir()

    source = tools.fetch(url + '/' + src, src, md5)
    root   = tools.untar(source, build) / 'xalan-j_2_7_2'

    ivy_cache = ivy.Cache()
    projects  = Path('projects')

    src = root / 'src'
    id  = ivy.ID('xalan', 'xalan', '2.7.2')
    mod = ivy_cache.resolve(id) # Download

    dst     = projects / 'xalan-2.7.2'
    dst_lib = dst      / 'lib'
    dst_src = dst      / 'src/main/java'
    dst_rrc = dst      / 'src/main/resources'

    if dst.exists():
        shutil.rmtree(dst)

    dst_src.mkdir(parents = True)
    dst_rrc.mkdir(parents = True)
    dst_lib.mkdir(parents = True)

    lib  = root / 'lib'
    libs = ['BCEL.jar', 'runtime.jar', 'regexp.jar']

    for l in libs:
        s = lib     / l
        d = dst_lib / l
        print("Copy", s, d)
        shutil.copy2(s, d)

    # TODO: Do we also need JLex?
    cup = root / 'tools' / 'java_cup.jar'
    print("Copy", cup, dst_lib)
    shutil.copy2(cup, dst_lib)

    for sdir in [ 'org', 'trax' ]:
        s = src / sdir
        d = dst_src / sdir
        print("Copy", s, d)
        shutil.copytree(s, d, dirs_exist_ok = True)

    src_meta_inf = src     / 'META-INF'
    dst_meta_inf = dst_rrc / 'META-INF'
    print("Copy", src_meta_inf, dst_meta_inf)
    shutil.copytree(src_meta_inf, dst_meta_inf, dirs_exist_ok = True)

