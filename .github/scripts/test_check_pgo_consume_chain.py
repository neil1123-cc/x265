#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_pgo_consume_chain.py')

VALID_METADATA = {
    'profile_target': '8b-lib',
    'profdata_branch': 'profdata-x86-64-8b-lib',
    'profdata_toolchain': 'llvm-20.1',
    'llvm_profdata_version': '20.1.8',
    'layout': 'per-target-bounded-window',
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


def write_metadata(path, metadata=None):
    path.write_text(json.dumps(metadata or VALID_METADATA))


def clone_metadata():
    return json.loads(json.dumps(VALID_METADATA))


def write_compile_commands(build_dir, flag):
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / 'compile_commands.json').write_text(json.dumps([
        {
            'directory': str(build_dir),
            'command': f'c++ -std=gnu++20 {flag} -c source/common/common.cpp',
            'file': str(build_dir.parent / 'source/common/common.cpp'),
        }
    ]))


def write_compile_commands_records(build_dir, records):
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / 'compile_commands.json').write_text(json.dumps(records))


def write_chain(root, consume_flag):
    metadata = root / 'metadata.json'
    profdata = root / 'x265.profdata'
    profiles = root / 'profiles'
    build = root / 'build'
    profiles.mkdir()
    profdata.write_text('profdata\n')
    (profiles / '0.profdata').write_text('fresh profdata\n')
    write_metadata(metadata)
    write_compile_commands(build, consume_flag)
    return metadata, profdata, build


def run_checker(metadata, profdata, build, *extra_args, require_dependency_fields=True):
    command = [
        sys.executable,
        str(CHECKER),
        '--metadata',
        str(metadata),
        '--profdata',
        str(profdata),
        '--build-dir',
        str(build),
        '--expected-target=8b-lib',
        '--expected-branch=profdata-x86-64-8b-lib',
        '--expected-toolchain=llvm-20.1',
        '--require-fresh-slot',
        '--min-cpp-commands=1',
        *extra_args,
    ]
    if require_dependency_fields:
        command.insert(-len(extra_args) if extra_args else len(command), '--require-dependency-fields')
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def expect_metadata_failure(mutator, expected, *extra_args):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        mutated_metadata = clone_metadata()
        mutator(mutated_metadata)
        write_metadata(metadata, mutated_metadata)
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}', *extra_args), expected)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        expect_pass(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'))

        stale_metadata = clone_metadata()
        stale_metadata['dependencies']['ffmpeg_cache_key'] = 'ffmpeg-stale-full-v4-clang'
        write_metadata(metadata, stale_metadata)
        stale_result = run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}', require_dependency_fields=False)
        expect_pass(stale_result)
        if 'profdata dependency cache key mismatch' not in stale_result.stdout:
            raise AssertionError(stale_result.stdout)
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'profdata dependency cache key mismatch')

    expect_metadata_failure(lambda metadata: metadata.pop('layout'), 'missing profdata metadata field: layout')
    expect_metadata_failure(lambda metadata: metadata.pop('window'), 'missing profdata metadata field: window')
    expect_metadata_failure(lambda metadata: metadata.pop('profile_target'), 'missing profdata metadata field: profile_target')
    expect_metadata_failure(lambda metadata: metadata.__setitem__('layout', 'single-branch'), 'profdata layout mismatch')
    expect_metadata_failure(lambda metadata: metadata['window'].__setitem__('slots', 8), 'profdata window mismatch field=slots')
    expect_metadata_failure(lambda metadata: metadata['window'].__setitem__('fresh_slot', 'x265.profdata'), 'profdata window mismatch field=fresh_slot')
    expect_metadata_failure(lambda metadata: metadata['window'].__setitem__('weights_newest_to_oldest', [1, 1, 1, 1]), 'profdata window mismatch field=weights_newest_to_oldest')
    expect_metadata_failure(lambda metadata: metadata.__setitem__('profdata_branch', 'profdata-x86-64-all'), 'profdata_branch mismatch')
    expect_metadata_failure(lambda metadata: metadata.__setitem__('profile_target', 'all'), 'profile_target mismatch')
    expect_metadata_failure(lambda metadata: metadata.pop('llvm_profdata_version'), 'missing profdata metadata field: llvm_profdata_version')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        partial_dependencies = clone_metadata()
        partial_dependencies['dependencies'].pop('gop_muxer_cache_key')
        write_metadata(metadata, partial_dependencies)
        partial_result = run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}', require_dependency_fields=False)
        expect_pass(partial_result)
        if 'missing profdata dependency metadata: gop_muxer_cache_key' not in partial_result.stdout:
            raise AssertionError(partial_result.stdout)
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing profdata dependency metadata: gop_muxer_cache_key')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        metadata.unlink()
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing PGO metadata')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        metadata.write_text('')
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing PGO metadata')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        profdata.unlink()
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing PGO profdata')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        (root / 'profiles' / '0.profdata').unlink()
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing profdata fresh slot')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        (root / 'profiles' / '0.profdata').write_text('')
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing profdata fresh slot')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        profdata.write_text('')
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing PGO profdata')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        stale_target_metadata = clone_metadata()
        stale_target_metadata['profile_target'] = '12b-lib'
        write_metadata(metadata, stale_target_metadata)
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'profile_target mismatch')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        stale_toolchain_metadata = clone_metadata()
        stale_toolchain_metadata['profdata_toolchain'] = 'llvm-19.1'
        write_metadata(metadata, stale_toolchain_metadata)
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'profdata_toolchain mismatch')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        stale_branch_metadata = clone_metadata()
        stale_branch_metadata['profdata_branch'] = 'profdata-x86-64-12b-lib'
        write_metadata(metadata, stale_branch_metadata)
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'profdata_branch mismatch')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata, profdata, build = write_chain(root, '-fprofile-instr-use=/tmp/stale.profdata')
        expect_fail(run_checker(metadata, profdata, build, '--profdata-flag-path=/tmp/x265.profdata'), 'missing required flag -fprofile-instr-use=/tmp/x265.profdata')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path} -fprofile-instr-generate')
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'forbidden flag -fprofile-instr-generate')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path} -fprofile-update=atomic')
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'forbidden flag -fprofile-update=atomic')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path} -fprofile-instr-generate -fprofile-update=atomic')
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'forbidden flag -fprofile-instr-generate')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        write_compile_commands_records(build, [{
            'directory': str(build),
            'command': f'c++ -std=gnu++20 -fprofile-instr-use={profdata_flag_path} -fprofile-update=atomic -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', f'-fprofile-instr-use={profdata_flag_path}', '-fprofile-instr-generate', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'forbidden flag -fprofile-instr-generate')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        metadata_without_dependencies = clone_metadata()
        metadata_without_dependencies.pop('dependencies')
        write_metadata(metadata, metadata_without_dependencies)
        result = run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}', require_dependency_fields=False)
        expect_pass(result)
        if '::warning::' not in result.stdout:
            raise AssertionError(result.stdout)
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing profdata metadata field: dependencies')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        source_commit_metadata = clone_metadata()
        source_commit_metadata['source_commit'] = 'old-commit'
        write_metadata(metadata, source_commit_metadata)
        result = run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}', '--current-commit=new-commit')
        expect_pass(result)
        if 'PGO profdata source_commit differs from build commit' not in result.stdout:
            raise AssertionError(result.stdout)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        write_compile_commands_records(build, [{
            'directory': str(build),
            'command': 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/stale.profdata -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', f'-fprofile-instr-use={profdata_flag_path}', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing required flag -fprofile-instr-use=/tmp/x265.profdata')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        (build / 'pgo.rsp').write_text('-std=gnu++20 -fprofile-instr-use=/tmp/stale.profdata')
        write_compile_commands_records(build, [{
            'directory': str(build),
            'command': 'c++ @pgo.rsp -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', f'-fprofile-instr-use={profdata_flag_path}', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'missing required flag -fprofile-instr-use=/tmp/x265.profdata')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        write_compile_commands_records(build, [{
            'directory': str(build),
            'command': f'c++ -std=gnu++20 -fprofile-instr-use={profdata_flag_path} -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', f'-fprofile-instr-use={profdata_flag_path}', '-fprofile-update=atomic', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'forbidden flag -fprofile-update=atomic')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        (build / 'pgo.rsp').write_text(f'-std=gnu++20 -fprofile-instr-use={profdata_flag_path}')
        write_compile_commands_records(build, [{
            'directory': str(build),
            'command': 'c++ @pgo.rsp -c source/common/common.cpp',
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        (build / 'pgo.rsp').write_text(f'-std=gnu++20 -fprofile-instr-use={profdata_flag_path} -fprofile-update=atomic')
        write_compile_commands_records(build, [{
            'directory': str(build),
            'arguments': ['c++', '@pgo.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'forbidden flag -fprofile-update=atomic')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profdata_flag_path = '/tmp/x265.profdata'
        metadata, profdata, build = write_chain(root, f'-fprofile-instr-use={profdata_flag_path}')
        (build / 'compile_commands.json').write_text(json.dumps([
            {
                'directory': str(build),
                'command': 'cc -std=c11 -c source/common/pixel.c',
                'file': str(root / 'source/common/pixel.c'),
            }
        ]))
        expect_fail(run_checker(metadata, profdata, build, f'--profdata-flag-path={profdata_flag_path}'), 'no C++ compile commands')

    print('PGO metadata/consume chain guardrails validated')


if __name__ == '__main__':
    main()
