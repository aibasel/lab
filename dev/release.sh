#! /bin/bash

set -exuo pipefail

VERSION="$1"
CHANGES="/tmp/lab-$VERSION-changes"

function set_version {
    local version="$1"
    sed -i -e "s/__version__ = \".*\"/__version__ = \"$version\"/" lab/__init__.py
}

cd $(dirname "$0")/../

# Check for uncommited changes.
set +e
git diff --quiet && git diff --cached --quiet
retcode=$?
set -e
if [[ $retcode != 0 ]]; then
    echo "There are uncommited changes:"
    git status
    exit 1
fi

if [[ $(git rev-parse --abbrev-ref HEAD) != main ]]; then
    echo "Must be on main branch for release"
    exit 1
fi

tox

set_version "$VERSION"
git commit -am "Update version number to ${VERSION} for release." || true

git tag -a "v$VERSION" -m "v$VERSION" HEAD
set_version "${VERSION}+"
git commit -am "Update version number to ${VERSION}+ after release."

git push
git push --tags

# PyPI release is created via GitHub Actions on tag push.

# Add changelog to GitHub release.
./dev/make-release-notes.py "$VERSION" docs/news.rst "$CHANGES"
gh release create v"$VERSION" --notes-file "$CHANGES"
