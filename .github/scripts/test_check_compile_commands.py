#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_compile_commands.py')


def write_compile_commands(build_dir, command, file_path='source/common/common.cpp'):
    write_compile_commands_entries(build_dir, [(command, file_path)])


def write_compile_commands_entries(build_dir, entries):
    build = Path(build_dir)
    build.mkdir(parents=True, exist_ok=True)
    (build / 'compile_commands.json').write_text(json.dumps([
        {
            'directory': str(build),
            'command': command,
            'file': str(build.parent / file_path),
        }
        for command, file_path in entries
    ]))


def write_compile_commands_records(build_dir, records):
    build = Path(build_dir)
    build.mkdir(parents=True, exist_ok=True)
    (build / 'compile_commands.json').write_text(json.dumps(records))


def run_checker(build_dir, *args):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(build_dir), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def ci_shape_records(build_dir, root, overrides=None):
    overrides = overrides or {}
    entries = (
        ('source/common/x86/asm-primitives.cpp', ['-DX265_ARCH_X86=1', '-DX265_DEPTH=8']),
        ('CMakeFiles/common.dir/Unity/unity_0_cxx.cxx', ['-DX265_DEPTH=8']),
        ('source/encoder/api.cpp', ['-DEXPORT_C_API=1', '-DX265_DEPTH=8']),
        ('source/encoder/encoder.cpp', ['-DX265_DEPTH=8']),
        ('source/encoder/ratecontrol.cpp', ['-DX265_DEPTH=8', '-Werror=deprecated-volatile']),
        ('source/output/output.cpp', ['-DX265_DEPTH=10']),
        ('source/output/reconplay.cpp', ['-DX265_DEPTH=8', '-Werror=deprecated-volatile']),
        ('source/common/winxp.cpp', ['-D_WIN32_WINNT=_WIN32_WINNT_WIN7', '-DX265_DEPTH=8']),
        ('source/common/cpu.cpp', ['-march=znver5', '-DX265_DEPTH=8']),
    )
    records = []
    for file_path, flags in entries:
        override = overrides.get(file_path, {})
        command_flags = override.get('command_flags', flags)
        argument_flags = override.get('argument_flags', flags)
        records.append({
            'directory': str(build_dir),
            'command': f"c++ -std=gnu++20 {' '.join(command_flags)} -c {file_path}",
            'arguments': ['c++', '-std=gnu++20', *argument_flags, '-c', file_path],
            'file': str(root / file_path),
        })
    return records


CI_SHAPE_ARGS = (
    '--min-cpp-commands=9',
    '--required-file-substring=source/common/x86/asm-primitives.cpp',
    '--required-file-substring=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx',
    '--required-file-substring=source/encoder/api.cpp',
    '--required-file-substring=source/encoder/encoder.cpp',
    '--required-file-substring=source/encoder/ratecontrol.cpp',
    '--required-file-substring=source/output/output.cpp',
    '--required-file-substring=source/output/reconplay.cpp',
    '--required-file-substring=source/common/winxp.cpp',
    '--required-file-substring=source/common/cpu.cpp',
    '--required-file-flag=source/common/x86/asm-primitives.cpp=-DX265_ARCH_X86=1',
    '--required-file-flag=source/common/x86/asm-primitives.cpp=-DX265_DEPTH=8',
    '--required-file-flag=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx=-DX265_DEPTH=8',
    '--required-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1',
    '--required-file-flag=source/encoder/api.cpp=-DX265_DEPTH=8',
    '--required-file-flag=source/encoder/encoder.cpp=-DX265_DEPTH=8',
    '--required-file-flag=source/encoder/ratecontrol.cpp=-Werror=deprecated-volatile',
    '--required-file-flag=source/encoder/ratecontrol.cpp=-DX265_DEPTH=8',
    '--required-file-flag=source/output/output.cpp=-DX265_DEPTH=10',
    '--required-file-flag=source/output/reconplay.cpp=-Werror=deprecated-volatile',
    '--required-file-flag=source/output/reconplay.cpp=-DX265_DEPTH=8',
    '--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7',
    '--required-file-flag=source/common/winxp.cpp=-DX265_DEPTH=8',
    '--required-file-flag=source/common/cpu.cpp=-march=znver5',
    '--required-file-flag=source/common/cpu.cpp=-DX265_DEPTH=8',
    '--forbidden-file-flag=source/common/x86/asm-primitives.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/common/x86/asm-primitives.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx=-DX265_DEPTH=10',
    '--forbidden-file-flag=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/encoder/api.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/encoder/api.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF',
    '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_MKV',
    '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LSMASH',
    '--forbidden-file-flag=source/encoder/encoder.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/encoder/ratecontrol.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/encoder/ratecontrol.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/output/reconplay.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/output/reconplay.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP',
    '--forbidden-file-flag=source/common/winxp.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/common/winxp.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/common/cpu.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/common/cpu.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/output/output.cpp=-DX265_DEPTH=8',
    '--forbidden-file-flag=source/output/output.cpp=-DX265_DEPTH=12',
)


def run_ci_shape_checker(build_dir):
    return run_checker(build_dir, *CI_SHAPE_ARGS)


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
        root = Path(tmp)
        write_compile_commands(root / 'pass', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp')
        expect_pass(run_checker(root / 'pass', '--required-flag=-Wdeprecated', '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8', '--min-cpp-commands=1', '--required-file-substring=source/common/'))

        missing_commands_dir = root / 'missing-compile-commands'
        missing_commands_dir.mkdir()
        expect_fail(run_checker(missing_commands_dir), 'missing compile_commands.json')

        invalid_json_dir = root / 'invalid-json'
        invalid_json_dir.mkdir()
        (invalid_json_dir / 'compile_commands.json').write_text('{')
        expect_fail(run_checker(invalid_json_dir), 'invalid compile_commands.json')

        object_json_dir = root / 'object-json'
        object_json_dir.mkdir()
        (object_json_dir / 'compile_commands.json').write_text('{}')
        expect_fail(run_checker(object_json_dir), 'compile_commands.json must contain a list')

        missing_file_field_dir = root / 'missing-file-field'
        write_compile_commands_records(missing_file_field_dir, [{
            'directory': str(missing_file_field_dir),
            'command': 'c++ -std=gnu++20 -c source/common/common.cpp',
        }])
        expect_fail(run_checker(missing_file_field_dir), 'compile command entry #1 is missing file field')

        nonobject_entry_dir = root / 'nonobject-entry'
        write_compile_commands_records(nonobject_entry_dir, ['c++ -std=gnu++20 -c source/common/common.cpp'])
        expect_fail(run_checker(nonobject_entry_dir), 'compile command entry #1 must be an object')

        nonstring_file_dir = root / 'nonstring-file-field'
        write_compile_commands_records(nonstring_file_dir, [{
            'directory': str(nonstring_file_dir),
            'command': 'c++ -std=gnu++20 -c source/common/common.cpp',
            'file': 17,
        }])
        expect_fail(run_checker(nonstring_file_dir), 'compile command entry #1 file field must be a string')

        nonstring_directory_dir = root / 'nonstring-directory-field'
        write_compile_commands_records(nonstring_directory_dir, [{
            'directory': 17,
            'command': 'c++ -std=gnu++20 -c source/common/common.cpp',
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(nonstring_directory_dir), 'compile command entry #1 directory field must be a string')

        missing_command_fields_dir = root / 'missing-command-fields'
        write_compile_commands_records(missing_command_fields_dir, [{
            'directory': str(missing_command_fields_dir),
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_fields_dir), 'compile command entry #1 is missing command or arguments field')

        nonstring_command_dir = root / 'nonstring-command-field'
        write_compile_commands_records(nonstring_command_dir, [{
            'directory': str(nonstring_command_dir),
            'command': ['c++', '-std=gnu++20', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(nonstring_command_dir), 'compile command entry #1 command field must be a string')

        nonlist_arguments_dir = root / 'nonlist-arguments-field'
        write_compile_commands_records(nonlist_arguments_dir, [{
            'directory': str(nonlist_arguments_dir),
            'arguments': 'c++ -std=gnu++20 -c source/common/common.cpp',
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(nonlist_arguments_dir), 'compile command entry #1 arguments field must be a list')

        nonstring_arguments_dir = root / 'nonstring-arguments-field'
        write_compile_commands_records(nonstring_arguments_dir, [{
            'directory': str(nonstring_arguments_dir),
            'arguments': ['c++', '-std=gnu++20', 17, '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(nonstring_arguments_dir), 'compile command entry #1 arguments field must contain only strings')

        ci_shape_dir = root / 'ci-shape-dual-field-pass'
        write_compile_commands_records(ci_shape_dir, ci_shape_records(ci_shape_dir, root))
        expect_pass(run_ci_shape_checker(ci_shape_dir))

        asm_shape_missing_dir = root / 'ci-shape-asm-arguments-missing-arch'
        write_compile_commands_records(asm_shape_missing_dir, ci_shape_records(asm_shape_missing_dir, root, {
            'source/common/x86/asm-primitives.cpp': {
                'argument_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(asm_shape_missing_dir), 'missing required flag -DX265_ARCH_X86=1 for file substring source/common/x86/asm-primitives.cpp')

        unity_shape_missing_dir = root / 'ci-shape-unity-command-missing-depth'
        write_compile_commands_records(unity_shape_missing_dir, ci_shape_records(unity_shape_missing_dir, root, {
            'CMakeFiles/common.dir/Unity/unity_0_cxx.cxx': {
                'command_flags': [],
            },
        }))
        expect_fail(run_ci_shape_checker(unity_shape_missing_dir), 'missing required flag -DX265_DEPTH=8 for file substring CMakeFiles/common.dir/Unity/unity_0_cxx.cxx')

        shared_api_missing_dir = root / 'ci-shape-shared-api-command-missing-export'
        write_compile_commands_records(shared_api_missing_dir, ci_shape_records(shared_api_missing_dir, root, {
            'source/encoder/api.cpp': {
                'command_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(shared_api_missing_dir), 'missing required flag -DEXPORT_C_API=1 for file substring source/encoder/api.cpp')

        encoder_dep_leak_dir = root / 'ci-shape-encoder-arguments-dep-leak'
        write_compile_commands_records(encoder_dep_leak_dir, ci_shape_records(encoder_dep_leak_dir, root, {
            'source/encoder/encoder.cpp': {
                'argument_flags': ['-DX265_DEPTH=8', '-DENABLE_LAVF'],
            },
        }))
        expect_fail(run_ci_shape_checker(encoder_dep_leak_dir), 'forbidden flag -DENABLE_LAVF for file substring source/encoder/encoder.cpp')

        ratecontrol_warning_missing_dir = root / 'ci-shape-ratecontrol-command-missing-warning'
        write_compile_commands_records(ratecontrol_warning_missing_dir, ci_shape_records(ratecontrol_warning_missing_dir, root, {
            'source/encoder/ratecontrol.cpp': {
                'command_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(ratecontrol_warning_missing_dir), 'missing required flag -Werror=deprecated-volatile for file substring source/encoder/ratecontrol.cpp')

        reconplay_warning_missing_dir = root / 'ci-shape-reconplay-arguments-missing-warning'
        write_compile_commands_records(reconplay_warning_missing_dir, ci_shape_records(reconplay_warning_missing_dir, root, {
            'source/output/reconplay.cpp': {
                'argument_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(reconplay_warning_missing_dir), 'missing required flag -Werror=deprecated-volatile for file substring source/output/reconplay.cpp')

        all_depth_forbidden_dir = root / 'ci-shape-all-bit-depth-arguments-forbidden-depth'
        write_compile_commands_records(all_depth_forbidden_dir, ci_shape_records(all_depth_forbidden_dir, root, {
            'source/output/output.cpp': {
                'argument_flags': ['-DX265_DEPTH=10', '-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(all_depth_forbidden_dir), 'forbidden flag -DX265_DEPTH=8 for file substring source/output/output.cpp')

        winxp_forbidden_dir = root / 'ci-shape-winxp-arguments-forbidden-target'
        write_compile_commands_records(winxp_forbidden_dir, ci_shape_records(winxp_forbidden_dir, root, {
            'source/common/winxp.cpp': {
                'argument_flags': ['-D_WIN32_WINNT=_WIN32_WINNT_WIN7', '-D_WIN32_WINNT=_WIN32_WINNT_WINXP', '-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(winxp_forbidden_dir), 'forbidden flag -D_WIN32_WINNT=_WIN32_WINNT_WINXP for file substring source/common/winxp.cpp')

        cpu_target_missing_dir = root / 'ci-shape-cpu-target-command-missing-march'
        write_compile_commands_records(cpu_target_missing_dir, ci_shape_records(cpu_target_missing_dir, root, {
            'source/common/cpu.cpp': {
                'command_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(cpu_target_missing_dir), 'missing required flag -march=znver5 for file substring source/common/cpu.cpp')

        shared_deps_shape_dir = root / 'ci-shape-shared-deps-dual-field-pass'
        shared_deps_entries = (
            ('source/input/lavf.cpp', ['-DX265_DEPTH=8', '-DENABLE_LAVF']),
            ('source/output/mkv.cpp', ['-DX265_DEPTH=8', '-DENABLE_MKV']),
            ('source/output/mp4.cpp', ['-DX265_DEPTH=8', '-DENABLE_LSMASH']),
            ('source/common/common.cpp', ['-DX265_DEPTH=8']),
            ('source/encoder/encoder.cpp', ['-DX265_DEPTH=8']),
        )
        write_compile_commands_records(shared_deps_shape_dir, [
            {
                'directory': str(shared_deps_shape_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags)} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *flags, '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in shared_deps_entries
        ])
        shared_deps_args = (
            '--min-cpp-commands=5',
            '--required-depth-define=-DX265_DEPTH=8',
            '--forbidden-flag=-DX265_DEPTH=10',
            '--forbidden-flag=-DX265_DEPTH=12',
            '--required-file-substring=source/input/lavf.cpp',
            '--required-file-substring=source/output/mkv.cpp',
            '--required-file-substring=source/output/mp4.cpp',
            '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF',
            '--required-file-flag=source/output/mkv.cpp=-DENABLE_MKV',
            '--required-file-flag=source/output/mp4.cpp=-DENABLE_LSMASH',
            '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF',
            '--forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV',
            '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH',
            '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF',
            '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_MKV',
            '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LSMASH',
        )
        expect_pass(run_checker(shared_deps_shape_dir, *shared_deps_args))

        shared_deps_common_leak_dir = root / 'ci-shape-shared-deps-common-arguments-leak'
        write_compile_commands_records(shared_deps_common_leak_dir, [
            {
                'directory': str(shared_deps_common_leak_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags)} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *(flags + (['-DENABLE_LSMASH'] if file_path == 'source/common/common.cpp' else [])), '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in shared_deps_entries
        ])
        expect_fail(run_checker(shared_deps_common_leak_dir, *shared_deps_args), 'forbidden flag -DENABLE_LSMASH for file substring source/common/common.cpp')

        lib_only_shape_entries = (
            ('source/encoder/api.cpp', ['-DX265_DEPTH=12']),
            ('source/common/version.cpp', ['-DX265_DEPTH=12']),
            ('source/encoder/encoder.cpp', ['-DX265_DEPTH=12']),
        )
        lib_only_shape_args = (
            '--min-cpp-commands=3',
            '--required-depth-define=-DX265_DEPTH=12',
            '--forbidden-flag=-DX265_DEPTH=8',
            '--forbidden-flag=-DX265_DEPTH=10',
            '--required-file-substring=source/encoder/api.cpp',
            '--required-file-substring=source/common/version.cpp',
            '--forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1',
            '--forbidden-file-substring=source/input/',
            '--forbidden-file-substring=source/output/',
            '--forbidden-file-substring=source/abrEncApp.cpp',
            '--forbidden-file-substring=source/x265.cpp',
            '--forbidden-file-substring=source/x265cli.cpp',
        )
        lib_only_shape_dir = root / 'ci-shape-12bit-lib-only-dual-field-pass'
        write_compile_commands_records(lib_only_shape_dir, [
            {
                'directory': str(lib_only_shape_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags)} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *flags, '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in lib_only_shape_entries
        ])
        expect_pass(run_checker(lib_only_shape_dir, *lib_only_shape_args))

        lib_only_cli_leak_dir = root / 'ci-shape-12bit-lib-only-cli-source-leak'
        write_compile_commands_records(lib_only_cli_leak_dir, [
            {
                'directory': str(lib_only_cli_leak_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags)} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *flags, '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in (*lib_only_shape_entries, ('source/x265.cpp', ['-DX265_DEPTH=12']))
        ])
        expect_fail(run_checker(lib_only_cli_leak_dir, *lib_only_shape_args), 'forbidden compile command for file substring source/x265.cpp')

        lib_only_export_leak_dir = root / 'ci-shape-12bit-lib-only-api-export-leak'
        write_compile_commands_records(lib_only_export_leak_dir, [
            {
                'directory': str(lib_only_export_leak_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags + (['-DEXPORT_C_API=1'] if file_path == 'source/encoder/api.cpp' else []))} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *flags, '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in lib_only_shape_entries
        ])
        expect_fail(run_checker(lib_only_export_leak_dir, *lib_only_shape_args), 'forbidden flag -DEXPORT_C_API=1 for file substring source/encoder/api.cpp')

        lib_only_mixed_depth_dir = root / 'ci-shape-12bit-lib-only-arguments-mixed-depth'
        write_compile_commands_records(lib_only_mixed_depth_dir, [
            {
                'directory': str(lib_only_mixed_depth_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags)} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *(flags + (['-DX265_DEPTH=8'] if file_path == 'source/encoder/encoder.cpp' else [])), '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in lib_only_shape_entries
        ])
        expect_fail(run_checker(lib_only_mixed_depth_dir, *lib_only_shape_args), 'forbidden flag -DX265_DEPTH=8')

        all_bit_depth_shape_entries = (
            ('source/output/output.cpp', ['-DX265_DEPTH=10']),
            ('source/dynamicHDR10/metadataFromJson.cpp', ['-DX265_DEPTH=10']),
            ('source/common/version.cpp', ['-DX265_DEPTH=10', '-DLINKED_8BIT=1', '-DLINKED_12BIT=1']),
            ('source/encoder/api.cpp', ['-DX265_DEPTH=10', '-DLINKED_8BIT=1', '-DLINKED_12BIT=1']),
            ('source/encoder/encoder.cpp', ['-DX265_DEPTH=10']),
        )
        all_bit_depth_shape_args = (
            '--min-cpp-commands=5',
            '--required-depth-define=-DX265_DEPTH=10',
            '--forbidden-flag=-DX265_DEPTH=8',
            '--forbidden-flag=-DX265_DEPTH=12',
            '--required-file-substring=source/output/output.cpp',
            '--required-file-substring=source/dynamicHDR10/',
            '--required-file-substring=source/common/version.cpp',
            '--required-file-substring=source/encoder/api.cpp',
            '--required-file-flag=source/output/output.cpp=-DX265_DEPTH=10',
            '--required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1',
            '--required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1',
            '--required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1',
            '--required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1',
            '--forbidden-file-substring=source/input/lavf.cpp',
            '--forbidden-file-substring=source/output/mp4.cpp',
            '--forbidden-file-flag=source/output/output.cpp=-DLINKED_8BIT=1',
            '--forbidden-file-flag=source/output/output.cpp=-DLINKED_12BIT=1',
            '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF',
            '--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LSMASH',
        )
        all_bit_depth_shape_dir = root / 'ci-shape-all-bit-depth-dual-field-pass'
        write_compile_commands_records(all_bit_depth_shape_dir, [
            {
                'directory': str(all_bit_depth_shape_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags)} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *flags, '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in all_bit_depth_shape_entries
        ])
        expect_pass(run_checker(all_bit_depth_shape_dir, *all_bit_depth_shape_args))

        all_bit_depth_missing_linked_dir = root / 'ci-shape-all-bit-depth-command-missing-version-linked-12bit'
        write_compile_commands_records(all_bit_depth_missing_linked_dir, [
            {
                'directory': str(all_bit_depth_missing_linked_dir),
                'command': f"c++ -std=gnu++20 {' '.join([flag for flag in flags if not (file_path == 'source/common/version.cpp' and flag == '-DLINKED_12BIT=1')])} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *flags, '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in all_bit_depth_shape_entries
        ])
        expect_fail(run_checker(all_bit_depth_missing_linked_dir, *all_bit_depth_shape_args), 'missing required flag -DLINKED_12BIT=1 for file substring source/common/version.cpp')

        all_bit_depth_output_linked_leak_dir = root / 'ci-shape-all-bit-depth-output-linked-leak'
        write_compile_commands_records(all_bit_depth_output_linked_leak_dir, [
            {
                'directory': str(all_bit_depth_output_linked_leak_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags + (['-DLINKED_8BIT=1'] if file_path == 'source/output/output.cpp' else []))} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *flags, '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in all_bit_depth_shape_entries
        ])
        expect_fail(run_checker(all_bit_depth_output_linked_leak_dir, *all_bit_depth_shape_args), 'forbidden flag -DLINKED_8BIT=1 for file substring source/output/output.cpp')

        all_bit_depth_cli_macro_leak_dir = root / 'ci-shape-all-bit-depth-encoder-cli-macro-leak'
        write_compile_commands_records(all_bit_depth_cli_macro_leak_dir, [
            {
                'directory': str(all_bit_depth_cli_macro_leak_dir),
                'command': f"c++ -std=gnu++20 {' '.join(flags)} -c {file_path}",
                'arguments': ['c++', '-std=gnu++20', *(flags + (['-DENABLE_LAVF'] if file_path == 'source/encoder/encoder.cpp' else [])), '-c', file_path],
                'file': str(root / file_path),
            }
            for file_path, flags in all_bit_depth_shape_entries
        ])
        expect_fail(run_checker(all_bit_depth_cli_macro_leak_dir, *all_bit_depth_shape_args), 'forbidden flag -DENABLE_LAVF for file substring source/encoder/encoder.cpp')

        write_compile_commands(root / 'profiling-flags', 'c++ -std=gnu++20 -fprofile-instr-generate -fprofile-update=atomic -c source/common/common.cpp')
        expect_pass(run_checker(root / 'profiling-flags', '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic', '--forbidden-flag-substring=-fprofile-instr-use='))

        write_compile_commands(root / 'profiling-consume-leak', 'c++ -std=gnu++20 -fprofile-instr-generate -fprofile-update=atomic -fprofile-instr-use=/tmp/x265.profdata -c source/common/common.cpp')
        expect_fail(run_checker(root / 'profiling-consume-leak', '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic', '--forbidden-flag-substring=-fprofile-instr-use='), 'forbidden flag substring -fprofile-instr-use=')

        write_compile_commands(root / 'profiling-consume-split-leak', 'c++ -std=gnu++20 -fprofile-instr-generate -fprofile-update=atomic -fprofile-instr-use /tmp/x265.profdata -c source/common/common.cpp')
        expect_fail(run_checker(root / 'profiling-consume-split-leak', '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic', '--forbidden-flag=-fprofile-instr-use', '--forbidden-flag-substring=-fprofile-instr-use='), 'forbidden flag -fprofile-instr-use')

        write_compile_commands(root / 'missing-profiling-flag', 'c++ -std=gnu++20 -fprofile-instr-generate -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-profiling-flag', '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic'), 'missing required flag -fprofile-update=atomic')

        malformed_required_file_flag_dir = root / 'malformed-required-file-flag'
        write_compile_commands(malformed_required_file_flag_dir, 'c++ -std=gnu++20 -DENABLE_LAVF -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_fail(run_checker(malformed_required_file_flag_dir, '--required-file-flag=source/input/lavf.cpp'), 'invalid file flag rule')

        malformed_forbidden_file_flag_dir = root / 'malformed-forbidden-file-flag'
        write_compile_commands(malformed_forbidden_file_flag_dir, 'c++ -std=gnu++20 -DENABLE_LAVF -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_fail(run_checker(malformed_forbidden_file_flag_dir, '--forbidden-file-flag=source/input/lavf.cpp='), 'invalid file flag rule')

        profiling_mixed_fields_dir = root / 'profiling-mixed-fields'
        write_compile_commands_records(profiling_mixed_fields_dir, [{
            'directory': str(profiling_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -fprofile-instr-generate -fprofile-update=atomic -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-fprofile-instr-generate', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(profiling_mixed_fields_dir, '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic'), 'missing required flag -fprofile-update=atomic')

        write_compile_commands(root / 'pgo-consume-flag', 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -c source/common/common.cpp')
        expect_pass(run_checker(root / 'pgo-consume-flag', '--required-flag-prefix=-fprofile-instr-use='))

        write_compile_commands(root / 'pgo-consume-missing', 'c++ -std=gnu++20 -fprofile-sample-use=/tmp/x265.profdata -c source/common/common.cpp')
        expect_fail(run_checker(root / 'pgo-consume-missing', '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        write_compile_commands(root / 'pgo-consume-split-spelling', 'c++ -std=gnu++20 -fprofile-instr-use /tmp/x265.profdata -c source/common/common.cpp')
        expect_fail(run_checker(root / 'pgo-consume-split-spelling', '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        write_compile_commands(root / 'pgo-consume-generate-leak', 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -fprofile-instr-generate -fprofile-update=atomic -c source/common/common.cpp')
        expect_fail(run_checker(root / 'pgo-consume-generate-leak', '--required-flag-prefix=-fprofile-instr-use=', '--forbidden-flag=-fprofile-instr-generate', '--forbidden-flag=-fprofile-update=atomic'), 'forbidden flag -fprofile-instr-generate')

        pgo_consume_arguments_leak_dir = root / 'pgo-consume-arguments-generate-leak'
        write_compile_commands_records(pgo_consume_arguments_leak_dir, [{
            'directory': str(pgo_consume_arguments_leak_dir),
            'command': 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-fprofile-instr-use=/tmp/x265.profdata', '-fprofile-update=atomic', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(pgo_consume_arguments_leak_dir, '--required-flag-prefix=-fprofile-instr-use=', '--forbidden-flag=-fprofile-update=atomic'), 'forbidden flag -fprofile-update=atomic')

        pgo_consume_response_dir = root / 'pgo-consume-response-file'
        pgo_consume_response_dir.mkdir()
        (pgo_consume_response_dir / 'pgo.rsp').write_text('-std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata')
        write_compile_commands(pgo_consume_response_dir, 'c++ @pgo.rsp -c source/common/common.cpp')
        expect_pass(run_checker(pgo_consume_response_dir, '--required-flag-prefix=-fprofile-instr-use='))

        pgo_consume_quoted_path_response_dir = root / 'pgo-consume-quoted-path-response-file'
        pgo_consume_quoted_path_response_dir.mkdir()
        (pgo_consume_quoted_path_response_dir / 'pgo path.rsp').write_text('-std=gnu++20 "-fprofile-instr-use=C:/Program Files/x265.profdata"')
        write_compile_commands(pgo_consume_quoted_path_response_dir, 'c++ @"pgo path.rsp" -c source/common/common.cpp')
        expect_pass(run_checker(pgo_consume_quoted_path_response_dir, '--required-flag-prefix=-fprofile-instr-use='))

        pgo_consume_arguments_response_dir = root / 'pgo-consume-arguments-response-file'
        pgo_consume_arguments_response_dir.mkdir()
        (pgo_consume_arguments_response_dir / 'pgo.rsp').write_text('-std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata')
        write_compile_commands_records(pgo_consume_arguments_response_dir, [{
            'directory': str(pgo_consume_arguments_response_dir),
            'arguments': ['c++', '@pgo.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(pgo_consume_arguments_response_dir, '--required-flag-prefix=-fprofile-instr-use='))

        pgo_consume_arguments_response_missing_dir = root / 'pgo-consume-arguments-response-missing-prefix'
        pgo_consume_arguments_response_missing_dir.mkdir()
        (pgo_consume_arguments_response_missing_dir / 'pgo.rsp').write_text('-std=gnu++20 -fprofile-sample-use=/tmp/x265.profdata')
        write_compile_commands_records(pgo_consume_arguments_response_missing_dir, [{
            'directory': str(pgo_consume_arguments_response_missing_dir),
            'arguments': ['c++', '@pgo.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(pgo_consume_arguments_response_missing_dir, '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        pgo_consume_response_missing_dir = root / 'pgo-consume-response-file-missing-prefix'
        pgo_consume_response_missing_dir.mkdir()
        (pgo_consume_response_missing_dir / 'pgo.rsp').write_text('-std=gnu++20 -fprofile-sample-use=/tmp/x265.profdata')
        write_compile_commands(pgo_consume_response_missing_dir, 'c++ @pgo.rsp -c source/common/common.cpp')
        expect_fail(run_checker(pgo_consume_response_missing_dir, '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        pgo_consume_mixed_fields_dir = root / 'pgo-consume-mixed-fields'
        write_compile_commands_records(pgo_consume_mixed_fields_dir, [{
            'directory': str(pgo_consume_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(pgo_consume_mixed_fields_dir, '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        pgo_consume_command_missing_dir = root / 'pgo-consume-command-missing-prefix'
        write_compile_commands_records(pgo_consume_command_missing_dir, [{
            'directory': str(pgo_consume_command_missing_dir),
            'command': 'c++ -std=gnu++20 -fprofile-sample-use=/tmp/x265.profdata -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-fprofile-instr-use=/tmp/x265.profdata', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(pgo_consume_command_missing_dir, '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        write_compile_commands(root / 'pass-msvc-std', 'cl /std:c++20 /c source/common/common.cpp')
        expect_pass(run_checker(root / 'pass-msvc-std', '--min-cpp-commands=1'))

        write_compile_commands(root / 'quoted-clang-cl-path', '"C:/Program Files/LLVM/bin/clang-cl.exe" /std:c++20 /c source/common/common.cpp')
        expect_pass(run_checker(root / 'quoted-clang-cl-path', '--min-cpp-commands=1'))

        write_compile_commands(root / 'quoted-clang-cl-old-std', '"C:/Program Files/LLVM/bin/clang-cl.exe" /std:c++17 /c source/common/common.cpp')
        expect_fail(run_checker(root / 'quoted-clang-cl-old-std'), 'old standard flag /std:c++17')

        msvc_arguments_dir = root / 'pass-msvc-arguments'
        write_compile_commands_records(msvc_arguments_dir, [{
            'directory': str(msvc_arguments_dir),
            'arguments': ['clang-cl', '/std:c++20', '/c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(msvc_arguments_dir, '--min-cpp-commands=1'))

        msvc_latest_arguments_dir = root / 'msvc-latest-arguments'
        write_compile_commands_records(msvc_latest_arguments_dir, [{
            'directory': str(msvc_latest_arguments_dir),
            'arguments': ['clang-cl', '/std:c++latest', '/c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(msvc_latest_arguments_dir), 'old standard flag /std:c++latest')

        both_fields_dir = root / 'pass-command-arguments-same-std'
        write_compile_commands_records(both_fields_dir, [{
            'directory': str(both_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(both_fields_dir, '--required-flag=-Wdeprecated', '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        missing_argument_flag_dir = root / 'command-arguments-missing-required-flag'
        write_compile_commands_records(missing_argument_flag_dir, [{
            'directory': str(missing_argument_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_argument_flag_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        missing_command_flag_dir = root / 'command-field-missing-required-flag'
        write_compile_commands_records(missing_command_flag_dir, [{
            'directory': str(missing_command_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_flag_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        forbidden_argument_flag_dir = root / 'command-arguments-forbidden-flag'
        write_compile_commands_records(forbidden_argument_flag_dir, [{
            'directory': str(forbidden_argument_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-Wno-deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(forbidden_argument_flag_dir, '--forbidden-flag-substring=-Wno-deprecated'), 'forbidden flag substring -Wno-deprecated')

        forbidden_command_flag_dir = root / 'command-field-forbidden-flag'
        write_compile_commands_records(forbidden_command_flag_dir, [{
            'directory': str(forbidden_command_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -Wno-deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(forbidden_command_flag_dir, '--forbidden-flag-substring=-Wno-deprecated'), 'forbidden flag substring -Wno-deprecated')

        exact_forbidden_argument_flag_dir = root / 'command-arguments-exact-forbidden-flag'
        write_compile_commands_records(exact_forbidden_argument_flag_dir, [{
            'directory': str(exact_forbidden_argument_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=12', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(exact_forbidden_argument_flag_dir, '--forbidden-flag=-DX265_DEPTH=12'), 'forbidden flag -DX265_DEPTH=12')

        exact_forbidden_command_flag_dir = root / 'command-field-exact-forbidden-flag'
        write_compile_commands_records(exact_forbidden_command_flag_dir, [{
            'directory': str(exact_forbidden_command_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=12 -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(exact_forbidden_command_flag_dir, '--forbidden-flag=-DX265_DEPTH=12'), 'forbidden flag -DX265_DEPTH=12')

        missing_argument_depth_dir = root / 'command-arguments-missing-depth'
        write_compile_commands_records(missing_argument_depth_dir, [{
            'directory': str(missing_argument_depth_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_argument_depth_dir, '--required-depth-define=-DX265_DEPTH=8'), 'missing -DX265_DEPTH=8')

        missing_command_depth_dir = root / 'command-field-missing-depth'
        write_compile_commands_records(missing_command_depth_dir, [{
            'directory': str(missing_command_depth_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_depth_dir, '--required-depth-define=-DX265_DEPTH=8'), 'missing -DX265_DEPTH=8')

        windows_path_dir = root / 'windows-path-substring'
        write_compile_commands_records(windows_path_dir, [{
            'directory': str(windows_path_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp',
            'file': str(root / 'source\\input\\lavf.cpp'),
        }])
        expect_pass(run_checker(windows_path_dir, '--required-file-substring=source/input/lavf.cpp', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'))

        windows_backslash_arg_dir = root / 'windows-backslash-arg-substrings'
        write_compile_commands_records(windows_backslash_arg_dir, [{
            'directory': str(windows_backslash_arg_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp',
            'file': str(root / 'source/input/lavf.cpp'),
        }])
        expect_pass(run_checker(windows_backslash_arg_dir, '--required-file-substring=source\\input\\lavf.cpp', '--required-file-flag=source\\input\\lavf.cpp=-DENABLE_LAVF', '--forbidden-file-flag=source\\input\\lavf.cpp=-DENABLE_MKV'))

        windows_forbidden_backslash_arg_dir = root / 'windows-forbidden-backslash-arg-substring'
        write_compile_commands_records(windows_forbidden_backslash_arg_dir, [{
            'directory': str(windows_forbidden_backslash_arg_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/output/mp4.cpp',
            'file': str(root / 'source/output/mp4.cpp'),
        }])
        expect_fail(run_checker(windows_forbidden_backslash_arg_dir, '--forbidden-file-substring=source\\output\\mp4.cpp'), 'forbidden compile command for file substring source/output/mp4.cpp')

        mixed_fields_dir = root / 'mixed-command-arguments-std'
        write_compile_commands_records(mixed_fields_dir, [{
            'directory': str(mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=c++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_fields_dir), 'duplicate standard flags -std=c++20,-std=gnu++20')

        mixed_msvc_fields_dir = root / 'mixed-msvc-command-arguments-std'
        write_compile_commands_records(mixed_msvc_fields_dir, [{
            'directory': str(mixed_msvc_fields_dir),
            'command': 'cl /std:c++20 /c source/common/common.cpp',
            'arguments': ['clang-cl', '-std=gnu++20', '/c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_msvc_fields_dir), 'duplicate standard flags -std=gnu++20,/std:c++20')

        equivalent_std_fields_dir = root / 'equivalent-command-arguments-std'
        write_compile_commands_records(equivalent_std_fields_dir, [{
            'directory': str(equivalent_std_fields_dir),
            'command': 'c++ -std gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '--std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(equivalent_std_fields_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        missing_argument_std_dir = root / 'command-arguments-missing-std'
        write_compile_commands_records(missing_argument_std_dir, [{
            'directory': str(missing_argument_std_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_argument_std_dir), 'missing GNU++20 dialect')

        missing_command_std_dir = root / 'command-field-missing-std'
        write_compile_commands_records(missing_command_std_dir, [{
            'directory': str(missing_command_std_dir),
            'command': 'c++ -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_std_dir), 'missing GNU++20 dialect')

        empty_arguments_dir = root / 'command-empty-arguments-std'
        write_compile_commands_records(empty_arguments_dir, [{
            'directory': str(empty_arguments_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': [],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(empty_arguments_dir), 'missing GNU++20 dialect')

        empty_command_dir = root / 'empty-command-field-std'
        write_compile_commands_records(empty_command_dir, [{
            'directory': str(empty_command_dir),
            'command': '',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(empty_command_dir), 'missing GNU++20 dialect')

        arguments_dir = root / 'pass-arguments'
        write_compile_commands_records(arguments_dir, [{
            'directory': str(arguments_dir),
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(arguments_dir, '--required-flag=-Wdeprecated', '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8', '--min-cpp-commands=1'))

        write_compile_commands(root / 'gnu20-double-dash', 'c++ --std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_pass(run_checker(root / 'gnu20-double-dash', '--min-cpp-commands=1'))

        write_compile_commands(root / 'gnu20-split-std', 'c++ -std gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_pass(run_checker(root / 'gnu20-split-std', '--min-cpp-commands=1'))

        split_std_arguments_dir = root / 'split-std-arguments'
        write_compile_commands_records(split_std_arguments_dir, [{
            'directory': str(split_std_arguments_dir),
            'arguments': ['c++', '--std', 'gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(split_std_arguments_dir, '--min-cpp-commands=1'))

        write_compile_commands(root / 'plain-cxx20-split-std', 'c++ -std c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'plain-cxx20-split-std'), 'non-GNU C++20 dialect flag -std=c++20')

        write_compile_commands(root / 'old-gnu17-split-std', 'c++ --std gnu++17 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu17-split-std'), 'old standard flag --std=gnu++17')

        write_compile_commands(root / 'plain-cxx20-double-dash', 'c++ --std=c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'plain-cxx20-double-dash'), 'non-GNU C++20 dialect flag --std=c++20')

        write_compile_commands(root / 'old-gnu17-double-dash', 'c++ --std=gnu++17 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu17-double-dash'), 'old standard flag --std=gnu++17')

        write_compile_commands(root / 'old-gnu', 'c++ -std=gnu++17 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu'), 'old standard flag -std=gnu++17')

        write_compile_commands(root / 'old-gnu2a', 'c++ -std=gnu++2a -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu2a'), 'old standard flag -std=gnu++2a')

        write_compile_commands(root / 'old-cxx2a', 'c++ -std=c++2a -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-cxx2a'), 'old standard flag -std=c++2a')

        write_compile_commands(root / 'plain-cxx20', 'c++ -std=c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'plain-cxx20'), 'non-GNU C++20 dialect flag -std=c++20')

        write_compile_commands(root / 'mixed-plain-cxx20', 'c++ -std=gnu++20 -std=c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'mixed-plain-cxx20'), 'duplicate standard flags -std=gnu++20,-std=c++20')

        write_compile_commands(root / 'mixed-old-std', 'c++ -std=gnu++20 -std=gnu++2a -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'mixed-old-std'), 'duplicate standard flags -std=gnu++20,-std=gnu++2a')

        write_compile_commands(root / 'duplicate-gnu20', 'c++ -std=gnu++20 -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'duplicate-gnu20'), 'duplicate standard flags -std=gnu++20,-std=gnu++20')

        write_compile_commands(root / 'old-msvc', 'cl /std:c++17 /c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-msvc'), 'old standard flag /std:c++17')

        write_compile_commands(root / 'missing-std', 'c++ -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-std'), 'missing GNU++20 dialect')

        write_compile_commands(root / 'missing-flag', 'c++ -std=gnu++20 -Wdeprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-flag', '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        write_compile_commands(root / 'required-flag-substring', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated-extra -c source/common/common.cpp')
        expect_fail(run_checker(root / 'required-flag-substring', '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        write_compile_commands(root / 'forbidden', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -Wno-deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden', '--forbidden-flag-substring=-Wno-deprecated'), 'forbidden flag substring -Wno-deprecated')

        write_compile_commands(root / 'forbidden-volatile', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -Wno-volatile -c source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden-volatile', '--forbidden-flag-substring=-Wno-volatile'), 'forbidden flag substring -Wno-volatile')

        write_compile_commands(root / 'forbidden-blanket-warning-disable', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -w -c source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden-blanket-warning-disable', '--forbidden-flag=-w'), 'forbidden flag -w')

        write_compile_commands(root / 'forbidden-exact-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=12 -c source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden-exact-flag', '--forbidden-flag=-DX265_DEPTH=12'), 'forbidden flag -DX265_DEPTH=12')

        write_compile_commands(root / 'forbidden-exact-flag-no-prefix-match', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=12 -c source/common/common.cpp')
        expect_pass(run_checker(root / 'forbidden-exact-flag-no-prefix-match', '--forbidden-flag=-DX265_DEPTH=10'))

        write_compile_commands(root / 'missing-depth', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=10 -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-depth', '--required-depth-define=-DX265_DEPTH=12'), 'missing -DX265_DEPTH=12')

        write_compile_commands(root / 'mixed-depth', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -DX265_DEPTH=10 -c source/common/common.cpp')
        expect_fail(run_checker(root / 'mixed-depth', '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=10')

        mixed_depth_arguments_dir = root / 'mixed-depth-arguments'
        write_compile_commands_records(mixed_depth_arguments_dir, [{
            'directory': str(mixed_depth_arguments_dir),
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-DX265_DEPTH=12', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_depth_arguments_dir, '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=12')

        mixed_depth_fields_dir = root / 'mixed-depth-fields'
        write_compile_commands_records(mixed_depth_fields_dir, [{
            'directory': str(mixed_depth_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-DX265_DEPTH=10', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_depth_fields_dir, '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=10')

        write_compile_commands(root / 'missing-file', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/encoder/api.cpp', 'source/encoder/api.cpp')
        expect_fail(run_checker(root / 'missing-file', '--required-file-substring=source/common/'), 'missing compile command for file substring source/common/')

        write_compile_commands_entries(root / 'forbidden-file-substring', [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp', 'source/common/common.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/output/mkv.cpp', 'source/output/mkv.cpp'),
        ])
        expect_fail(run_checker(root / 'forbidden-file-substring', '--forbidden-file-substring=source/output/mkv.cpp'), 'forbidden compile command for file substring source/output/mkv.cpp')

        write_compile_commands(root / 'forbidden-windows-file-substring', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/output/mp4.cpp', 'source\\output\\mp4.cpp')
        expect_fail(run_checker(root / 'forbidden-windows-file-substring', '--forbidden-file-substring=source/output/mp4.cpp'), 'forbidden compile command for file substring source/output/mp4.cpp')

        write_compile_commands(root / 'file-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_pass(run_checker(root / 'file-flag', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', '--forbidden-file-flag=source/input/lavf.cpp=-DENABLE_MKV'))

        write_compile_commands(root / 'file-flag-no-prefix-match', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF_EXTRA -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_fail(run_checker(root / 'file-flag-no-prefix-match', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        file_flag_mixed_fields_dir = root / 'file-flag-mixed-fields'
        write_compile_commands_records(file_flag_mixed_fields_dir, [{
            'directory': str(file_flag_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/input/lavf.cpp'],
            'file': str(root / 'source/input/lavf.cpp'),
        }])
        expect_fail(run_checker(file_flag_mixed_fields_dir, '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        file_flag_command_missing_dir = root / 'file-flag-command-missing'
        write_compile_commands_records(file_flag_command_missing_dir, [{
            'directory': str(file_flag_command_missing_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/input/lavf.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DENABLE_LAVF', '-c', 'source/input/lavf.cpp'],
            'file': str(root / 'source/input/lavf.cpp'),
        }])
        expect_fail(run_checker(file_flag_command_missing_dir, '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        file_forbidden_mixed_fields_dir = root / 'file-forbidden-mixed-fields'
        write_compile_commands_records(file_forbidden_mixed_fields_dir, [{
            'directory': str(file_forbidden_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DENABLE_LAVF', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(file_forbidden_mixed_fields_dir, '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF'), 'forbidden flag -DENABLE_LAVF for file substring source/common/common.cpp')

        file_forbidden_command_only_dir = root / 'file-forbidden-command-only'
        write_compile_commands_records(file_forbidden_command_only_dir, [{
            'directory': str(file_forbidden_command_only_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(file_forbidden_command_only_dir, '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF'), 'forbidden flag -DENABLE_LAVF for file substring source/common/common.cpp')

        file_flag_response_dir = root / 'file-flag-response-file'
        file_flag_response_dir.mkdir()
        (file_flag_response_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF')
        write_compile_commands_records(file_flag_response_dir, [{
            'directory': str(file_flag_response_dir),
            'arguments': ['c++', '@args.rsp', '-c', 'source/input/lavf.cpp'],
            'file': str(root / 'source/input/lavf.cpp'),
        }])
        expect_pass(run_checker(file_flag_response_dir, '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'))

        file_flag_response_missing_dir = root / 'file-flag-response-file-missing'
        file_flag_response_missing_dir.mkdir()
        (file_flag_response_missing_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated')
        write_compile_commands_records(file_flag_response_missing_dir, [{
            'directory': str(file_flag_response_missing_dir),
            'arguments': ['c++', '@args.rsp', '-c', 'source/input/lavf.cpp'],
            'file': str(root / 'source/input/lavf.cpp'),
        }])
        expect_fail(run_checker(file_flag_response_missing_dir, '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        multi_match_file_flag_dir = root / 'multi-match-file-flag'
        write_compile_commands_entries(multi_match_file_flag_dir, [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp', 'source/input/lavf.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/input/yuv.cpp', 'source/input/yuv.cpp'),
        ])
        expect_fail(run_checker(multi_match_file_flag_dir, '--required-file-flag=source/input/=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/')

        multi_match_forbidden_file_flag_dir = root / 'multi-match-forbidden-file-flag'
        write_compile_commands_entries(multi_match_forbidden_file_flag_dir, [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/output/output.cpp', 'source/output/output.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_MKV -c source/output/mkv.cpp', 'source/output/mkv.cpp'),
        ])
        expect_fail(run_checker(multi_match_forbidden_file_flag_dir, '--forbidden-file-flag=source/output/=-DENABLE_MKV'), 'forbidden flag -DENABLE_MKV for file substring source/output/')

        write_compile_commands(root / 'missing-file-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_fail(run_checker(root / 'missing-file-flag', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        write_compile_commands(root / 'missing-file-flag-match', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp', 'source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-file-flag-match', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing compile command for file substring source/input/lavf.cpp required by file flag -DENABLE_LAVF')

        write_compile_commands(root / 'forbidden-file-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/common/common.cpp', 'source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden-file-flag', '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF'), 'forbidden flag -DENABLE_LAVF for file substring source/common/common.cpp')

        write_compile_commands_entries(root / 'mixed-c-cpp', [
            ('cc -std=c11 -c source/common/pixel.c', 'source/common/pixel.c'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp', 'source/common/common.cpp'),
        ])
        expect_pass(run_checker(root / 'mixed-c-cpp', '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8', '--min-cpp-commands=1'))

        cxx_language_dir = root / 'x-cxx-language'
        write_compile_commands_records(cxx_language_dir, [{
            'directory': str(cxx_language_dir),
            'command': 'cc -x c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/template.inc',
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_pass(run_checker(cxx_language_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        fused_cxx_language_dir = root / 'fused-x-cxx-language'
        write_compile_commands_records(fused_cxx_language_dir, [{
            'directory': str(fused_cxx_language_dir),
            'command': 'cc -xc++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/template.inc',
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_pass(run_checker(fused_cxx_language_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        cxx_header_language_dir = root / 'x-cxx-header-language'
        write_compile_commands_records(cxx_header_language_dir, [{
            'directory': str(cxx_header_language_dir),
            'command': 'cc -x c++-header -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/template.inc',
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_pass(run_checker(cxx_header_language_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        objective_cxx_language_dir = root / 'x-objective-cxx-language'
        write_compile_commands_records(objective_cxx_language_dir, [{
            'directory': str(objective_cxx_language_dir),
            'command': 'cc -x objective-c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/template.inc',
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_pass(run_checker(objective_cxx_language_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        cxx_language_arguments_dir = root / 'x-cxx-language-arguments'
        write_compile_commands_records(cxx_language_arguments_dir, [{
            'directory': str(cxx_language_arguments_dir),
            'arguments': ['cc', '-x', 'c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/template.inc'],
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_pass(run_checker(cxx_language_arguments_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        msvc_tp_language_dir = root / 'msvc-tp-cxx-language'
        write_compile_commands_records(msvc_tp_language_dir, [{
            'directory': str(msvc_tp_language_dir),
            'command': 'clang-cl /TP /std:c++20 /c source/common/template.inc',
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_pass(run_checker(msvc_tp_language_dir, '--min-cpp-commands=1'))

        msvc_fused_tp_language_dir = root / 'msvc-fused-tp-cxx-language'
        write_compile_commands_records(msvc_fused_tp_language_dir, [{
            'directory': str(msvc_fused_tp_language_dir),
            'command': 'clang-cl /Tpsource/common/template.inc /std:c++20 /c source/common/template.inc',
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_pass(run_checker(msvc_fused_tp_language_dir, '--min-cpp-commands=1'))

        msvc_tp_missing_std_dir = root / 'msvc-tp-cxx-language-missing-std'
        write_compile_commands_records(msvc_tp_missing_std_dir, [{
            'directory': str(msvc_tp_missing_std_dir),
            'arguments': ['clang-cl', '/TP', '/c', 'source/common/template.inc'],
            'file': str(root / 'source/common/template.inc'),
        }])
        expect_fail(run_checker(msvc_tp_missing_std_dir), 'missing GNU++20 dialect')

        write_compile_commands(root / 'only-c', 'cc -std=c11 -c source/common/pixel.c', 'source/common/pixel.c')
        expect_fail(run_checker(root / 'only-c'), 'no C++ compile commands')

        response_dir = root / 'response-file'
        response_dir.mkdir()
        (response_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands(response_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_pass(run_checker(response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        uppercase_response_dir = root / 'uppercase-response-file'
        uppercase_response_dir.mkdir()
        (uppercase_response_dir / 'ARGS.RSP').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands(uppercase_response_dir, 'c++ @ARGS.RSP -c source/common/common.cpp')
        expect_pass(run_checker(uppercase_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        response_split_std_dir = root / 'response-file-split-std'
        response_split_std_dir.mkdir()
        (response_split_std_dir / 'args.rsp').write_text('--std gnu++20 -Wdeprecated -Werror=deprecated')
        write_compile_commands(response_split_std_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_pass(run_checker(response_split_std_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        quoted_response_dir = root / 'quoted-response-file'
        quoted_response_dir.mkdir()
        (quoted_response_dir / 'args file.rsp').write_text('"-std=gnu++20" "-Wdeprecated" "-Werror=deprecated" "-DX265_DEPTH=8"')
        write_compile_commands(quoted_response_dir, 'c++ @"args file.rsp" -c "source/common/common.cpp"')
        expect_pass(run_checker(quoted_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        quoted_arguments_response_dir = root / 'quoted-response-file-arguments'
        quoted_arguments_response_dir.mkdir()
        (quoted_arguments_response_dir / 'args file.rsp').write_text('"-std=gnu++20" "-Wdeprecated" "-Werror=deprecated" "-DX265_DEPTH=8"')
        write_compile_commands_records(quoted_arguments_response_dir, [{
            'directory': str(quoted_arguments_response_dir),
            'arguments': ['c++', '@args file.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(quoted_arguments_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        windows_arguments_response_dir = root / 'windows-arguments-response-file'
        windows_arguments_response_dir.mkdir()
        (windows_arguments_response_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands_records(windows_arguments_response_dir, [{
            'directory': str(windows_arguments_response_dir),
            'arguments': ['c++', '@args.rsp', '-c', 'source\\common\\common.cpp'],
            'file': str(root / 'source\\common\\common.cpp'),
        }])
        expect_pass(run_checker(windows_arguments_response_dir, '--required-file-substring=source/common/common.cpp', '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        quoted_response_missing_flag_dir = root / 'quoted-response-file-arguments-missing-flag'
        quoted_response_missing_flag_dir.mkdir()
        (quoted_response_missing_flag_dir / 'args file.rsp').write_text('"-std=gnu++20" "-Wdeprecated" "-DX265_DEPTH=8"')
        write_compile_commands_records(quoted_response_missing_flag_dir, [{
            'directory': str(quoted_response_missing_flag_dir),
            'arguments': ['c++', '@args file.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(quoted_response_missing_flag_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        missing_response_dir = root / 'missing-response-file'
        missing_response_dir.mkdir()
        write_compile_commands(missing_response_dir, 'c++ @missing.rsp -c source/common/common.cpp')
        expect_fail(run_checker(missing_response_dir), 'missing response file')

        nested_missing_response_dir = root / 'nested-missing-response-file'
        nested_missing_response_dir.mkdir()
        (nested_missing_response_dir / 'args.rsp').write_text('-std=gnu++20 @missing-nested.rsp')
        write_compile_commands(nested_missing_response_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(nested_missing_response_dir), 'missing response file')

        missing_arguments_response_dir = root / 'missing-response-file-arguments'
        missing_arguments_response_dir.mkdir()
        write_compile_commands_records(missing_arguments_response_dir, [{
            'directory': str(missing_arguments_response_dir),
            'arguments': ['c++', '@missing.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_arguments_response_dir), 'missing response file')

        modmap_reference_dir = root / 'modmap-reference-not-response-file'
        modmap_reference_dir.mkdir()
        write_compile_commands(modmap_reference_dir, 'c++ -std=gnu++20 @encoderCMakeFilesencoder.diranalysis.cpp.obj.modmap -c source/encoder/analysis.cpp', 'source/encoder/analysis.cpp')
        expect_pass(run_checker(modmap_reference_dir, '--min-cpp-commands=1'))

        uppercase_suffix_dir = root / 'uppercase-cpp-suffix'
        write_compile_commands_records(uppercase_suffix_dir, [{
            'directory': str(uppercase_suffix_dir),
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/COMMON.CPP'],
            'file': str(root / 'source/common/COMMON.CPP'),
        }])
        expect_pass(run_checker(uppercase_suffix_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        nested_response_dir = root / 'nested-response-file'
        nested_response_dir.mkdir()
        (nested_response_dir / 'std.rsp').write_text('-std=gnu++20 -Wdeprecated')
        (nested_response_dir / 'args.rsp').write_text('@std.rsp -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands(nested_response_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_pass(run_checker(nested_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        nested_parent_response_dir = root / 'nested-parent-response-file'
        nested_parent_response_dir.mkdir()
        nested_parent_response_subdir = nested_parent_response_dir / 'sub'
        nested_parent_response_subdir.mkdir()
        (nested_parent_response_dir / 'std.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated')
        (nested_parent_response_subdir / 'args.rsp').write_text('@../std.rsp -DX265_DEPTH=8')
        write_compile_commands_records(nested_parent_response_dir, [{
            'directory': str(nested_parent_response_subdir),
            'command': 'c++ @args.rsp -c source/common/common.cpp',
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(nested_parent_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        nested_parent_response_missing_dir = root / 'nested-parent-response-file-missing-flag'
        nested_parent_response_missing_dir.mkdir()
        nested_parent_response_missing_subdir = nested_parent_response_missing_dir / 'sub'
        nested_parent_response_missing_subdir.mkdir()
        (nested_parent_response_missing_dir / 'std.rsp').write_text('-std=gnu++20 -Wdeprecated')
        (nested_parent_response_missing_subdir / 'args.rsp').write_text('@../std.rsp -DX265_DEPTH=8')
        write_compile_commands_records(nested_parent_response_missing_dir, [{
            'directory': str(nested_parent_response_missing_subdir),
            'command': 'c++ @args.rsp -c source/common/common.cpp',
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(nested_parent_response_missing_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        nested_arguments_dir = root / 'nested-response-file-arguments'
        nested_arguments_dir.mkdir()
        (nested_arguments_dir / 'std.rsp').write_text('-std=gnu++20 -Wdeprecated')
        (nested_arguments_dir / 'args.rsp').write_text('@std.rsp -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands_records(nested_arguments_dir, [{
            'directory': str(nested_arguments_dir),
            'arguments': ['c++', '@args.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(nested_arguments_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        response_mixed_fields_dir = root / 'response-file-mixed-fields'
        response_mixed_fields_dir.mkdir()
        (response_mixed_fields_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands_records(response_mixed_fields_dir, [{
            'directory': str(response_mixed_fields_dir),
            'command': 'c++ @args.rsp -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(response_mixed_fields_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'), 'missing required flag -Werror=deprecated')

        response_dual_field_equivalent_std_dir = root / 'response-dual-field-equivalent-std'
        response_dual_field_equivalent_std_dir.mkdir()
        (response_dual_field_equivalent_std_dir / 'std.rsp').write_text('--std=gnu++20 -Wdeprecated -Werror=deprecated')
        write_compile_commands_records(response_dual_field_equivalent_std_dir, [{
            'directory': str(response_dual_field_equivalent_std_dir),
            'command': 'c++ @std.rsp -c source/common/common.cpp',
            'arguments': ['c++', '-std', 'gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(response_dual_field_equivalent_std_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        response_dual_field_std_mismatch_dir = root / 'response-dual-field-std-mismatch'
        response_dual_field_std_mismatch_dir.mkdir()
        (response_dual_field_std_mismatch_dir / 'std.rsp').write_text('--std=gnu++20 -Wdeprecated -Werror=deprecated')
        write_compile_commands_records(response_dual_field_std_mismatch_dir, [{
            'directory': str(response_dual_field_std_mismatch_dir),
            'command': 'c++ @std.rsp -c source/common/common.cpp',
            'arguments': ['c++', '-std=c++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(response_dual_field_std_mismatch_dir), 'duplicate standard flags -std=c++20,--std=gnu++20')

        response_duplicate_std_dir = root / 'response-file-duplicate-std'
        response_duplicate_std_dir.mkdir()
        (response_duplicate_std_dir / 'args.rsp').write_text('-std=gnu++20 -std=gnu++20 -Wdeprecated -Werror=deprecated')
        write_compile_commands(response_duplicate_std_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(response_duplicate_std_dir), 'duplicate standard flags -std=gnu++20,-std=gnu++20')

        response_command_missing_std_dir = root / 'response-command-missing-std-dual-field'
        response_command_missing_std_dir.mkdir()
        (response_command_missing_std_dir / 'args.rsp').write_text('-Wdeprecated -Werror=deprecated')
        write_compile_commands_records(response_command_missing_std_dir, [{
            'directory': str(response_command_missing_std_dir),
            'command': 'c++ @args.rsp -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(response_command_missing_std_dir), 'missing GNU++20 dialect')

        response_missing_flag_dir = root / 'response-file-missing-required-flag'
        response_missing_flag_dir.mkdir()
        (response_missing_flag_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated')
        write_compile_commands(response_missing_flag_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(response_missing_flag_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        response_forbidden_file_flag_dir = root / 'response-file-forbidden-file-flag'
        response_forbidden_file_flag_dir.mkdir()
        (response_forbidden_file_flag_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF')
        write_compile_commands(response_forbidden_file_flag_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(response_forbidden_file_flag_dir, '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF'), 'forbidden flag -DENABLE_LAVF for file substring source/common/common.cpp')

        response_mixed_depth_dir = root / 'response-file-mixed-depth'
        response_mixed_depth_dir.mkdir()
        (response_mixed_depth_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -DX265_DEPTH=10')
        write_compile_commands(response_mixed_depth_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(response_mixed_depth_dir, '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=10')

        response_cycle_dir = root / 'response-file-cycle'
        response_cycle_dir.mkdir()
        (response_cycle_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated @args.rsp')
        write_compile_commands(response_cycle_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_pass(run_checker(response_cycle_dir, '--required-flag=-Werror=deprecated'))

        two_file_response_cycle_dir = root / 'two-file-response-cycle'
        two_file_response_cycle_dir.mkdir()
        (two_file_response_cycle_dir / 'a.rsp').write_text('-std=gnu++20 -Wdeprecated @b.rsp')
        (two_file_response_cycle_dir / 'b.rsp').write_text('-Werror=deprecated @a.rsp')
        write_compile_commands(two_file_response_cycle_dir, 'c++ @a.rsp -c source/common/common.cpp')
        expect_pass(run_checker(two_file_response_cycle_dir, '--required-flag=-Werror=deprecated'))

        write_compile_commands_entries(root / 'depth-exclude', [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/dynamicHDR10/json11.cpp', 'source/dynamicHDR10/json11.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp', 'source/common/common.cpp'),
        ])
        expect_pass(run_checker(root / 'depth-exclude', '--required-depth-define=-DX265_DEPTH=8', '--depth-exclude-path=dynamicHDR10/'))

        write_compile_commands_entries(root / 'windows-depth-exclude', [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/dynamicHDR10/json11.cpp', 'source\\dynamicHDR10\\json11.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp', 'source/common/common.cpp'),
        ])
        expect_pass(run_checker(root / 'windows-depth-exclude', '--required-depth-define=-DX265_DEPTH=8', '--depth-exclude-path=source/dynamicHDR10/'))

        windows_depth_exclude_backslash_arg_dir = root / 'windows-depth-exclude-backslash-arg'
        write_compile_commands_entries(windows_depth_exclude_backslash_arg_dir, [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/dynamicHDR10/json11.cpp', 'source/dynamicHDR10/json11.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp', 'source/common/common.cpp'),
        ])
        expect_pass(run_checker(windows_depth_exclude_backslash_arg_dir, '--required-depth-define=-DX265_DEPTH=8', '--depth-exclude-path=source\\dynamicHDR10\\'))

        duplicate_source_dir = root / 'duplicate-source-min-cpp-commands'
        write_compile_commands_entries(duplicate_source_dir, [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp', 'source/common/common.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DSECOND_PASS=1 -c source/common/common.cpp', 'source/common/common.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/encoder/encoder.cpp', 'source/encoder/encoder.cpp'),
        ])
        expect_pass(run_checker(duplicate_source_dir, '--min-cpp-commands=2'))
        expect_fail(run_checker(duplicate_source_dir, '--min-cpp-commands=3'), 'expected at least 3 unique C++ compile commands')

        expect_fail(run_checker(root / 'pass', '--min-cpp-commands=2'), 'expected at least 2 unique C++ compile commands')

    print('compile command guardrails validated')


if __name__ == '__main__':
    main()
