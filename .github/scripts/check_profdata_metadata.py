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
    return mismatches


def main():
    parser = argparse.ArgumentParser(description='Check x265 PGO profdata metadata')
    parser.add_argument('metadata_path', type=Path)
    parser.add_argument('--expected-target', required=True)
    parser.add_argument('--expected-branch', required=True)
    parser.add_argument('--expected-toolchain')
    parser.add_argument('--current-commit')
    parser.add_argument('--require-dependency-fields', action='store_true')
    parser.add_argument('--require-fresh-slot', action='store_true')
    args = parser.parse_args()

    metadata = json.loads(args.metadata_path.read_text())
    layout = required(args.metadata_path, metadata, 'layout')
    profile_target = required(args.metadata_path, metadata, 'profile_target')
    profdata_branch = required(args.metadata_path, metadata, 'profdata_branch')
    window = required(args.metadata_path, metadata, 'window')
    if layout != EXPECTED_LAYOUT:
        fail(args.metadata_path, f'profdata layout mismatch expected={EXPECTED_LAYOUT} actual={layout}')
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
        summary = ' '.join(f'{field}={dependencies[field]}' for field in DEPENDENCY_SUMMARY_FIELDS if field in dependencies)
        if summary:
            print(f'PGO profdata dependencies: metadata={args.metadata_path} {summary}')
    else:
        message = f'{args.metadata_path}: missing profdata metadata field: dependencies'
        if args.require_dependency_fields:
            raise SystemExit(message)
        print('::warning::' + message)
    print(f"Validated profdata metadata: metadata={args.metadata_path} layout={layout} profile_target={profile_target} profdata_branch={profdata_branch} profdata_toolchain={profdata_toolchain or '<legacy>'} llvm_profdata_version={llvm_profdata_version or '<missing>'}")


if __name__ == '__main__':
    main()
