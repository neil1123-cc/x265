#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_dependency_patch_suffixes.py')

ACTION_TEXT = '''
name: Setup Windows dependencies
inputs:
  lsmash-cache-suffix:
    description: Cache suffix appended after the L-SMASH ref
    required: false
    default: clang-coff-refptr-v2
  lsmash-patch-path:
    description: Patch path relative to the checked-out L-SMASH directory
    required: false
    default: ../x265/.github/patches/l-smash-clang-coff-refptr.patch
  gop-muxer-cache-suffix:
    description: Cache suffix appended after the GOP muxer ref
    required: false
    default: lsmash-add-box-v2-clang-gnu20
  gop-muxer-patch-path:
    description: Patch path relative to the checked-out GOP muxer directory
    required: false
    default: ../x265/.github/patches/gop-muxer-lsmash-add-box.patch
'''


def run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def write_repo(repo):
    action = repo / '.github' / 'actions' / 'setup-windows-deps'
    patches = repo / '.github' / 'patches'
    action.mkdir(parents=True)
    patches.mkdir(parents=True)
    (action / 'action.yml').write_text(ACTION_TEXT)
    (patches / 'l-smash-clang-coff-refptr.patch').write_text('lsmash patch v1\n')
    (patches / 'gop-muxer-lsmash-add-box.patch').write_text('gop patch v1\n')


def replace_text(path, old, new):
    text = path.read_text()
    if old not in text:
        raise AssertionError(f'missing text {old!r}')
    path.write_text(text.replace(old, new, 1))


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        git(repo, 'init')
        git(repo, 'config', 'user.name', 'test')
        git(repo, 'config', 'user.email', 'test@example.com')
        git(repo, 'add', '.')
        git(repo, 'commit', '-m', 'base')
        base = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()

        expect_pass(run('--repo-root', str(repo)))

        (repo / '.github' / 'patches' / 'l-smash-clang-coff-refptr.patch').write_text('lsmash patch v2\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-m', 'patch without suffix')
        no_suffix = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        expect_fail(run('--repo-root', str(repo), '--before', base, '--after', no_suffix), 'changed without bumping lsmash-cache-suffix')

        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            'default: clang-coff-refptr-v2',
            'default: clang-coff-refptr-v3',
        )
        git(repo, 'add', '.')
        git(repo, 'commit', '-m', 'suffix bumped')
        bumped = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        expect_pass(run('--repo-root', str(repo), '--before', base, '--after', bumped))

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            '../x265/.github/patches/gop-muxer-lsmash-add-box.patch',
            '../x265/.github/patches/missing.patch',
        )
        expect_fail(run('--repo-root', str(repo)), 'GOP muxer patch input gop-muxer-patch-path points to .github/patches/missing.patch')

    print('dependency patch suffix guardrails validated')


if __name__ == '__main__':
    main()
