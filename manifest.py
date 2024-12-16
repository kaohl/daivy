#!/bin/env python3
import argparse
import os
from pathlib import Path
import re

# References
#   https://docs.oracle.com/javase/8/docs/technotes/guides/jar/jar.html

class Manifest:
    _name_pattern = re.compile('^[a-zA-Z0-9][a-zA-Z0-9-_]*$')

    def validate_attribute(k, v):
        if not Manifest._name_pattern.match(k) or k.startswith('From'):
            raise ValueError('Bad name', k, v)
        if not isinstance(v, str):
            raise ValueError('Bad value. Expected a string', k, v)
        i = 0
        for c in v:
            if c in '\r\n\x00':
                rep = { '\r'[0]: 'CR', '\n'[0]: 'LF', '\x00'[0]: 'NUL' }
                raise ValueError('Bad character in value', k, v, rep[c], 'at index', str(i))
            i = i + 1

    def __init__(self, attrib = {}):
        self._attrib  = attrib

    def update(self, attrib):
        for k, v in attrib.items():
            if v is None:
                self._attrib.pop(k, None)
                continue
            Manifest.validate_attribute(k, v)
            self._attrib[k] = v

    def text(self, keys = set()):
        blocks = []
        for k, v in self._attrib.items():
            if len(keys) == 0 or k in keys:
                blocks.append(encode_attribute(k, v))
        return ''.join(blocks)

    def bytes(self, keys = set()):
        return bytes(self.text(keys), encoding='utf-8')

    def store(self, path, keys = set()):
        with open(path, 'wb') as f:
            # Manifest MUST start with version attributes.
            # We pop() them from the dict to force the order
            # and therefore also need to handle re-insertion.
            try:
                man_ver_name = 'Manifest-Version'
                sig_ver_name = 'Signature-Version'
                version = self._attrib.pop(man_ver_name, None)
                sigvers = self._attrib.pop(sig_ver_name, None)
                if not version is None:
                    f.write(bytes(encode_attribute(man_ver_name, version), encoding='utf-8'))
                if not sigvers is None:
                    f.write(bytes(encode_attribute(sig_ver_name, sigvers), encoding='utf-8'))
                f.write(self.bytes(keys))
                if not version is None:
                    self._attrib[man_ver_name] = version
                if not sigvers is None:
                    self._attrib[sig_ver_name] = sigvers
            except:
                if not version is None:
                    self._attrib[man_ver_name] = version
                if not sigvers is None:
                    self._attrib[sig_ver_name] = sigvers
                raise

    def load(path):
        with open(path, "rb") as f:
            return Manifest(decode_lines(f.readlines()))

def encode_attribute(header, value):
    space   = b'\x20'
    newline = b'\x0A'

    b_line   = bytes(header + ': ', encoding='utf-8')
    lines    = []
    i        = 0
    N        = len(value)
    while i < N:
        bs = bytes(value[i], encoding='utf-8')
        if not (len(b_line) + len(bs) < 72):
            lines.append(b_line + newline)
            b_line = space
        b_line = b_line + bs
        i = i + 1
    if len(b_line) > 1:
        lines.append(b_line + newline)
    return ''.join([l.decode('utf-8') for l in lines])

def decode_lines(lines):
    space   = b'\x20'[0]
    newline = b'\x0A'[0]

    i = 0
    b = None
    d = dict()
    N = len(lines)
    while i < N:
        ln = lines[i]
        l0 = ln[0]
        if l0 != newline and l0 != space:
            b  = ln[:-1] # Start attribute line; skip newline
            i  = i + 1
            while i < N:
                ln = lines[i]
                l0 = ln[0]
                if not l0 == space:
                    break
                b = b + ln[1:-1] # Add to line; skip space and newline
                i = i + 1
            l = b.decode('utf-8')
            j = l.find(':')
            k = l[:j]
            v = l[j+2:]
            #print("Read", k, v)
            d[k] = v
        else:
            i = i + 1
    return d

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--attribute", required = True)
    parser.add_argument("-v", "--value"    , required = True)
    parser.add_argument("-p", "--path"     , required = False)
    args = parser.parse_args()

    value = args.value if args.attribute != 'Class-Path' else ' '.join(args.value.split(':'))

    if not args.path is None:
        print("-----", args.path, "-----")
        print(Manifest.load(args.path).text())
        print((12 + len(args.path))*'-')

    print("Encode Attribute")
    print(encode_attribute(args.attribute, value))

    # Usage:
    #   ./manifest.py -a 'Class-Path' -v $(cat tmp_cachepath.txt)
    #   ./manifest.py -a 'Class-Path' -v $(cat tmp_cachepath.txt) --path temp/MANIFEST.MF
