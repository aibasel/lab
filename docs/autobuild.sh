#! /bin/bash
# Automatically rebuild Sphinx documentation when files change.

DOCS="$( dirname "$0" )"
REPO="$DOCS/../"

cd "$REPO/docs"

# Build html documentation.
make html

# Open documentation in browser.
xdg-open "$DOCS/_build/html/index.html"

while :; do
    # Wait for changes.
    inotifywait -e modify,create,delete -r "$REPO"
    # Build html documentation.
    make html
done
