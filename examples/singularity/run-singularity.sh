#!/bin/bash

set -euo pipefail

if [[ $# != 4 ]]; then
    echo "usage: $(basename "$0") image domain_file problem_file plan_file" 1>&2
    exit 2
fi

if [ -f $PWD/$4 ]; then
    echo "Remove $PWD/$4" 1>&2
    exit 2
fi

start=`date +%s`

set +e
{ time singularity run -C -H $PWD $1 $PWD/$2 $PWD/$3 $4 ; } 2>&1
set -e

end=`date +%s`

runtime=$((end-start))
echo "Singularity runtime: ${runtime}s"

echo ""
echo "Run VAL"
echo ""

if [ -f $PWD/$4 ]; then
    echo "Found plan file."
    validate $PWD/$2 $PWD/$3 $PWD/$4
else
    echo "No plan file."
    validate $PWD/$2 $PWD/$3
fi
