#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

EXPECTED_LAYOUT = 'per-target-bounded-window'
EXPECTED_WINDOW = {
    'slots': 4,
    'fresh_slot': 'profiles/0.profdata',
    'weights_newest_to_oldest': [4, 3, 2, 1],
}
DEPENDENCY_SUMMARY_FIELDS = (
    'ffmpeg_ref',
    'ffmpeg_cache_key',
    'mimalloc_ref',
    'obuparse_ref',
    'obuparse_cache_key',
    'lsmash_repository',
    'lsmash_ref',
    'lsmash_cache_key',
    'gop_muxer_repository',
    'gop_muxer_ref',
    'gop_muxer_cache_key',
)
REQUIRED_DEPENDENCY_FIELDS = (
    'ffmpeg_ref',
    'ffmpeg_cache_key',
    'mimalloc_ref',
    'obuparse_ref',
    'obuparse_cache_key',
    'lsmash_repository',
    'lsmash_ref',
    'lsmash_cache_key',
    'gop_muxer_repository',
    'gop_muxer_ref',
    'gop_muxer_cache_key',
)
DEPENDENCY_CACHE_KEY_CONTAINS = (
    ('ffmpeg_cache_key', ('ffmpeg_ref',)),
    ('obuparse_cache_key', ('obuparse_ref',)),
    ('lsmash_cache_key', ('lsmash_repository', 'lsmash_ref')),
    ('gop_muxer_cache_key', ('gop_muxer_repository', 'gop_muxer_ref')),
)
DEPENDENCY_CACHE_KEY_REQUIRED_SUBSTRINGS = (
    ('gop_muxer_cache_key', ('gnu20',)),
)
DEPENDENCY_REQUIRED_SUFFIX_FIELDS = (
    ('ffmpeg_cache_key', ('ffmpeg_ref',), 'ffmpeg', 'ffmpeg'),
    ('obuparse_cache_key', ('obuparse_ref',), 'obuparse', 'obuparse'),
    ('lsmash_cache_key', ('lsmash_repository', 'lsmash_ref'), 'lsmash', 'lsmash'),
    ('gop_muxer_cache_key', ('gop_muxer_repository', 'gop_muxer_ref'), 'gop-muxer', 'gop_muxer'),
)


def fail(metadata_path, message):
    raise SystemExit(f'{metadata_path}: {message}')


def required(metadata_path, mapping, key):
    if key not in mapping:
        fail(metadata_path, f'missing profdata metadata field: {key}')
    return mapping[key]


def dependency_cache_key_mismatches(dependencies):
    mismatches = []
    for cache_key_field, source_fields in DEPENDENCY_CACHE_KEY_CONTAINS:
        cache_key = dependencies.get(cache_key_field)
        missing_sources = [field for field in source_fields if field not in dependencies]
        if cache_key is None or missing_sources:
            continue
        missing_values = [field for field in source_fields if str(dependencies[field]) not in str(cache_key)]
        if missing_values:
            expected = ', '.join(f'{field}={dependencies[field]}' for field in missing_values)
            mismatches.append(f'{cache_key_field} actual={cache_key} missing_expected_values={expected}')
    for cache_key_field, required_substrings in DEPENDENCY_CACHE_KEY_REQUIRED_SUBSTRINGS:
        cache_key = dependencies.get(cache_key_field)
        if cache_key is None:
            continue
        missing_substrings = [substring for substring in required_substrings if substring not in str(cache_key)]
        if missing_substrings:
            expected = ', '.join(missing_substrings)
            mismatches.append(f'{cache_key_field} actual={cache_key} missing_required_substrings={expected}')
    return mismatches


def dependency_required_suffix_mismatches(dependencies, required_suffixes):
    mismatches = []
    for cache_key_field, key_parts, prefix, suffix_name in DEPENDENCY_REQUIRED_SUFFIX_FIELDS:
        required_suffix = required_suffixes.get(suffix_name)
        if not required_suffix:
            continue
        cache_key = dependencies.get(cache_key_field)
        if cache_key is None or any(part not in dependencies for part in key_parts):
            continue
        expected_parts = [prefix, *(str(dependencies[part]) for part in key_parts), required_suffix]
        expected = '-'.join(expected_parts)
        if str(cache_key) != expected:
            mismatches.append(f'{cache_key_field} actual={cache_key} expected={expected}')
    return mismatches


def run_self_test():
    dependencies = {
        'ffmpeg_ref': 'n8.1',
        'ffmpeg_cache_key': 'ffmpeg-n8.1-full-v4-clang',
        'mimalloc_ref': 'v3.3.2',
        'obuparse_ref': 'v2.0.2',
        'obuparse_cache_key': 'obuparse-v2.0.2-clang-v1',
        'lsmash_repository': 'vimeo/l-smash',
        'lsmash_ref': '04e39f1fb232c332d4b04a1043c02c7c2d282d00',
        'lsmash_cache_key': 'lsmash-vimeo/l-smash-04e39f1fb232c332d4b04a1043c02c7c2d282d00-clang-coff-refptr-v2',
        'gop_muxer_repository': 'msg7086/gop_muxer',
        'gop_muxer_ref': '5677cf5ef905c2412ed31de300cd1a08b341d21d',
        'gop_muxer_cache_key': 'gop-muxer-msg7086/gop_muxer-5677cf5ef905c2412ed31de300cd1a08b341d21d-lsmash-add-box-v2-clang-gnu20',
    }
    mismatches = dependency_cache_key_mismatches(dependencies)
    if mismatches:
        fail('--self-test', 'valid GNU++20 dependency metadata was rejected: ' + '; '.join(mismatches))
    required_suffixes = {
        'ffmpeg': 'full-v4-clang',
        'obuparse': 'clang-v1',
        'lsmash': 'clang-coff-refptr-v2',
        'gop_muxer': 'lsmash-add-box-v2-clang-gnu20',
    }
    required_suffix_mismatches = dependency_required_suffix_mismatches(dependencies, required_suffixes)
    if required_suffix_mismatches:
        fail('--self-test', 'valid GNU++20 dependency cache suffix metadata was rejected: ' + '; '.join(required_suffix_mismatches))

    downgraded = dict(dependencies)
    downgraded['gop_muxer_cache_key'] = downgraded['gop_muxer_cache_key'].replace('-gnu20', '-gnu17')
    mismatches = dependency_cache_key_mismatches(downgraded)
    if not any('gop_muxer_cache_key' in mismatch and 'missing_required_substrings=gnu20' in mismatch for mismatch in mismatches):
        fail('--self-test', 'GOP muxer GNU++20 cache-key downgrade was not rejected')
    downgraded = dict(dependencies)
    downgraded['ffmpeg_cache_key'] = downgraded['ffmpeg_cache_key'].replace('-full-v4-clang', '-full-v5-clang')
    required_suffix_mismatches = dependency_required_suffix_mismatches(downgraded, required_suffixes)
    if not any('ffmpeg_cache_key' in mismatch and 'expected=ffmpeg-n8.1-full-v4-clang' in mismatch for mismatch in required_suffix_mismatches):
        fail('--self-test', 'FFmpeg cache suffix downgrade was not rejected')
    downgraded = dict(dependencies)
    downgraded['obuparse_cache_key'] = downgraded['obuparse_cache_key'].replace('-clang-v1', '-clang-v2')
    required_suffix_mismatches = dependency_required_suffix_mismatches(downgraded, required_suffixes)
    if not any('obuparse_cache_key' in mismatch and 'expected=obuparse-v2.0.2-clang-v1' in mismatch for mismatch in required_suffix_mismatches):
        fail('--self-test', 'obuparse cache suffix downgrade was not rejected')
    downgraded = dict(dependencies)
    downgraded['lsmash_cache_key'] = downgraded['lsmash_cache_key'].replace('-clang-coff-refptr-v2', '-clang-coff-refptr-v3')
    required_suffix_mismatches = dependency_required_suffix_mismatches(downgraded, required_suffixes)
    if not any('lsmash_cache_key' in mismatch and 'expected=lsmash-vimeo/l-smash-04e39f1fb232c332d4b04a1043c02c7c2d282d00-clang-coff-refptr-v2' in mismatch for mismatch in required_suffix_mismatches):
        fail('--self-test', 'L-SMASH cache suffix downgrade was not rejected')
    downgraded = dict(dependencies)
    downgraded['gop_muxer_cache_key'] = downgraded['gop_muxer_cache_key'].replace('-lsmash-add-box-v2-clang-gnu20', '-lsmash-add-box-v3-clang-gnu20')
    required_suffix_mismatches = dependency_required_suffix_mismatches(downgraded, required_suffixes)
    if not any('gop_muxer_cache_key' in mismatch and 'expected=gop-muxer-msg7086/gop_muxer-5677cf5ef905c2412ed31de300cd1a08b341d21d-lsmash-add-box-v2-clang-gnu20' in mismatch for mismatch in required_suffix_mismatches):
        fail('--self-test', 'GOP muxer cache suffix downgrade was not rejected')

    print('PGO profdata metadata guard self-test validated')


def main():
    parser = argparse.ArgumentParser(description='Check x265 PGO profdata metadata')
    parser.add_argument('metadata_path', nargs='?', type=Path)
    parser.add_argument('--expected-cpu')
    parser.add_argument('--expected-target')
    parser.add_argument('--expected-branch')
    parser.add_argument('--expected-toolchain')
    parser.add_argument('--current-toolchain')
    parser.add_argument('--current-commit')
    parser.add_argument('--required-ffmpeg-cache-suffix')
    parser.add_argument('--required-obuparse-cache-suffix')
    parser.add_argument('--required-lsmash-cache-suffix')
    parser.add_argument('--required-gop-muxer-cache-suffix')
    parser.add_argument('--require-target-cpu', action='store_true')
    parser.add_argument('--require-dependency-fields', action='store_true')
    parser.add_argument('--require-fresh-slot', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()

    if args.self_test:
        if args.metadata_path or args.expected_target or args.expected_branch:
            parser.error('--self-test cannot be combined with metadata validation arguments')
        run_self_test()
        return
    if not args.metadata_path:
        parser.error('metadata_path is required unless --self-test is used')
    if not args.expected_target:
        parser.error('--expected-target is required unless --self-test is used')
    if not args.expected_branch:
        parser.error('--expected-branch is required unless --self-test is used')

    metadata = json.loads(args.metadata_path.read_text())
    layout = required(args.metadata_path, metadata, 'layout')
    target_cpu = metadata.get('target_cpu')
    profile_target = required(args.metadata_path, metadata, 'profile_target')
    profdata_branch = required(args.metadata_path, metadata, 'profdata_branch')
    window = required(args.metadata_path, metadata, 'window')
    if layout != EXPECTED_LAYOUT:
        fail(args.metadata_path, f'profdata layout mismatch expected={EXPECTED_LAYOUT} actual={layout}')
    if args.expected_cpu:
        if target_cpu is None:
            message = f'{args.metadata_path}: missing profdata metadata field: target_cpu'
            if args.require_target_cpu:
                raise SystemExit(message)
            print('::warning::' + message)
        elif target_cpu != args.expected_cpu:
            fail(args.metadata_path, f'target_cpu mismatch expected={args.expected_cpu} actual={target_cpu}')
    if profile_target != args.expected_target:
        fail(args.metadata_path, f'profile_target mismatch expected={args.expected_target} actual={profile_target}')
    if profdata_branch != args.expected_branch:
        fail(args.metadata_path, f'profdata_branch mismatch expected={args.expected_branch} actual={profdata_branch}')
    profdata_toolchain = metadata.get('profdata_toolchain')
    llvm_profdata_version = metadata.get('llvm_profdata_version')
    if args.expected_toolchain:
        if profdata_toolchain != args.expected_toolchain:
            fail(args.metadata_path, f'profdata_toolchain mismatch expected={args.expected_toolchain} actual={profdata_toolchain}')
        if not llvm_profdata_version:
            fail(args.metadata_path, 'missing profdata metadata field: llvm_profdata_version')
    elif args.current_toolchain:
        if not profdata_toolchain:
            print(
                f'::warning::PGO profdata metadata missing profdata_toolchain: '
                f'metadata={args.metadata_path} branch={args.expected_branch} current_toolchain={args.current_toolchain}'
            )
        else:
            if profdata_toolchain != args.current_toolchain:
                print(
                    f'::warning::PGO profdata toolchain differs from local llvm-profdata: '
                    f'metadata={args.metadata_path} branch={args.expected_branch} '
                    f'metadata_toolchain={profdata_toolchain} current_toolchain={args.current_toolchain}'
                )
            if not llvm_profdata_version:
                print(
                    f'::warning::PGO profdata metadata missing llvm_profdata_version: '
                    f'metadata={args.metadata_path} branch={args.expected_branch} profdata_toolchain={profdata_toolchain}'
                )
    for key, expected in EXPECTED_WINDOW.items():
        actual = required(args.metadata_path, window, key)
        if actual != expected:
            fail(args.metadata_path, f'profdata window mismatch field={key} expected={expected} actual={actual}')
    if args.require_fresh_slot:
        fresh_slot = args.metadata_path.parent / EXPECTED_WINDOW['fresh_slot']
        if not fresh_slot.is_file() or fresh_slot.stat().st_size == 0:
            fail(args.metadata_path, f'missing profdata fresh slot: {EXPECTED_WINDOW["fresh_slot"]}')
    source_commit = metadata.get('source_commit')
    if args.current_commit and source_commit and source_commit != args.current_commit:
        print(f"::warning::PGO profdata source_commit differs from build commit: metadata={args.metadata_path} target={args.expected_target} branch={args.expected_branch} source_commit={source_commit} build_commit={args.current_commit}")
    dependencies = metadata.get('dependencies')
    if isinstance(dependencies, dict):
        missing_dependencies = [field for field in REQUIRED_DEPENDENCY_FIELDS if field not in dependencies]
        if missing_dependencies:
            message = f'{args.metadata_path}: missing profdata dependency metadata: ' + ', '.join(missing_dependencies)
            if args.require_dependency_fields:
                raise SystemExit(message)
            print('::warning::' + message)
        cache_key_mismatches = dependency_cache_key_mismatches(dependencies)
        if cache_key_mismatches:
            message = f'{args.metadata_path}: profdata dependency cache key mismatch: ' + '; '.join(cache_key_mismatches)
            if args.require_dependency_fields:
                raise SystemExit(message)
            print('::warning::' + message)
        required_suffix_mismatches = dependency_required_suffix_mismatches(
            dependencies,
            {
                'ffmpeg': args.required_ffmpeg_cache_suffix,
                'obuparse': args.required_obuparse_cache_suffix,
                'lsmash': args.required_lsmash_cache_suffix,
                'gop_muxer': args.required_gop_muxer_cache_suffix,
            },
        )
        if required_suffix_mismatches:
            message = f'{args.metadata_path}: profdata dependency cache suffix mismatch: ' + '; '.join(required_suffix_mismatches)
            if args.require_dependency_fields:
                raise SystemExit(message)
            print('::warning::' + message)
        summary = ' '.join(f'{field}={dependencies[field]}' for field in DEPENDENCY_SUMMARY_FIELDS if field in dependencies)
        if summary:
            print(f'PGO profdata dependencies: metadata={args.metadata_path} {summary}')
    else:
        message = f'{args.metadata_path}: missing profdata metadata field: dependencies'
        if args.require_dependency_fields:
            raise SystemExit(message)
        print('::warning::' + message)
    print(f"Validated profdata metadata: metadata={args.metadata_path} layout={layout} target_cpu={target_cpu or '<legacy>'} profile_target={profile_target} profdata_branch={profdata_branch} profdata_toolchain={profdata_toolchain or '<legacy>'} llvm_profdata_version={llvm_profdata_version or '<missing>'}")


if __name__ == '__main__':
    main()
