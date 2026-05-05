#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_dependency_patch_suffixes.py')

ACTION_TEXT = '''
name: Setup Windows dependencies
inputs:
  obuparse-ref:
    description: obuparse ref to checkout
    required: false
    default: v2.0.2
  lsmash-repository:
    description: L-SMASH repository to checkout
    required: false
    default: vimeo/l-smash
  lsmash-ref:
    description: L-SMASH ref to checkout
    required: false
    default: 04e39f1fb232c332d4b04a1043c02c7c2d282d00
  lsmash-cache-suffix:
    description: Cache suffix appended after the L-SMASH ref
    required: false
    default: clang-coff-refptr-v2
  lsmash-path:
    description: L-SMASH checkout path
    required: false
    default: l-smash
  lsmash-patch-path:
    description: Patch path relative to the checked-out L-SMASH directory
    required: false
    default: ../x265/.github/patches/l-smash-clang-coff-refptr.patch
  gop-muxer-repository:
    description: GOP muxer repository to checkout
    required: false
    default: msg7086/gop_muxer
  gop-muxer-ref:
    description: GOP muxer ref to checkout
    required: false
    default: 5677cf5ef905c2412ed31de300cd1a08b341d21d
  gop-muxer-cache-suffix:
    description: Cache suffix appended after the GOP muxer ref
    required: false
    default: lsmash-add-box-v2-clang-gnu20
  gop-muxer-path:
    description: GOP muxer checkout path
    required: false
    default: gop_muxer
  gop-muxer-patch-path:
    description: Patch path relative to the checked-out GOP muxer directory
    required: false
    default: ../x265/.github/patches/gop-muxer-lsmash-add-box.patch
          key: lsmash-${{ inputs.lsmash-repository }}-${{ inputs.lsmash-ref }}-${{ inputs.lsmash-cache-suffix }}
        git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}
        git apply --ignore-whitespace ${{ inputs.lsmash-patch-path }}
        git diff --check -- ${{ inputs.lsmash-patch-check-paths }}
        grep -Fq 'lsmash_local_isom_box_type' codecs/description.c
        grep -Fq "LSMASH_4CC( 'h', 'v', 'c', 'C' )" codecs/hevc.c
        grep -Fq 'lsmash_isom_box_type_value' core/box.c
        grep -Fq 'lsmash_qtff_box_type_value' core/box.c
        grep -Fq 'return isom_get_sample_group_description_common( list, ISOM_GROUP_TYPE_PROL );' core/isom.c
        grep -Fq 'return isom_get_sample_to_group_common( list, ISOM_GROUP_TYPE_PROL );' core/isom.c
        echo "Validated L-SMASH patch anchors"
          key: gop-muxer-${{ inputs.gop-muxer-repository }}-${{ inputs.gop-muxer-ref }}-${{ inputs.gop-muxer-cache-suffix }}
        git -c core.autocrlf=false reset --hard HEAD
        git apply --check ${{ inputs.gop-muxer-patch-path }}
        git apply ${{ inputs.gop-muxer-patch-path }}
        git diff --check -- gop_muxer.cpp
        grep -Fq 'lsmash_add_box(lsmash_root_as_box(p_root), free_box)' gop_muxer.cpp
        echo "Validated GOP muxer patch anchors"
        c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o
'''

UPDATE_DEPS_TEXT = '''
name: Update Dependencies
jobs:
  update-deps:
    steps:
      - name: Get Latest L-SMASH Commit
        id: lsmash
        run: |
          SHA=$(curl -fsSL "https://api.github.com/repos/vimeo/l-smash/commits?sha=master&per_page=1" | jq -r '.[0].sha')
          echo "sha=$SHA" >> $GITHUB_OUTPUT
      - name: Get Latest GOP muxer Commit
        id: gop_muxer
        run: |
          SHA=$(curl -fsSL "https://api.github.com/repos/msg7086/gop_muxer/commits?sha=master&per_page=1" | jq -r '.[0].sha')
          echo "sha=$SHA" >> $GITHUB_OUTPUT
      - name: Update Dependency Refs
        run: |
          sed -i "/lsmash-ref:/,/lsmash-cache-suffix:/s/default: [0-9a-f]\\{40\\}/default: ${{ steps.lsmash.outputs.sha }}/" "$action"
          sed -i "/gop-muxer-ref:/,/gop-muxer-cache-suffix:/s/default: [0-9a-f]\\{40\\}/default: ${{ steps.gop_muxer.outputs.sha }}/" "$action"
      - name: Update Deps Cache
        run: |
          cat > .github/deps-cache.json << EOF
          {
            "lsmash": "${{ steps.lsmash.outputs.sha }}",
            "obuparse": "${{ steps.obuparse.outputs.tag }}",
            "gop_muxer": "${{ steps.gop_muxer.outputs.sha }}"
          }
          EOF
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
    (repo / '.github' / 'workflows').mkdir(parents=True)
    (action / 'action.yml').write_text(ACTION_TEXT)
    (repo / '.github' / 'workflows' / 'update-deps.yml').write_text(UPDATE_DEPS_TEXT)
    (repo / '.github' / 'deps-cache.json').write_text(json.dumps({
        'lsmash': '04e39f1fb232c332d4b04a1043c02c7c2d282d00',
        'obuparse': 'v2.0.2',
        'gop_muxer': '5677cf5ef905c2412ed31de300cd1a08b341d21d',
        'updated_at': '2026-05-04T00:00:00Z',
    }))
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

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            'default: 5677cf5ef905c2412ed31de300cd1a08b341d21d',
            'default: 1111111111111111111111111111111111111111',
        )
        expect_fail(run('--repo-root', str(repo)), ".github/deps-cache.json gop_muxer='5677cf5ef905c2412ed31de300cd1a08b341d21d' does not match gop-muxer-ref default '1111111111111111111111111111111111111111'")


    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            'default: vimeo/l-smash',
            'default: fork/l-smash',
        )
        expect_fail(run('--repo-root', str(repo)), "L-SMASH repository input lsmash-repository is 'fork/l-smash'")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            'default: clang-coff-refptr-v2',
            'default: clang coff refptr v2',
        )
        expect_fail(run('--repo-root', str(repo)), 'L-SMASH cache suffix input lsmash-cache-suffix must be a non-empty cache-key suffix')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'deps-cache.json',
            '04e39f1fb232c332d4b04a1043c02c7c2d282d00',
            'master',
        )
        expect_fail(run('--repo-root', str(repo)), ".github/deps-cache.json lsmash='master' does not match lsmash-ref default")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'workflows' / 'update-deps.yml',
            'https://api.github.com/repos/msg7086/gop_muxer/commits?sha=master&per_page=1',
            'https://api.github.com/repos/other/gop_muxer/commits?sha=master&per_page=1',
        )
        expect_fail(run('--repo-root', str(repo)), 'update-deps workflow is not pinned to GOP muxer provenance snippet')
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            '    default: clang-coff-refptr-v2\n  lsmash-path:',
            '  lsmash-path:',
        )
        expect_fail(run('--repo-root', str(repo)), 'lsmash-cache-suffix default not found')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            'git -c core.autocrlf=false reset --hard HEAD',
            'git reset --hard HEAD',
        )
        expect_fail(run('--repo-root', str(repo)), 'setup-windows-deps action is missing GOP muxer patch preflight snippet: git -c core.autocrlf=false reset --hard HEAD')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        git(repo, 'init')
        git(repo, 'config', 'user.name', 'test')
        git(repo, 'config', 'user.email', 'test@example.com')
        git(repo, 'add', '.')
        git(repo, 'commit', '-m', 'base')
        base = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()

        (repo / '.github' / 'patches' / 'gop-muxer-lsmash-add-box.patch').write_text('gop patch v2\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-m', 'gop patch without suffix')
        no_suffix = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        expect_fail(run('--repo-root', str(repo), '--before', base, '--after', no_suffix), 'changed without bumping gop-muxer-cache-suffix')

        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            'default: lsmash-add-box-v2-clang-gnu20',
            'default: lsmash-add-box-v3-clang-gnu20',
        )
        git(repo, 'add', '.')
        git(repo, 'commit', '-m', 'gop suffix bumped')
        bumped = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        expect_pass(run('--repo-root', str(repo), '--before', base, '--after', bumped))
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            "grep -Fq 'lsmash_qtff_box_type_value' core/box.c",
            "grep -Fq 'lsmash_isom_box_type_value' core/box.c",
        )
        expect_fail(run('--repo-root', str(repo)), 'setup-windows-deps action is missing L-SMASH patch preflight snippet')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml',
            'echo "Validated GOP muxer patch anchors"',
            'echo "GOP muxer patch applied"',
        )
        expect_fail(run('--repo-root', str(repo)), 'setup-windows-deps action is missing GOP muxer patch preflight snippet')


if __name__ == '__main__':
    main()
