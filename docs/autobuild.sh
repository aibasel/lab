#!/bin/bash
# Automatically rebuild Sphinx documentation upon file change

set -e

DOCS="$( dirname "$0" )"
REPO="$DOCS/../"

while :; do
    # Wait for changes
    inotifywait -e modify,create,delete -r "$REPO"
    # Make html documentation
    make -C "$DOCS" html
done
