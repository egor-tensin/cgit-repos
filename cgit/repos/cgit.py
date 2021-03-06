# Copyright (c) 2018 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cgit repos" project.
# For details, see https://github.com/egor-tensin/cgit-repos.
# Distributed under the MIT License.

from enum import Enum
import logging
import os
import os.path
import shutil

from cgit.repos.utils import chdir, check_output, run


_ENV = os.environ.copy()
_ENV['GIT_SSH_COMMAND'] = 'ssh -oBatchMode=yes -oLogLevel=QUIET -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null'


def _run(*args, **kwargs):
    return run(*args, env=_ENV, **kwargs)


def _check_output(*args, **kwargs):
    return check_output(*args, env=_ENV, **kwargs)


class CGit:
    def __init__(self, clone_url):
        self.clone_url = clone_url

    def get_clone_url(self, repo):
        if self.clone_url is None:
            return None
        return self.clone_url.format(repo_id=repo.repo_id)


class CGitRC:
    def __init__(self, cgit):
        self.cgit = cgit

    def write(self, path, repo):
        with open(path, 'w') as fd:
            self._write_field(fd, 'clone-url', self._build_clone_url(repo))
            self._write_field(fd, 'owner', repo.owner)
            self._write_field(fd, 'desc', repo.desc)
            self._write_field(fd, 'homepage', repo.homepage)

    @staticmethod
    def _write_field(fd, field, value):
        if value is None:
            return
        fd.write(f'{field}={value}\n')

    def _build_clone_url(self, repo):
        clone_urls = []
        if repo.clone_url is not None:
            clone_urls.append(repo.clone_url)
        cgit_clone_url = self.cgit.get_clone_url(repo)
        if cgit_clone_url is not None:
            clone_urls.append(cgit_clone_url)
        if not clone_urls:
            return None
        clone_urls = ' '.join(clone_urls)
        return clone_urls


class Output:
    def __init__(self, output_dir, cgit):
        self.output_dir = self._make_dir(output_dir)
        self.cgitrc = CGitRC(cgit)

    @staticmethod
    def _make_dir(rel_path):
        abs_path = os.path.abspath(rel_path)
        os.makedirs(abs_path, exist_ok=True)
        return abs_path

    def get_repo_dir(self, repo):
        return os.path.join(self.output_dir, repo.repo_id)

    def get_cgitrc_path(self, repo):
        return os.path.join(self.get_repo_dir(repo), 'cgitrc')

    def pull(self, repo):
        success = False
        verdict = self.judge(repo)
        if verdict is RepoVerdict.SHOULD_MIRROR:
            success = self.mirror(repo)
        elif verdict is RepoVerdict.SHOULD_UPDATE:
            success = self.update(repo)
        elif verdict is RepoVerdict.CANT_DECIDE:
            success = False
        else:
            raise NotImplementedError(f'Unknown repository verdict: {verdict}')
        if success:
            self.cgitrc.write(self.get_cgitrc_path(repo), repo)
        return success

    def judge(self, repo):
        repo_dir = self.get_repo_dir(repo)
        if not os.path.isdir(repo_dir):
            return RepoVerdict.SHOULD_MIRROR
        with chdir(repo_dir):
            if not _run('git', 'rev-parse', '--is-inside-work-tree', discard_output=True):
                logging.warning('Not a repository, so going to mirror: %s', repo_dir)
                return RepoVerdict.SHOULD_MIRROR
            success, output = _check_output('git', 'config', '--get', 'remote.origin.url')
            if not success:
                # Every repository managed by this script should have the
                # 'origin' remote. If it doesn't, it's trash.
                return RepoVerdict.SHOULD_MIRROR
            if f'{repo.clone_url}\n' != output:
                logging.warning("Existing repository '%s' URL doesn't match the specified clone" \
                                " URL: %s", repo.repo_id, repo.clone_url)
                return RepoVerdict.CANT_DECIDE
            # Looks like a legit clone of the specified remote.
            return RepoVerdict.SHOULD_UPDATE

    def mirror(self, repo):
        logging.info("Mirroring repository '%s' from: %s", repo.repo_id,
                     repo.clone_url)
        repo_dir = self.get_repo_dir(repo)
        if os.path.isdir(repo_dir):
            try:
                shutil.rmtree(repo_dir)
            except Exception as e:
                logging.exception(e)
                return False
        return _run('git', 'clone', '--mirror', repo.clone_url, repo_dir)

    def update(self, repo):
        logging.info("Updating repository '%s'", repo.repo_id)
        repo_dir = self.get_repo_dir(repo)
        with chdir(repo_dir):
            if not _run('git', 'remote', 'update', '--prune'):
                return False
            if _run('git', 'rev-parse', '--verify', '--quiet', 'origin/master', discard_output=True):
                if not _run('git', 'reset', '--soft', 'origin/master'):
                    return False
            return True


class RepoVerdict(Enum):
    SHOULD_MIRROR = 1
    SHOULD_UPDATE = 2
    CANT_DECIDE = 3
