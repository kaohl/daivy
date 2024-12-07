#!/bin/env python3

import copy
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import zipfile

import ivy_cache_resolver as ivy

# Validate MD5 checksum of specified file.
# Note: If the origin of the file does not provide an MD5 checksum,
#       download the file and verify it using recommended method,
#       then compute an MD5 sum of the same file and used that
#       as argument to this function.
def validate_file(target, md5):
    with open(target, "rb") as f:
        digest = hashlib.file_digest(f, "md5")
        if md5 != digest.hexdigest():
            raise ValueError(
                "Invalid file checksum",
                target,
                "Expected MD5 to be",
                md5,
                "but found",
                digest.hexdigest()
            )
        print("Validation succeeded for file", str(target))

# Fetch specified file from url with optional MD5 validation.
# Return path to the downloaded resource.
def fetch(url, file, md5 = None, cache = Path('downloads')):

    if not cache.exists():
        cache.mkdir(exist_ok = True, parents = True)

    file = cache / file

    # Note: Fetch using 'wget' to avoid 'user-agent'
    #       issues with http requests from urllib.

    if not file.exists():
        print("Fetching", file, "from", url)
        subprocess.run(
            " ".join(['wget', '--no-clobber', '--output-document=' + str(file), url]), shell = True
        )
    else:
        print("Fetching", file.parts[-1], "from", file)

    if not file.exists():
        raise ValueError('Could not download file', url, str(file))

    if md5 is not None:
        validate_file(file, md5)

    return file

def unzip(src, dst):

    suffix = src.suffix
    if not (suffix == '.zip' or suffix == '.jar'):
        raise ValueError('Specified file is not a zip file', src)

    target = None
    with ZipFile(src, 'r') as z:
        name = z.namelist()[0]
        if name.endswith('/'):
            target = dst / name
        else:
            default_target = src.name[0:-len(src.suffix)]
            target         = dst / default_target

        print('Unzip', src, 'into', target)

        if not target.exists():
            z.extractall(target)

    return target

def extract_lib_batik():
    url = 'https://archive.apache.org/dist/xmlgraphics/batik/source'
    src = 'batik-src-1.16.zip'
    md5 = 'b40dedda815115a98aa334d90c6c312c'

    # Download and unpack into build

    build = Path('build')

    if not build.exists():
        build.mkdir()

    source = fetch(url + '/' + src, src, md5)
    root   = unzip(source, build)

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

    ## Collect all external (non-batik) dependencies
    ## since we have merged all batik source roots
    ## into the same source tree (batik-all).
    # non_batik_dependencies = []

    for mod in mods:
        module_root = root / mod
        module_src  = module_root / 'src'
        module_id   = ivy.ID('org.apache.xmlgraphics', mod, '1.16')
        module      = ivy_cache.resolve(module_id)

        #for dep_xml in module.load_xml().findall('.//dependency'):
        #    if dep_xml.get('mod').startswith('batik-'):
        #        continue
            #d_id = ivy.ID(
            #    dep_xml.get('org'),
            #    dep_xml.get('mod'),
            #    dep_xml.get('rev')
            #)
            #non_batik_dependencies.append(copy.deepcopy(dep_xml))

        print("Copy", module_src, batik_1_16_src)
        shutil.copytree(module_src, batik_1_16_src, dirs_exist_ok = True)

# TODO: Not sure whether we actually need this. See compile.py.
#    with open(batik_1_16 / 'ivy.xml', 'w') as xml:
#
#        # TODO
#        #   See build/batik-1.16/lib/ and 'build.xml'.
#        #   Some extra dependencies are provided and used in the build script.
#        #
#        # xalan:serializer:2.7.2 (MD5 e8325763fd4235f174ab7b72ed815db1)
#        #

def extract_bms_batik():
    base = 'https://download.dacapobench.org'
    data = base + '/chopin/data'
    file = 'batik-data.zip'
    md5  = '55fb9674f17157c7ea88381219c951d9'

    build = Path('build')

    if not build.exists():
        build.mkdir()

    filepath  = fetch(data + '/' + file, file, md5)
    data_root = unzip(filepath, build)

    bm             = 'batik'
    src_bms        = Path('dacapobench/benchmarks/bms')
    src_bm         = src_bms / bm
    src_bm_cnf     = src_bm  / (bm + '.cnf')
    src_bm_harness = src_bm  / 'harness'

    dst_bm          = Path('projects') / bm
    dst_bm_harness  = dst_bm / 'harness'
    dst_bm_cnf      = dst_bm / (bm + '.cnf')
    dst_bm_data     = dst_bm / 'data'
    dst_bm_data_dat = dst_bm / 'data' / 'dat'

    shutil.copytree(data_root, dst_bm_data_dat, dirs_exist_ok = True)
    shutil.copytree(src_bm_harness, dst_bm_harness, dirs_exist_ok = True)
    shutil.copy2(src_bm_cnf, dst_bm_cnf)

    # ivy_batik = dst_bm / 'ivy.xml'

    # TODO

def extract_harness():

    # Note
    #   The test harness (dacapo harness) is built as a separate
    #   jar allowing the harness (dacapo) main class to load it
    #   in a dedicated classloader which then bootstraps the
    #   specified benchmark from the benchmark configuration
    #   file.

    # Project: dacapo harness

    src_harness = Path('dacapobench/benchmarks/harness')
    dst_harness = Path('dacapo/harness')
    shutil.copytree(src_harness, dst_harness, dirs_exist_ok = True)

    # Dependencies of dacapo harness.
    ivy_harness = Path('dacapo/harness/ivy.xml')

    # Project: dacapo

    src_src = Path('dacapobench/benchmarks/src')
    dst_src = Path('dacapo/dacapo/src')
    shutil.copytree(src_src, dst_src, dirs_exist_ok = True)

    # Dependencies of dacapo.
    ivy_dacapo = Path('dacapo/dacapo/ivy.xml')

    # TODO

def extract_resources():
    extract_harness()
    extract_lib_batik()
    extract_bms_batik()

if __name__ == '__main__':
    extract_resources()

