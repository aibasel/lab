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

# Requirements:
#   Install uv: https://github.com/astral-sh/uv (e.g., curl -LsSf https://astral.sh/uv/install.sh | sh)
# Authentication:
#   Either export UV_PUBLISH_TOKEN=<pypi-token> or configure ~/.pypirc (uv will pick it up).
# Build both sdist and wheel into dist/.
uv build
# Publish previously built artifacts.
uv publish

git tag -a "v$VERSION" -m "v$VERSION" HEAD
set_version "${VERSION}+"
git commit -am "Update version number to ${VERSION}+ after release."

git push
git push --tags

# Add changelog to GitHub release.
./dev/make-release-notes.py "$VERSION" docs/news.rst "$CHANGES"
hub release create v"$VERSION" --file="$CHANGES"
