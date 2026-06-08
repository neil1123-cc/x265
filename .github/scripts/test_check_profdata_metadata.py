#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from ci_guard_script_runner import run_python_script_main


CHECKER = Path(__file__).with_name('check_profdata_metadata.py')

VALID_METADATA = {
    'layout': 'per-target-bounded-window',
    'profile_target': '8b-lib',
    'profdata_branch': 'profdata-x86-64-8b-lib',
    'profdata_toolchain': 'llvm-20.1',
    'llvm_profdata_version': '20.1.8',
    'window': {
        'slots': 4,
        'fresh_slot': 'profiles/0.profdata',
        'weights_newest_to_oldest': [4, 3, 2, 1],
    },
    'dependencies': {
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
    },
}


def clone_metadata():
    return json.loads(json.dumps(VALID_METADATA))


def run_checker(*args):
    return run_python_script_main(CHECKER, args)


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def write_metadata(path, metadata):
    path.write_text(json.dumps(metadata), encoding='utf-8')


def metadata_args(metadata_path, *extra_args):
    return (
        str(metadata_path),
        '--expected-target=8b-lib',
        '--expected-branch=profdata-x86-64-8b-lib',
        '--expected-toolchain=llvm-20.1',
        '--required-ffmpeg-cache-suffix=full-v4-clang',
        '--required-obuparse-cache-suffix=clang-v1',
        '--required-lsmash-cache-suffix=clang-coff-refptr-v2',
        '--required-gop-muxer-cache-suffix=lsmash-add-box-v2-clang-gnu20',
        *extra_args,
    )


def main():
    expect_pass(run_checker('--self-test'))

    expect_fail(
        run_checker('--self-test', '--expected-target=8b-lib'),
        '--self-test cannot be combined with metadata validation arguments',
    )

    expect_fail(
        run_checker(),
        'metadata_path is required unless --self-test is used',
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata_path = root / 'metadata.json'
        profiles_dir = root / 'profiles'
        profiles_dir.mkdir()
        fresh_slot = profiles_dir / '0.profdata'
        fresh_slot.write_text('fresh profdata\n', encoding='utf-8')
        write_metadata(metadata_path, clone_metadata())

        expect_pass(run_checker(*metadata_args(metadata_path, '--require-dependency-fields', '--require-fresh-slot')))

        missing_layout = clone_metadata()
        missing_layout.pop('layout')
        write_metadata(metadata_path, missing_layout)
        expect_fail(run_checker(*metadata_args(metadata_path)), 'missing profdata metadata field: layout')

        stale_suffix = clone_metadata()
        stale_suffix['dependencies']['gop_muxer_cache_key'] = stale_suffix['dependencies']['gop_muxer_cache_key'].replace('-gnu20', '-gnu17')
        write_metadata(metadata_path, stale_suffix)
        expect_fail(run_checker(*metadata_args(metadata_path, '--require-dependency-fields')), 'profdata dependency cache key mismatch')

        stale_ffmpeg_suffix = clone_metadata()
        stale_ffmpeg_suffix['dependencies']['ffmpeg_cache_key'] = 'ffmpeg-n8.1-full-v5-clang'
        write_metadata(metadata_path, stale_ffmpeg_suffix)
        expect_fail(run_checker(*metadata_args(metadata_path, '--require-dependency-fields')), 'profdata dependency cache suffix mismatch')

        missing_dependencies = clone_metadata()
        missing_dependencies.pop('dependencies')
        write_metadata(metadata_path, missing_dependencies)
        warning_result = run_checker(*metadata_args(metadata_path))
        expect_pass(warning_result)
        if '::warning::' not in warning_result.stdout:
            raise AssertionError(warning_result.stdout)
        expect_fail(run_checker(*metadata_args(metadata_path, '--require-dependency-fields')), 'missing profdata metadata field: dependencies')

        missing_fresh_slot = clone_metadata()
        write_metadata(metadata_path, missing_fresh_slot)
        fresh_slot.unlink()
        expect_fail(run_checker(*metadata_args(metadata_path, '--require-fresh-slot')), 'missing profdata fresh slot: profiles/0.profdata')

        fresh_slot.write_text('fresh profdata\n', encoding='utf-8')
        commit_warning = clone_metadata()
        commit_warning['source_commit'] = 'old-commit'
        write_metadata(metadata_path, commit_warning)
        warning_result = run_checker(*metadata_args(metadata_path, '--current-commit=new-commit'))
        expect_pass(warning_result)
        if 'PGO profdata source_commit differs from build commit' not in warning_result.stdout:
            raise AssertionError(warning_result.stdout)

    print('Profdata metadata tests passed')


if __name__ == '__main__':
    main()
