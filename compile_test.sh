#!/bin/bash
cd server
echo "Building server..."
make clean 2>&1
make 2>&1
echo "Build status: $?"
