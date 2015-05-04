#!/bin/bash 

export PYTHONPATH=../:../lib

sphinx-apidoc -f -o "source/api" "../"

make html
