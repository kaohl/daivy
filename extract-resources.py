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
import tools

import extract_batik
import extract_lucene
import extract_xalan
import extract_h2

bm_data_files = {
    'batik' : (
        'https://download.dacapobench.org/chopin/data',
        'batik-data.zip',
        '55fb9674f17157c7ea88381219c951d9'
    ),
    'luindex' : (
        'https://download.dacapobench.org/chopin/data',
        'luindex-data.zip',
        '1f7bd66b5869f47ea358829e6128de8c'
    ),
    'lusearch' : (
        'https://download.dacapobench.org/chopin/data',
        'lusearch-data.zip',
        '5723fcb558059c3f794fa7af410e171a'
    ),
    'xalan' : (
        'https://www.w3.org/TR/2001/WD-xforms-20010608',
        'WD-xforms-20010608.zip',
        '1473de8fd3df1ca1780947bc4f317d61'
    ),
    'h2' : (

    )
}

def download_bm_data(name):
    if not name in bm_data_files:
        # In this case, the benchmark driver
        # probably has the workload in code?
        print("Benchmark has no data")
        return

    url  = bm_data_files[name][0]
    file = bm_data_files[name][1]
    md5  = bm_data_files[name][2]
    dst  = Path("build/" + name + "-data")
    src  = tools.fetch(url + '/' + file, file, md5)
    # Data can take a lot of time to unzip
    # so reuse unpacked if exists.
    if not dst.exists():
        tools.unzip(src, dst)
    else:
        print("Reusing existing unpacked data archive", str(dst))
        print("Please manually remove the unpacked data to redeploy from archive")
    return Path(dst)

def extract_bm(name, dependencies):
    bm             = name
    src_bms        = Path('dacapobench/benchmarks/bms')
    src_bm         = src_bms / bm
    src_bm_cnf     = src_bm  / (bm + '.cnf')
    src_bm_harness = src_bm  / 'harness'
    src_bm_src     = src_bm  / 'src'

    dst_bm          = Path('projects') / bm
    dst_bm_harness  = dst_bm / 'harness'
    dst_bm_src      = dst_bm / 'src'
    dst_bm_cnf      = dst_bm / (bm + '.cnf')
    dst_bm_data     = dst_bm / 'data'
    dst_bm_data_dat = dst_bm / 'data' / 'dat'

    if dst_bm.exists():
        shutil.rmtree(dst_bm)

    # Download and unpack data
    # Note: Data is symlinked into deployment to save disk space. See 'build.py'.
    data_root = download_bm_data(name)

    # Extract benchmark driver (harness)
    shutil.copytree(src_bm_harness, dst_bm_harness, dirs_exist_ok = True)

    # Extract benchmark driver (source?)
    if src_bm_src.exists():
        shutil.copytree(src_bm_src, dst_bm_src, dirs_exist_ok = True)

    # Extract benchmark config.
    shutil.copy2(src_bm_cnf, dst_bm_cnf)

    # We append the version to complete the config. See dacapo build.
    # In dacapo, this version string seems to resolve to a string of
    # library versions. See deployment in build context instead.
    with open(dst_bm_cnf, 'a') as f:
        f.write('  version "";')

    # Provide benchmark application through local ivy 'daivy' resolver.
    id = ivy.ID('dacapo', name, '1.0') # TODO: Use dacapo release version?
    bp = ivy.blueprint()
    bp.id(id)
    bp.artifact({ 'name' : name, 'type' : "jar", 'ext' : "jar", 'conf' : "master" })
    bp.conf({ 'name': 'master' })
    bp.conf({ 'name': 'compile' })
    bp.conf({ 'name': 'runtime', 'extends' : 'compile' })
    for dep_id, dep_attrib in dependencies:
        bp.dep(dep_id, dep_attrib)
    ivy.ResolverModule.add_module(bp.build())

def extract_bm_h2():
    attrib = {
        'force': 'true',
        'conf' : 'compile->master(*);runtime->master(*),runtime(*)'
    }
    extract_bm('h2', [
        (ivy.ID('com.h2database', 'h2', '2.2.220'), copy.deepcopy(attrib)),
    ])

def extract_bm_xalan():
    attrib = {
        'force': 'true',
        'conf' : 'compile->master(*);runtime->master(*),runtime(*)'
    }
    extract_bm('xalan', [
        (ivy.ID('xalan', 'xalan', '2.7.2'), copy.deepcopy(attrib)),
    ])

def extract_bm_luindex():
    attrib = {
        'force': 'true',
        'conf' : 'compile->master(*);runtime->master(*),runtime(*)'
    }
    extract_bm('luindex', [
        (ivy.ID('org.apache.lucene', 'lucene-core', '9.10.0')           , copy.deepcopy(attrib)),
        (ivy.ID('org.apache.lucene', 'lucene-demo', '9.10.0')           , copy.deepcopy(attrib)),
        (ivy.ID('org.apache.lucene', 'lucene-queryparser', '9.10.0')    , copy.deepcopy(attrib)),
        (ivy.ID('org.apache.lucene', 'lucene-backward-codecs', '9.10.0'), copy.deepcopy(attrib)),
    ])

def extract_bm_lusearch():
    attrib = {
        'force': 'true',
        'conf' : 'compile->master(*);runtime->master(*),runtime(*)'
    }
    extract_bm('lusearch', [
        (ivy.ID('org.apache.lucene', 'lucene-core', '9.10.0')           , copy.deepcopy(attrib)),
        (ivy.ID('org.apache.lucene', 'lucene-demo', '9.10.0')           , copy.deepcopy(attrib)),
        (ivy.ID('org.apache.lucene', 'lucene-queryparser', '9.10.0')    , copy.deepcopy(attrib)),
        (ivy.ID('org.apache.lucene', 'lucene-backward-codecs', '9.10.0'), copy.deepcopy(attrib)),
    ])

def extract_bm_batik():
    attrib = {
        'force': 'true',
        'conf' : 'compile->master(*);runtime->master(*),runtime(*)'
    }
    extract_bm('batik', [
        (ivy.ID('org.apache.xmlgraphics', 'batik-all', '1.16'), copy.deepcopy(attrib)),
    ])

def extract_harness():

    # The harness is injected into the build of benchmarks
    # and is therefore not an independent project. We can
    # still resolve its dependencies via ivy by adding
    # an interface module.

    # Dacapo (Harness)

    src_src = Path('dacapobench/benchmarks/src')
    dst_src = Path('dacapo/dacapo/src')
    shutil.copytree(src_src, dst_src, dirs_exist_ok = True)

    # Dacapo harness (TestHarness)

    src_harness = Path('dacapobench/benchmarks/harness')
    dst_harness = Path('dacapo/harness')
    shutil.copytree(src_harness, dst_harness, dirs_exist_ok = True)

    id  = ivy.ID('dacapo', 'harness', '1.0')
    bp  = ivy.blueprint()
    bp.id(id)
    bp.artifact(None) # Delete default artifact (interface module).
    bp.conf({'name': 'compile'})
    bp.conf({'name': 'runtime', 'extends': 'compile'})
    dependencies = [
        ivy.ID('javax.xml.bind', 'jaxb-api', '2.3.0'),
        ivy.ID('com.sun.activation','javax.activation','1.2.0'),
        ivy.ID('com.sun.xml.bind','jaxb-core','2.3.0'),
        ivy.ID('com.sun.xml.bind','jaxb-impl','2.3.0'),
        ivy.ID('org.hdrhistogram','HdrHistogram','2.1.12'),
        ivy.ID('com.google.code.java-allocation-instrumenter','java-allocation-instrumenter','3.3.4'),
        ivy.ID('commons-cli','commons-cli','1.5.0')
    ]
    for dep_id in dependencies:
        bp.dep(dep_id, { 'conf': 'compile->master(*);runtime->master(*),runtime(*)'})

    ivy.ResolverModule.add_module(bp.build())

def extract_resources():
    #extract_harness()
    #
    #extract_bm_batik()
    #extract_batik.extract_lib_batik()
    #
    #extract_bm_luindex()
    #extract_bm_lusearch()
    #extract_lucene.extract_lib_lucene()
    #
    #extract_bm_xalan()
    #extract_xalan.extract_lib_xalan()

    extract_bm_h2()
    #extract_h2.extract_lib_h2()

    #print("Uncomment target to extract")

if __name__ == '__main__':
    extract_resources()

