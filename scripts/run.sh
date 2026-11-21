#!/bin/sh
# Rebuild everything from the downloaded pages: ./scripts/run.sh [output.html]
set -e
cd "$(dirname "$0")/.."
OUT="${1:-banished-guide.html}"
python3 -I scripts/extract.py wob/raw wob/db.json
python3 -I scripts/compute.py wob/db.json wob/tools.json
mkdir -p wob/gen
python3 -I scripts/cheat.py wob/db.json wob/tools.json wob/gen/cheatsheet.html
python3 -I scripts/professions.py wob/db.json wob/raw wob/gen/professions.html
python3 -I scripts/homestead.py wob/db.json wob/gen/homestead.html
python3 -I scripts/systems.py wob/db.json wob/raw wob/gen
python3 -I scripts/build.py wob/raw wob/icons guides,wob/gen "$OUT"
