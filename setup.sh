#!/bin/env bash

# This script will clone dacapobench into the current directory,
# checkout the specified commit, and extract resources from the
# source tree.

if [ ! -d dacapobench ]; then
    git clone https://github.com/dacapobench/dacapobench.git
    cd dacapobench
    git checkout 59ab7e97cec32d9d87559db3db02c28bcb3006ab
    cd -
fi

if [ ! -d context ]; then
    mkdir context
fi

./extract-resources.py

