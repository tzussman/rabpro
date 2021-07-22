#!/bin/bash

platforms=( osx-64 linux-32 linux-64 win-32 win-64 )
find /opt/anaconda3/conda-bld/osx-64 -name *.tar.bz2 | while read file
do
echo $file
    #conda convert --platform all $file  -o $HOME/conda-bld/
    for platform in "${platforms[@]}"
    do
       conda convert --platform $platform $file  -o /opt/anaconda3/conda-bld/
    done    
done

find /opt/anaconda3/conda-bld/ -name *.tar.bz2 | while read file
do
    echo $file
    anaconda upload $file
done
echo "Building conda package done!"
