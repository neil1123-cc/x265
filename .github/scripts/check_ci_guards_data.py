#!/usr/bin/env python3
from pathlib import Path

WORKFLOW_DIR = Path('.github/workflows')
ACTION_DIR = Path('.github/actions')
SCAN_HELPER = Path('.github/scripts/cxx20_scan_helpers.sh')
MP4_SMOKE_HELPER = Path('.github/scripts/mp4_smoke_helpers.sh')
PROFILING_SMOKE_HELPER = Path('.github/scripts/profiling_smoke_package_verify.sh')
VERIFY_CI_ARCHIVE_HELPER = Path('.github/scripts/verify_ci_archive.sh')
RUNTIME_SMOKE_SUITE = Path('.github/scripts/runtime_smoke_suite.sh')
MP4_SMOKE_SUITE = Path('.github/scripts/mp4_smoke_suite.sh')
SOURCE_TEST_VECTOR_CHECK = Path('.github/scripts/check_source_test_vectors.py')
SOURCE_TEST_VECTOR_TEST = Path('.github/scripts/test_check_source_test_vectors.py')
DEPENDENCY_SUFFIX_CHECK = Path('.github/scripts/check_dependency_patch_suffixes.py')
WINDOWS_DEPS_ACTION = Path('.github/actions/setup-windows-deps/action.yml')
UPDATE_DEPS_WORKFLOW = Path('.github/workflows/update-deps.yml')
BUILD_WORKFLOW = Path('.github/workflows/build.yml')
BUILD_PROFILING_WORKFLOW = Path('.github/workflows/build-profiling.yml')
BUILD_PGO_WORKFLOW = Path('.github/workflows/build-pgo.yml')
BUILD_PROFILING_ACTION = Path('.github/actions/build-x265-profiling/action.yml')

UPDATE_DEPS_ANCHORS = (
    'ffmpeg-ref',
    'mimalloc-ref',
    'obuparse-ref',
    'lsmash-ref',
    'lsmash-cache-suffix',
    'gop-muxer-ref',
    'gop-muxer-cache-suffix',
)
REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS = (
    'CXX20_CHECK_SCRIPT="${{ github.action_path }}/../../scripts/check_compile_commands.py"',
    '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
    'check_cxx20_commands_profiling build/8b',
    'check_cxx20_commands_profiling build/12b',
    'check_cxx20_commands_profiling .',
    'enable-lsmash',
    "if [ \"${{ inputs.enable-lsmash }}\" = 'true' ] || [ \"${{ inputs.enable-lsmash }}\" = 'ON' ]; then",
    'lsmash_args=(-DENABLE_LSMASH=ON)',
)
REQUIRED_UPDATE_DEPS_SNIPPETS = (
    'python .github/scripts/check_ci_guards.py',
    'python .github/scripts/test_check_ci_guards.py',
    'python .github/scripts/check_dependency_patch_suffixes.py',
    'for anchor in ffmpeg-ref mimalloc-ref obuparse-ref lsmash-ref lsmash-cache-suffix gop-muxer-ref gop-muxer-cache-suffix; do',
    'lsmash_suffix=$(sed -n',
    'gop_muxer_suffix=$(sed -n',
    'Current L-SMASH cache suffix: ${lsmash_suffix}',
    'Current GOP muxer cache suffix: ${gop_muxer_suffix}',
    'Unexpected dependency update diff paths:',
)
REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS = (
    'case "${MSYSTEM:-}" in',
    'CLANG64) ;;',
    '/clang64/bin/*|/usr/bin/*) ;;',
    'lsmash=${{ inputs.lsmash-repository }}@${{ inputs.lsmash-ref }} suffix=${{ inputs.lsmash-cache-suffix }} patch=${{ inputs.lsmash-patch-path }}',
    'gop_muxer=${{ inputs.gop-muxer-repository }}@${{ inputs.gop-muxer-ref }} suffix=${{ inputs.gop-muxer-cache-suffix }} patch=${{ inputs.gop-muxer-patch-path }}',
    'git -c core.autocrlf=false reset --hard HEAD',
    'git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}',
    "grep -Fq \"LSMASH_4CC( 'h', 'v', 'c', 'C' )\" codecs/hevc.c",
    "grep -Fq 'lsmash_isom_box_type_value' core/box.c",
    'git -c core.autocrlf=false reset --hard HEAD',
    'git apply ${{ inputs.gop-muxer-patch-path }}',
    'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o',
)
TME_SMOKE_FLAGS = (
    '--threaded-me',
    '--no-wpp',
    '--no-progress',
)
TME_SMOKE_OPTIONS = (
    ('--input', 'smoke_threaded_me.y4m'),
    ('--input-res', '160x90'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--preset', 'medium'),
    ('--pools', '32'),
    ('--frame-threads', '1'),
    ('--output', 'smoke_threaded_me.hevc'),
)
TME_GENERATOR_OPTIONS = (
    ('-i', 'testsrc2=size=160x90:rate=24'),
    ('-frames:v', '16'),
    ('-pix_fmt', 'yuv420p'),
)
TME_STRESS_FLAGS = (
    '--threaded-me',
    '--no-wpp',
    '--no-progress',
)
TME_STRESS_OPTIONS = (
    ('--input', 'smoke_threaded_me_stress.y4m'),
    ('--input-res', '160x90'),
    ('--fps', '24'),
    ('--frames', '2'),
    ('--preset', 'medium'),
    ('--pools', '32'),
    ('--frame-threads', '1'),
)
TME_STRESS_GENERATOR_OPTIONS = (
    ('-i', 'testsrc2=size=160x90:rate=24'),
    ('-frames:v', '2'),
    ('-pix_fmt', 'yuv420p'),
)
MKV_SMOKE_OPTIONS = (
    ('--input', 'smoke_mkv.y4m'),
    ('--input-res', '160x90'),
    ('--fps', '24'),
    ('--frames', '12'),
    ('--output', 'smoke_mkv.mkv'),
)
MKV_GENERATOR_OPTIONS = (
    ('-i', 'testsrc2=size=160x90:rate=24'),
    ('-frames:v', '12'),
    ('-pix_fmt', 'yuv420p'),
)
LAVF_SMOKE_OPTIONS = (
    ('--input', 'smoke_lavf_input.mkv'),
    ('--frames', '12'),
    ('--output', 'smoke_lavf_output.hevc'),
)
LAVF_GENERATOR_OPTIONS = (
    ('-f', 'lavfi'),
    ('-i', 'testsrc2=size=160x90:rate=24'),
    ('-frames:v', '12'),
    ('-pix_fmt', 'yuv420p'),
    ('-c:v', 'ffv1'),
)
GOP_SMOKE_FLAGS = (
    '--no-open-gop',
)
GOP_SMOKE_OPTIONS = (
    ('--input', 'smoke_gop.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '0'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_gop.gop'),
)
GOP_GENERATOR_OPTIONS = (
    ('-f', 'lavfi'),
    ('-i', 'testsrc2=size=128x72:rate=24'),
    ('-frames:v', '16'),
    ('-pix_fmt', 'yuv420p'),
)
MP4_SMOKE_FLAGS = (
    '--no-open-gop',
)
MP4_SMOKE_OPTIONS = (
    ('--input', 'smoke.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke.mp4'),
)
MP4_OPEN_GOP_SMOKE_FLAGS = (
    '--open-gop',
)
MP4_OPEN_GOP_SMOKE_OPTIONS = (
    ('--input', 'smoke_open.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_open.mp4'),
)
MP4_CRA_SMOKE_FLAGS = (
    '--cra-nal',
)
MP4_CRA_SMOKE_OPTIONS = (
    ('--input', 'smoke_cra.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '0'),
    ('--keyint', '1'),
    ('--min-keyint', '1'),
    ('--output', 'smoke_cra.mp4'),
)
MP4_SINGLE_FRAME_SMOKE_OPTIONS = (
    ('--input', 'smoke_single.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '1'),
    ('--bframes', '0'),
    ('--keyint', '1'),
    ('--min-keyint', '1'),
    ('--output', 'smoke_single.mp4'),
)
MP4_ZERO_FRAMES_SMOKE_OPTIONS = (
    ('--input', 'smoke_zero.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '0'),
    ('--bframes', '0'),
    ('--keyint', '1'),
    ('--min-keyint', '1'),
    ('--output', 'smoke_zero.mp4'),
)
MP4_VUI_SMOKE_OPTIONS = (
    ('--input', 'smoke_vui.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '4'),
    ('--bframes', '0'),
    ('--keyint', '4'),
    ('--min-keyint', '4'),
    ('--sar', '4:3'),
    ('--range', 'limited'),
    ('--colorprim', 'bt709'),
    ('--transfer', 'bt709'),
    ('--colormatrix', 'bt709'),
    ('--output', 'smoke_vui.mp4'),
)
MP4_FRAC_SMOKE_FLAGS = (
    '--no-open-gop',
)
MP4_FRAC_SMOKE_OPTIONS = (
    ('--input', 'smoke_frac.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24000/1001'),
    ('--frames', '24'),
    ('--bframes', '4'),
    ('--keyint', '12'),
    ('--min-keyint', '12'),
    ('--output', 'smoke_frac.mp4'),
)
MP4_BPYRAMID_SMOKE_FLAGS = (
    '--b-pyramid',
    '--no-open-gop',
)
MP4_BPYRAMID_SMOKE_OPTIONS = (
    ('--input', 'smoke_bpyramid.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_bpyramid.mp4'),
)
MP4_AUD_SMOKE_FLAGS = (
    '--aud',
)
MP4_AUD_SMOKE_OPTIONS = (
    ('--input', 'smoke_aud.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_aud.mp4'),
)
MP4_EOS_SMOKE_FLAGS = (
    '--eos',
    '--eob',
)
MP4_EOS_SMOKE_OPTIONS = (
    ('--input', 'smoke_eos.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_eos.mp4'),
)
MP4_RECOVERY_SMOKE_FLAGS = (
    '--no-open-gop',
    '--idr-recovery-sei',
)
MP4_RECOVERY_SMOKE_OPTIONS = (
    ('--input', 'smoke_recovery.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '0'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_recovery.mp4'),
)
ZIMG_SMOKE_OPTIONS = (
    ('--input', 'build/cxx20-warning-scan/smoke_zimg.yuv'),
    ('--input-res', '96x96'),
    ('--fps', '1'),
    ('--frames', '1'),
    ('--vf', 'zimg:lanczos(64,64)'),
    ('--output', 'build/cxx20-warning-scan/smoke_zimg.hevc'),
)
LINUX_GCC_SMOKE_OPTIONS = (
    ('--input', 'build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv'),
    ('--input-res', '64x64'),
    ('--fps', '1'),
    ('--frames', '1'),
    ('--output', 'build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc'),
)
WARNING_SCAN_SMOKES = (
    (
        '12-bit warning-scan smoke',
        'build/cxx20-warning-scan-12bit/x265.exe',
        (
            ('--input', 'build/cxx20-warning-scan-12bit/smoke_12bit.yuv'),
            ('--input-res', '64x64'),
            ('--input-depth', '12'),
            ('--output-depth', '12'),
            ('--fps', '1'),
            ('--frames', '1'),
            ('--output', 'build/cxx20-warning-scan-12bit/smoke_12bit.hevc'),
        ),
        'test -s build/cxx20-warning-scan-12bit/smoke_12bit.hevc',
    ),
    (
        'shared-library warning-scan smoke',
        'build/cxx20-warning-scan-shared-library/x265.exe',
        (
            ('--input', 'build/cxx20-warning-scan-shared-library/smoke_shared.yuv'),
            ('--input-res', '64x64'),
            ('--fps', '1'),
            ('--frames', '1'),
            ('--output', 'build/cxx20-warning-scan-shared-library/smoke_shared.hevc'),
        ),
        'test -s build/cxx20-warning-scan-shared-library/smoke_shared.hevc',
    ),
    (
        'all-bit-depth warning-scan smoke',
        'build/cxx20-warning-scan-all/x265.exe',
        (
            ('--input', 'build/cxx20-warning-scan-all/smoke_all.yuv'),
            ('--input-res', '64x64'),
            ('--input-depth', '10'),
            ('--output-depth', '10'),
            ('--fps', '1'),
            ('--frames', '1'),
            ('--output', 'build/cxx20-warning-scan-all/smoke_all.hevc'),
        ),
        'test -s build/cxx20-warning-scan-all/smoke_all.hevc',
    ),
)
PR_TRIGGER_PATHS = (
    '.github/workflows/**',
    '.github/actions/**',
    '.github/patches/**',
    '.github/scripts/**',
    'source/**',
    'x265Version.txt',
)
PR_SKIPPED_BUILD_JOBS = (
    'cxx20-warning-scan',
    'cxx20-gcc-compile-commands',
    'cxx20-linux-gcc-compile-commands',
    'build',
)


def build_step_requirements():
    return (
        ('validate-deps-cache-suffix', 'Run Python CI guard bundle', (
            'python .github/scripts/check_ci_guards.py',
            'python .github/scripts/test_check_ci_guards.py',
            'python .github/scripts/check_cmake_cxx20_contract.py source',
            'python .github/scripts/test_check_cmake_cxx20_contract.py',
            'python .github/scripts/test_check_compile_commands.py',
            'python .github/scripts/check_source_test_vectors.py source/test',
            'python .github/scripts/test_check_source_test_vectors.py',
            'python .github/scripts/test_check_dependency_patch_suffixes.py',
            'python .github/scripts/check_release_needs.py',
            'python .github/scripts/test_check_pgo_consume_chain.py',
        )),
        ('validate-deps-cache-suffix', 'Check dependency patch cache suffixes', (
            'python .github/scripts/check_dependency_patch_suffixes.py',
            'python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after"',
        )),
        ('build', 'Get Latest Tag', (
            'No numeric version tag found; using $version as CI fallback',
        )),
        ('build', 'Compile X265', (
            'check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"',
            'check_pgo_consume_commands build/8b-lib "$PGO_8B_LIB_FLAG" 50',
            'check_pgo_consume_commands build/12b-lib "$PGO_12B_LIB_FLAG" 50',
            'check_pgo_consume_commands build/all-8b-lib "$PGO_ALL_FLAG" 50',
            'check_pgo_consume_commands build/all-12b-lib "$PGO_ALL_FLAG" 50',
            'check_pgo_consume_commands build/all "$PGO_ALL_FLAG" 60',
        )),
        ('build', 'Runtime Smokes (All CLI)', (
            'bash x265/.github/scripts/runtime_smoke_suite.sh all',
        )),
        ('build', 'MP4 Smokes (All CLI)', (
            'bash x265/.github/scripts/mp4_smoke_suite.sh all',
        )),
        ('build', 'Verify Package Artifact', (
            'expected_count=4',
            'bash x265/.github/scripts/verify_ci_archive.sh x265-release "x265-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z" artifact-check "${{ matrix.target_cpu }}" "$expected_count"',
        )),
        ('cxx20-linux-gcc-compile-commands', 'Run Linux GCC C++20 compile command diagnostics', (
            'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands',
        )),
        ('cxx20-warning-scan', 'Run C++20 CLI and dependency warning scans', (
            '-DENABLE_ZIMG=ON',
        )),
        ('cxx20-warning-scan', 'Run C++20 shared and all-bit-depth warning scans', (
            'check_cxx20_commands_clang build/cxx20-warning-scan-shared-library',
        )),
        ('cxx20-gcc-compile-commands', 'Run GCC C++20 compile command diagnostics', (
            'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands',
        )),
    )


def profiling_step_requirements():
    return (
        ('validate-guardrails', 'Check CI guardrails', (
            'python .github/scripts/check_ci_guards.py',
            'python .github/scripts/test_check_ci_guards.py',
        )),
        ('build', 'Get Latest Tag', (
            'if [[ "${GITHUB_REF:-}" == refs/tags/[0-9].[0-9]* ]]; then',
            'version="0.0"',
        )),
        ('build', 'Get CI Version', (
            'head_hash=$(git rev-parse --short HEAD)',
            'version="${{ steps.tag.outputs.version }}-g${head_hash}"',
        )),
        ('build', 'Package LLVM Profdata Tool', (
            'cp "$llvm_profdata" profdata-dist/',
            'strip -s profdata-dist/llvm-profdata.exe',
        )),
        ('build', 'Smoke, Package, and Verify 8b-lib', (
            'TARGET_CPU="${{ matrix.target_cpu }}" bash x265/.github/scripts/profiling_smoke_package_verify.sh 8b-lib',
        )),
        ('build', 'Smoke, Package, and Verify 12b-lib', (
            'TARGET_CPU="${{ matrix.target_cpu }}" bash x265/.github/scripts/profiling_smoke_package_verify.sh 12b-lib',
        )),
        ('build', 'Smoke, Package, and Verify All', (
            'TARGET_CPU="${{ matrix.target_cpu }}" bash x265/.github/scripts/profiling_smoke_package_verify.sh all',
        )),
        ('build', 'Compress Profiling Build', (
            '7za a -t7z -mx=9 ../x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe',
        )),
        ('build', 'Compress LLVM Profdata', (
            '7za a -t7z -mx=9 ../llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z ./*',
        )),
        ('build', 'Verify Profiling Artifact', (
            'bash x265/.github/scripts/verify_ci_archive.sh x265-profiling "x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z" artifact-check-profiling "${{ matrix.target_cpu }}"',
        )),
        ('build', 'Verify LLVM Profdata Artifact', (
            'bash x265/.github/scripts/verify_ci_archive.sh llvm-profdata "llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z" artifact-check-profdata',
        )),
    )


def pgo_step_requirements():
    return (
        ('validate-guardrails', 'Check CI guardrails', (
            'python .github/scripts/check_ci_guards.py',
            'python .github/scripts/test_check_ci_guards.py',
        )),
        ('generate', 'Run PGO Profiling Workload', (
            'check_cxx20_commands_profiling "$profile_build_dir"',
            'llvm-profdata merge -output=../x265.profdata "${profraw_files[@]}"',
            'llvm-profdata show --summary ../x265.profdata || llvm-profdata show --detailed-summary ../x265.profdata',
        )),
        ('generate', 'Push Baseline Profdata to Branch', (
            'profile_target="${{ github.event.inputs.profile_target || \'all\' }}"',
            'copy_if_exists "profiles/0.profdata" "$profiles_dir/1.profdata"',
            'python x265/.github/scripts/check_profdata_metadata.py "$profdata_push_dir/metadata.json"',
            'git -C "$profdata_push_dir" push origin HEAD:"$profdata_branch"',
        )),
    )
