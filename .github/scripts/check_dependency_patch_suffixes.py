#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

ACTION_PATH = Path('.github/actions/setup-windows-deps/action.yml')
DEPS_CACHE_PATH = Path('.github/deps-cache.json')
DEPS_CACHE_REF_RULES = (
    ('obuparse', 'obuparse-ref'),
    ('lsmash', 'lsmash-ref'),
    ('gop_muxer', 'gop-muxer-ref'),
)
PATCH_SUFFIX_RULES = (
    {
        'name': 'L-SMASH',
        'patch_path': '.github/patches/l-smash-clang-coff-refptr.patch',
        'patch_field': 'lsmash-patch-path',
        'suffix_field': 'lsmash-cache-suffix',
    },
    {
        'name': 'GOP muxer',
        'patch_path': '.github/patches/gop-muxer-lsmash-add-box.patch',
        'patch_field': 'gop-muxer-patch-path',
        'suffix_field': 'gop-muxer-cache-suffix',
    },
)


def annotation_path(path):
    return Path(path).as_posix()


def fail(message, path=None):
    if path is not None:
        print(f'::error file={annotation_path(path)}::{message}')
        raise SystemExit(f'{message}: {annotation_path(path)}')
    print(f'::error::{message}')
    raise SystemExit(message)


def action_default(action_text, field, ref='working tree'):
    lines = action_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == f'{field}:':
            for candidate in lines[index + 1:index + 8]:
                stripped = candidate.strip()
                if stripped.startswith('default:'):
                    return stripped.partition(':')[2].strip().strip('"\'')
            fail(f'{field} default not found in setup-windows-deps action at {ref}', ACTION_PATH)
    fail(f'{field} input not found in setup-windows-deps action at {ref}', ACTION_PATH)


def normalize_patch_default(value):
    normalized = value.replace('\\', '/').strip()
    while normalized.startswith('../'):
        normalized = normalized[3:]
    if normalized.startswith('./'):
        normalized = normalized[2:]
    if normalized.startswith('x265/'):
        normalized = normalized[5:]
    return normalized


def git_output(repo_root, args):
    return subprocess.check_output(['git', '-C', str(repo_root), *args], text=True)


def action_text_at(repo_root, ref=None):
    if ref is None:
        path = repo_root / ACTION_PATH
        if not path.is_file():
            fail('missing setup-windows-deps action', path)
        return path.read_text()
    return git_output(repo_root, ['show', f'{ref}:{ACTION_PATH.as_posix()}'])


def changed_paths(repo_root, before, after):
    paths = [rule['patch_path'] for rule in PATCH_SUFFIX_RULES]
    output = git_output(repo_root, ['diff', '--name-only', before, after, '--', *paths])
    return set(output.splitlines())


def validate_current_mapping(repo_root):
    action_text = action_text_at(repo_root)
    for rule in PATCH_SUFFIX_RULES:
        patch_default = normalize_patch_default(action_default(action_text, rule['patch_field']))
        if patch_default != rule['patch_path']:
            fail(
                f"{rule['name']} patch input {rule['patch_field']} points to {patch_default}, expected {rule['patch_path']}",
                ACTION_PATH,
            )
        suffix = action_default(action_text, rule['suffix_field'])
        if not suffix:
            fail(f"{rule['name']} cache suffix input {rule['suffix_field']} has an empty default", ACTION_PATH)
        patch_file = repo_root / rule['patch_path']
        if not patch_file.is_file():
            fail(f"{rule['name']} patch file is missing", patch_file)


def validate_deps_cache_refs(repo_root):
    cache_path = repo_root / DEPS_CACHE_PATH
    if not cache_path.is_file():
        print(f'::warning::{DEPS_CACHE_PATH.as_posix()} is missing; skipping dependency cache ref provenance check')
        return

    action_text = action_text_at(repo_root)
    cache = json.loads(cache_path.read_text())
    for cache_key, action_field in DEPS_CACHE_REF_RULES:
        expected = action_default(action_text, action_field)
        actual = cache.get(cache_key)
        if actual != expected:
            fail(
                f'{DEPS_CACHE_PATH.as_posix()} {cache_key}={actual!r} does not match {action_field} default {expected!r}',
                cache_path,
            )
    print('Dependency cache ref provenance validated')


def validate_diff(repo_root, before, after):
    changed = changed_paths(repo_root, before, after)
    if not changed:
        print('Dependency patches unchanged')
        return

    before_action = action_text_at(repo_root, before)
    after_action = action_text_at(repo_root, after)
    for rule in PATCH_SUFFIX_RULES:
        if rule['patch_path'] not in changed:
            continue
        before_suffix = action_default(before_action, rule['suffix_field'], before)
        after_suffix = action_default(after_action, rule['suffix_field'], after)
        if before_suffix == after_suffix:
            fail(f"{rule['patch_path']} changed without bumping {rule['suffix_field']}", rule['patch_path'])
        print(f"{rule['suffix_field']} changed: {before_suffix} -> {after_suffix}")


def main():
    parser = argparse.ArgumentParser(description='Check dependency patch files stay coupled to cache suffix bumps')
    parser.add_argument('--repo-root', type=Path, default=Path.cwd())
    parser.add_argument('--before')
    parser.add_argument('--after')
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    validate_current_mapping(repo_root)
    validate_deps_cache_refs(repo_root)
    if bool(args.before) != bool(args.after):
        fail('--before and --after must be provided together')
    if args.before and args.after:
        validate_diff(repo_root, args.before, args.after)
    print('Dependency patch cache suffix guardrails validated')


if __name__ == '__main__':
    main()
