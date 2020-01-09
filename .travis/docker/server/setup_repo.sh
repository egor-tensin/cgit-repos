#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

readonly local_repo_path="$HOME/test_repo"

setup_local_repo() {
    mkdir -p -- "$local_repo_path"
    pushd -- "$local_repo_path" > /dev/null
    git init
    echo '1' > 1.txt
    git add .
    git commit -m 'first commit'
    echo '2' > 2.txt
    git add .
    git commit -m 'second commit'
    popd > /dev/null
}

main() {
    setup_local_repo
}

main
