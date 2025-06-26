from pathlib import Path
import shutil

import ivy_cache_resolver as ivy
import tools

# TODO: We are actually using 2.9.1 for Xalan.
#       Version is based on public ivy-files
#       for Xalan-2.7.2. The original DaCapo
#       build uses 2.8.0 for some reason.

def extract_lib_xerces():
    url = 'https://archive.apache.org/dist/xml/xerces-j/source/'
    src = 'Xerces-J-src.2.8.0.tar.gz'
    md5 = '162d481e901a302eb82eb40ebeb8653e'

    src_tools_tgz = 'Xerces-J-tools.2.8.0.tar.gz'
    md5_tools_tgz = '4206f318b43654552f16a9040bdfa6b4'

    #src_tools_zip = 'Xerces-J-tools.2.8.0.zip'
    #md5_tools_zip = '21bd406b21402ce2e19ba5c305667a88'

    # Download and unpack into build

    build = Path('build')

    if not build.exists():
        build.mkdir()

    source       = tools.fetch(url + '/' + src, src, md5)
    source_tools = tools.fetch(url + '/' + src_tools_tgz, src_tools_tgz, md5_tools_tgz)
    #source_tools = tools.fetch(url + '/' + src_tools_zip, src_tools_zip, md5_tools_zip)

    root = tools.untar(source, build)
    tools.untar(source_tools, build / 'xerces-2_8_0')

    raise ValueError("TODO -- Unfinished")

