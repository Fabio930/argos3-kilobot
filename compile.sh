#!/bin/bash
BUILD_TYPE=Release

rm -rf build
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=${BUILD_TYPE} ../src

make -j ${nproc}