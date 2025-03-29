#!/bin/bash

if [ "$1" = "" ]; then
    echo "Please specify a folder name."
    exit 1
fi

#for f in `find $1 -iname *~`; do
#    rm "$f"
#done

if [ ! -d "$1" ]; then
    echo "There is no folder named '$1' in the current directory."
    exit 1
fi

rm     "$1.zip"
cd     "$1"
zip -r ../"$1.zip" *
zip -d ../"$1.zip" "*~"
md5sum ../"$1.zip"
cd     -
