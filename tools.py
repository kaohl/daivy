#!/bin/env python3

import hashlib
from pathlib import Path
import shutil
import subprocess
import zipfile
from zipfile import ZipFile

def cwd_prefix(cwd):
    return '../' * len(cwd.parts)

def javacc_7_0_12(rel_cwd_path, options_map, inputfile_list, verbose = False):
    parts = [
        'java',
        '-cp',
        cwd_prefix(rel_cwd_path) + 'tools/javacc-7.0.12/javacc.jar',
        'javacc'
    ]
    options_list = [
        '-' + "=".join([opt, val]) for (opt, val) in options_map.items()
    ]
    command = " ".join(parts + options_list + inputfile_list)
    if verbose:
        print("[run]", command)
    subprocess.run(command, shell = True, cwd=rel_cwd_path)

def unzip(src, dst):

    if not zipfile.is_zipfile(src):
        raise ValueError('Specified file is not a zip file', src)

    with ZipFile(src, 'r') as z:
        print('[run] unzip', src, 'into', dst)
        z.extractall(dst)

    return dst

def zip(src, dst):
    if dst.suffix == '.zip':
        dst = dst.parent / dst.stem
    print("[run] zip", src, dst)
    shutil.make_archive(dst, 'zip', src)

def jar(src, dst):
    zip(src, dst)
    shutil.move(str(dst) + '.zip', dst)

def patch(src, dst):
    print("[run] patch", src, dst)

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

