#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path

ACTION_PATH = Path('.github/actions/setup-windows-deps/action.yml')
DEPS_CACHE_PATH = Path('.github/deps-cache.json')
UPDATE_DEPS_PATH = Path('.github/workflows/update-deps.yml')
HEX_SHA_RE = re.compile(r'^[0-9a-f]{40}$')
DEPENDENCY_RULES = (
    {
        'name': 'L-SMASH',
        'cache_key': 'lsmash',
        'ref_field': 'lsmash-ref',
        'repository_field': 'lsmash-repository',
        'expected_repository': 'vimeo/l-smash',
        'latest_step_id': 'lsmash',
        'latest_api': 'https://api.github.com/repos/vimeo/l-smash/commits?sha=master&per_page=1',
        'patch_path': '.github/patches/l-smash-clang-coff-refptr.patch',
        'patch_field': 'lsmash-patch-path',
        'suffix_field': 'lsmash-cache-suffix',
        'action_snippets': (
            'key: lsmash-${{ inputs.lsmash-repository }}-${{ inputs.lsmash-ref }}-${{ inputs.lsmash-cache-suffix }}',
            'git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}',
            'git apply --ignore-whitespace ${{ inputs.lsmash-patch-path }}',
            'git diff --check -- ${{ inputs.lsmash-patch-check-paths }}',
            'grep -Fq \'lsmash_local_isom_box_type\' codecs/description.c',
            'grep -Fq \'return isom_get_sample_group_description_common( list, ISOM_GROUP_TYPE_PROL );\' core/isom.c',
        ),
    },
    {
        'name': 'GOP muxer',
        'cache_key': 'gop_muxer',
        'ref_field': 'gop-muxer-ref',
        'repository_field': 'gop-muxer-repository',
        'expected_repository': 'msg7086/gop_muxer',
        'latest_step_id': 'gop_muxer',
        'latest_api': 'https://api.github.com/repos/msg7086/gop_muxer/commits?sha=master&per_page=1',
        'patch_path': '.github/patches/gop-muxer-lsmash-add-box.patch',
        'patch_field': 'gop-muxer-patch-path',
        'suffix_field': 'gop-muxer-cache-suffix',
        'action_snippets': (
            'key: gop-muxer-${{ inputs.gop-muxer-repository }}-${{ inputs.gop-muxer-ref }}-${{ inputs.gop-muxer-cache-suffix }}',
            'git -c core.autocrlf=false reset --hard HEAD',
            'git apply --check ${{ inputs.gop-muxer-patch-path }}',
            'git apply ${{ inputs.gop-muxer-patch-path }}',
            'git diff --check -- gop_muxer.cpp',
            "grep -Fq 'lsmash_add_box(lsmash_root_as_box(p_root), free_box)' gop_muxer.cpp",
            'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o',
        ),
    },
)
DEPS_CACHE_REF_RULES = (
    {'cache_key': 'obuparse', 'action_field': 'obuparse-ref', 'allow_tag': True},
    *DEPENDENCY_RULES,
)
PATCH_SUFFIX_RULES = DEPENDENCY_RULES


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
        if line.strip() != f'{field}:':
            continue
        base_indent = len(line) - len(line.lstrip(' '))
        for candidate in lines[index + 1:]:
            stripped = candidate.strip()
            indent = len(candidate) - len(candidate.lstrip(' '))
            if stripped and indent <= base_indent:
                break
            if stripped.startswith('default:'):
                return stripped.partition(':')[2].strip().strip('"\'')
        fail(f'{field} default not found in setup-windows-deps action at {ref}', ACTION_PATH)
    fail(f'{field} input not found in setup-windows-deps action at {ref}', ACTION_PATH)


def validate_sha(value, description, path):
    if not isinstance(value, str) or not HEX_SHA_RE.fullmatch(value):
        fail(f'{description} must be a 40-character lowercase hex commit SHA, got {value!r}', path)


def validate_suffix(value, description, path):
    if not value:
        fail(f'{description} has an empty default', path)
    if any(char.isspace() for char in value) or '/' in value or '\\' in value:
        fail(f'{description} must be a non-empty cache-key suffix without whitespace or path separators', path)


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
        repository = action_default(action_text, rule['repository_field'])
        if repository != rule['expected_repository']:
            fail(
                f"{rule['name']} repository input {rule['repository_field']} is {repository!r}, expected {rule['expected_repository']!r}",
                ACTION_PATH,
            )
        validate_sha(action_default(action_text, rule['ref_field']), f"{rule['name']} ref input {rule['ref_field']}", ACTION_PATH)
        patch_default = normalize_patch_default(action_default(action_text, rule['patch_field']))
        if patch_default != rule['patch_path']:
            fail(
                f"{rule['name']} patch input {rule['patch_field']} points to {patch_default}, expected {rule['patch_path']}",
                ACTION_PATH,
            )
        validate_suffix(action_default(action_text, rule['suffix_field']), f"{rule['name']} cache suffix input {rule['suffix_field']}", ACTION_PATH)
        patch_file = repo_root / rule['patch_path']
        if not patch_file.is_file():
            fail(f"{rule['name']} patch file is missing", patch_file)


def validate_action_snippets(repo_root):
    text = action_text_at(repo_root)
    for rule in PATCH_SUFFIX_RULES:
        for snippet in rule['action_snippets']:
            if snippet not in text:
                fail(f"setup-windows-deps action is missing {rule['name']} patch preflight snippet: {snippet}", ACTION_PATH)
    print('Dependency patch preflight snippets validated')


def validate_deps_cache_refs(repo_root):
    cache_path = repo_root / DEPS_CACHE_PATH
    if not cache_path.is_file():
        print(f'::warning::{DEPS_CACHE_PATH.as_posix()} is missing; skipping dependency cache ref provenance check')
        return

    action_text = action_text_at(repo_root)
    cache = json.loads(cache_path.read_text())
    for rule in DEPS_CACHE_REF_RULES:
        cache_key = rule['cache_key']
        action_field = rule['action_field'] if 'action_field' in rule else rule['ref_field']
        expected = action_default(action_text, action_field)
        actual = cache.get(cache_key)
        if actual != expected:
            fail(
                f'{DEPS_CACHE_PATH.as_posix()} {cache_key}={actual!r} does not match {action_field} default {expected!r}',
                cache_path,
            )
        if not rule.get('allow_tag'):
            validate_sha(actual, f'{DEPS_CACHE_PATH.as_posix()} {cache_key}', cache_path)
    print('Dependency cache ref provenance validated')


def validate_update_deps_provenance(repo_root):
    update_path = repo_root / UPDATE_DEPS_PATH
    if not update_path.is_file():
        fail('missing update-deps workflow', update_path)
    text = update_path.read_text()
    for rule in DEPENDENCY_RULES:
        required = (
            f'https://api.github.com/repos/{rule["expected_repository"]}/commits?sha=master&per_page=1',
            f'id: {rule["latest_step_id"]}',
            f'${{{{ steps.{rule["latest_step_id"]}.outputs.sha }}}}',
            f'/{rule["ref_field"]}:/,/{rule["suffix_field"]}:/s/default: [0-9a-f]\\{{40\\}}/',
            f'"{rule["cache_key"]}": "${{{{ steps.{rule["latest_step_id"]}.outputs.sha }}}}"',
        )
        for snippet in required:
            if snippet not in text:
                fail(f"update-deps workflow is not pinned to {rule['name']} provenance snippet: {snippet}", update_path)
    print('Dependency update provenance validated')


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
    validate_action_snippets(repo_root)
    validate_deps_cache_refs(repo_root)
    validate_update_deps_provenance(repo_root)
    if bool(args.before) != bool(args.after):
        fail('--before and --after must be provided together')
    if args.before and args.after:
        validate_diff(repo_root, args.before, args.after)
    print('Dependency patch cache suffix guardrails validated')


if __name__ == '__main__':
    main()
