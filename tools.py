#!/bin/env python3

import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile
from zipfile import ZipFile

def cwd_prefix(cwd):
    return '../' * len(cwd.parts)

def javacc(rel_cwd_path, options_map, inputfile_list, verbose, javacc_jar, command):
    parts = [
        'java',
        '-cp',
        cwd_prefix(rel_cwd_path) + javacc_jar,
        command
    ]
    options_list = [
        '-' + "=".join([opt, val]) for (opt, val) in options_map.items()
    ]
    cmd = " ".join(parts + options_list + inputfile_list)
    if verbose:
        print("[javacc {}]".format(command), cmd)
    subprocess.run(
        cmd,
        shell      = True,
        executable = '/bin/bash',
        cwd        = rel_cwd_path
    )

def javacc_jjtree_7_0_12(rel_cwd_path, options_map, inputfile_list, verbose = False):
    javacc(
        rel_cwd_path,
        options_map,
        inputfile_list,
        verbose,
        'tools/javacc-7.0.12/javacc.jar',
        'jjtree'
    )

def javacc_7_0_12(rel_cwd_path, options_map, inputfile_list, verbose = False):
    javacc(
        rel_cwd_path,
        options_map,
        inputfile_list,
        verbose,
        'tools/javacc-7.0.12/javacc.jar',
        'javacc'
    )

def javacc_jjtree_4_2(rel_cwd_path, options_map, inputfile_list, verbose = False):
    javacc(
        rel_cwd_path,
        options_map,
        inputfile_list,
        verbose,
        'tools/javacc-4.2/bin/lib/javacc.jar',
        'jjtree'
    )

def javacc_4_2(rel_cwd_path, options_map, inputfile_list, verbose = False):
    javacc(
        rel_cwd_path,
        options_map,
        inputfile_list,
        verbose,
        'tools/javacc-4.2/bin/lib/javacc.jar',
        'javacc'
    )

def javacc_jjtree_5_0(rel_cwd_path, options_map, inputfile_list, verbose = False):
    javacc(
        rel_cwd_path,
        options_map,
        inputfile_list,
        verbose,
        'tools/javacc-5.0/javacc-5.0.jar',
        'jjtree'
    )

def javacc_5_0(rel_cwd_path, options_map, inputfile_list, verbose = False):
    javacc(
        rel_cwd_path,
        options_map,
        inputfile_list,
        verbose,
        'tools/javacc-5.0/javacc-5.0.jar',
        'javacc'
    )

def untar(src, dst):
    if not tarfile.is_tarfile(src):
        raise ValueError('Specified file is not a tar file', str(src))

    with tarfile.open(src, 'r:*') as t:
        print('[untar]', src, 'into', dst)
        t.extractall(dst)

    return dst

def unzip(src, dst):

    if not zipfile.is_zipfile(src):
        raise ValueError('Specified file is not a zip file', src)

    with ZipFile(src, 'r') as z:
        print('[unzip]', src, 'into', dst)
        z.extractall(dst)

    return dst

def _zip(src, dst):
    if src is None or dst is None:
        raise ValueError('Cannot zip', src, dst)
    if dst.suffix == '.zip':
        dst = dst.parent / dst.stem
    print("[zip]", str(src), str(dst))
    shutil.make_archive(dst, 'zip', src)

def zip(src, dst):
    _zip(src, dst) # Call internal.

def jar(src, dst):
    print("[jar]", str(src), str(dst))
    _zip(src, dst) # Call internal to avoid collision with builtin 'zip'.
    shutil.move(str(dst) + '.zip', dst)

def patch(src, dst):
    print("[patch]", src, dst)

def digest(target, alg = 'md5'):
    print("[digest " + alg + "]", str(target))
    with open(target, "rb") as f:
        digest = hashlib.file_digest(f, alg)
        return digest.hexdigest()

def compute_md5(target):
    return digest(target, 'md5')

def is_md5(target, md5):
    return md5 == compute_md5(target)

# Validate MD5 checksum of specified file.
# Note: If the origin of the file does not provide an MD5 checksum,
#       download the file and verify it using recommended method,
#       then compute an MD5 sum of the same file and used that
#       as argument to this function.
def validate_file(target, md5):
    digest = compute_md5(target)
    is_valid = md5 is None or md5 == digest
    if not is_valid:
        raise ValueError(
            "Invalid file checksum",
            target,
            "Expected MD5 to be",
            md5,
            "but found",
            digest
        )
    elif is_valid:
        print("Validation succeeded for file", str(target), "(" + ("unchecked" if md5 is None else "checked") + ")")
    return is_valid

# Fetch specified file from url with optional MD5 validation.
# Return path to the downloaded resource.
def fetch(url, file, md5 = None, cache = Path('downloads')):

    if not cache.exists():
        cache.mkdir(exist_ok = True, parents = True)

    file = cache / file

    # Note: Fetch using 'wget' to avoid 'user-agent'
    #       issues with http requests from urllib.

    # Fetch if not exists or try to resume if the fetch was not completed.
    if file.exists():
        print("Validating cached file", file)
    continue_download = md5 is not None and file.exists() and not is_md5(file, md5)
    if not file.exists() or continue_download:
        print("Fetching", file, "from", url, "(" + ("continue" if continue_download else "fetch") + ")")
        cmd = " ".join([
            'wget',
            ('-c' if continue_download else '--no-clobber'),
            '--output-document=' + str(file),
            url
        ])
        subprocess.run(
            cmd,
            shell      = True,
            executable = '/bin/bash'
        )
    else:
        print("Fetching", file.parts[-1], "from", file)

    if not file.exists():
        raise ValueError('Could not download file', url, str(file))

    if md5 is not None:
        validate_file(file, md5)

    return file

