#!/bin/bash
SCRIPT_HOME=./bin
SCRIPT_CONFIG=./dev/config.yaml
export SCRIPT_HOME SCRIPT_CONFIG PYTHONUNBUFFERED=1

./bin/aiproxy.py "$@"