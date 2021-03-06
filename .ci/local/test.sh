#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

readonly local_repo_path="$HOME/test_repo"
readonly cgit_repos_conf_path="$HOME/etc/cgit-repos/cgit-repos.conf"
readonly my_repos_path="$HOME/etc/cgit-repos/my_repos.py"
readonly output_path="$HOME/var/cgit-repos/output"

setup_local_repo() {
    echo
    echo ----------------------------------------------------------------------
    echo Setting up upstream repository
    echo ----------------------------------------------------------------------

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

setup_cgit_repos_conf() {
    echo
    echo ----------------------------------------------------------------------
    echo cgit-repos.conf
    echo ----------------------------------------------------------------------

    local conf_dir
    conf_dir="$( dirname -- "$cgit_repos_conf_path" )"
    mkdir -p -- "$conf_dir"

    cat <<EOF | tee "$cgit_repos_conf_path"
[DEFAULT]

my_repos = $my_repos_path
output = $output_path
EOF
}

setup_my_repos_py() {
    echo
    echo ----------------------------------------------------------------------
    echo my_repos.py
    echo ----------------------------------------------------------------------

    local conf_dir
    conf_dir="$( dirname -- "$my_repos_path" )"
    mkdir -p -- "$conf_dir"

    cat <<EOF | tee "$my_repos_path"
from cgit.repos.repo import Repo


MY_REPOS = (
    Repo('test_repo', clone_url='$HOME/test_repo'),
)
EOF
}

setup_cgit_repos() {
    setup_cgit_repos_conf
    setup_my_repos_py
}

setup() {
    setup_local_repo
    setup_cgit_repos
}

run() {
    echo
    echo ----------------------------------------------------------------------
    echo Pulling repository from upstream
    echo ----------------------------------------------------------------------

    python3 -m cgit.repos.main --config "$cgit_repos_conf_path"
}

verify() {
    echo
    echo ----------------------------------------------------------------------
    echo Checking the pulled repository
    echo ----------------------------------------------------------------------

    pushd -- "$output_path" > /dev/null
    cd -- test_repo
    git log --oneline
    popd > /dev/null
}

main() {
    setup
    run
    verify
}

main
