#!/bin/bash

set -e

uv export --no-group dev --no-hashes --format=requirements.txt > requirements.txt
