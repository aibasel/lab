#!/bin/bash
# Automatically rebuild Sphinx documentation upon file change

DOCS="$( dirname "$0" )"
REPO="$DOCS/../"

# Make html documentation
make -C "$DOCS" html

# Open documentation in browser
xdg-open "$DOCS/_build/html/index.html"

while :; do
    # Wait for changes
    inotifywait -e modify,create,delete -r "$REPO"
    # Make html documentation
    make -C "$DOCS" html
done
