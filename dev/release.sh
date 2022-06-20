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
git commit -am "Update version number to ${VERSION} for release."

# Requirements:
#   pipx install twine
#   pip install --user wheel
python3 setup.py sdist bdist_wheel --universal
twine upload dist/lab-${VERSION}.tar.gz dist/lab-${VERSION}-py2.py3-none-any.whl

git tag -a "v$VERSION" -m "v$VERSION" HEAD
set_version "${VERSION}+"
git commit -am "Update version number to ${VERSION}+ after release."

git push
git push --tags

# Add changelog to GitHub release.
./dev/make-release-notes.py "$VERSION" docs/news.rst "$CHANGES"
hub release create v"$VERSION" --file="$CHANGES"
