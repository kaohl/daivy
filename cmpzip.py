#!/bin/env python3

import argparse
import io
import os
import sys
import zipfile

# Return 0 if nameslists in specified zip files are the same.
# Otherwise, return 1.
def compare_zip_namelists(file1, file2):
    if file1 == file2:
        return 0

    same = True
    with zipfile.ZipFile(file1) as z1:
        z1_names = z1.namelist()
        z1_nameset = set(z1.namelist())
        with zipfile.ZipFile(file2) as z2:
            z2_names = z2.namelist()
            z2_nameset = set(z2.namelist())

            out = io.StringIO()
            for n in z1_names:
                if not n in z2_nameset:
                    out.write('  ' + n + os.linesep)

            if out.tell() > 0:
                same = False
                print(file1, 'extra')
                print(out.getvalue())
                out = io.StringIO()

            for n in z2_names:
                if not n in z1_nameset:
                    out.write('  ' + n + os.linesep)

            if out.tell() > 0:
                same = False
                print(file2, 'extra' + os.linesep + out.getvalue())

    return 0 if same else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file1', required = True)
    parser.add_argument('-g', '--file2', required = True)
    args = parser.parse_args()
    sys.exit(compare_zip_namelists(args.file1, args.file2))

