#!/bin/env python3

import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from zipfile import ZipFile
import zipfile
from ivy_cache_resolver import IvyCache, IvyId

# Validate MD5 sum of downloaded file.
# Compute MD5 sum from verified archive if not specified at origin.
def validate_file(target, md5):
    with open(target, "rb") as f:
        digest = hashlib.file_digest(f, "md5")
        if md5 != digest.hexdigest():
            raise ValueError(
                "Invalid file",
                target,
                "Expected MD5 to be",
                md5,
                "but found",
                digest.hexdigest()
            )

def download(url, filename, md5):
    cache  = Path('downloads')
    target = cache / filename

    if target.exists():
        validate_file(target, md5)
        return target

    if not cache.exists():
        cache.mkdir()

    with urllib.request.urlopen(url + '/' + filename) as response:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            shutil.copyfileobj(response, tmp_file)
            shutil.copy2(tmp_file.name, target)

    validate_file(target, md5)

    return target

def unzip(src, dst):
    target = None
    with ZipFile(src, 'r') as z:
        name   = z.namelist()[0]
        target = dst / name

        print('Unzip', src, 'into', target)

        if not target.exists():
            z.extractall(dst)

    return target

def source_root(url, src, md5):
    src_location = download(url, src, md5)
    build = Path('build')

    if not build.exists():
        build.mkdir()

    src_root = unzip(src_location, build)
    return src_root

def extract_lib_batik():
    url = 'https://archive.apache.org/dist/xmlgraphics/batik/source'
    src = 'batik-src-1.16.zip'
    md5 = 'b40dedda815115a98aa334d90c6c312c'

    # Download and unpack into build

    root = source_root(url, src, md5)

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

    source_modules = set()

    for mod in mods:
        source_modules.add(('org.apache.xmlgraphics', mod, '1.16'))

    ivy = IvyCache()

    external_dependencies = dict()
    
    for mod in mods:
        module_root = root / mod
        module_src  = module_root / 'src'
        module_id   = IvyId('org.apache.xmlgraphics', mod, '1.16')

        ivy_module       = ivy.resolve_module(module_id)
        all_dependencies = ivy_module.dependencies()

        for dep in all_dependencies:
            id = dep.id
            key = (id.org, id.mod, id.rev)
            if not key in source_modules:
                if not key in external_dependencies:
                    print("Dependency", id.org, id.mod, id.rev)
                    external_dependencies[key] = dep

        print("Copy", module_src, batik_1_16_src)
        shutil.copytree(module_src, batik_1_16_src, dirs_exist_ok = True)

    # Collect all external (non-batik) dependencies
    # since we have merged all batik source roots
    # into the same source tree.
    with open(batik_1_16 / 'ivy.xml', 'w') as xml:
        xml.write('<?xml version="1.0" encoding="UTF-8"?>' + os.linesep)
        xml.write('<ivy-module version="2.0" xmlns:m="http://ant.apache.org/ivy/maven">' + os.linesep)
        xml.write('    <info organisation="org.apache.xmlgraphics"' + os.linesep)
        xml.write('          module="batik-all"' + os.linesep)
        xml.write('          revision="1.16"' + os.linesep)
        xml.write('    />' + os.linesep)
        xml.write('    <dependencies>' + os.linesep)
        for xdep in external_dependencies.values():
            xmod = ivy.resolve_module(xdep.id)
            xml.write(
                '        <dependency org="@ORG" name="@MOD" rev="@REV" force="true" conf="@CNF"/>'
                .replace('@ORG', xdep.id.org)
                .replace('@MOD', xdep.id.mod)
                .replace('@REV', xdep.id.rev)
                .replace('@CNF', xdep.conf)
                 + os.linesep
            )
        xml.write('    </dependencies>' + os.linesep)
        xml.write('</ivy-module>' + os.linesep)

def extract_bms_batik():
    pass
    
def extract_harness():
    pass

def extract_resources():
    extract_harness()
    extract_lib_batik()
    extract_bms_batik()

if __name__ == '__main__':
    extract_resources()
