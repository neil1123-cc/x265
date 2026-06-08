#!/usr/bin/env python3
import io
import os
import shlex
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import check_ci_guards as checker_module
import check_ci_guards_helpers as helper_module
import check_cli_nullptr_usage as cli_nullptr_checker
from check_ci_guards_data import build_step_requirements, build_workflow_step_requirements, pgo_step_requirements, profiling_step_requirements
from test_check_ci_guards_fixture import case, replace_text as fixture_replace_text, write_repo

BASELINE_CHECKS = (
    'yaml-text',
    'yaml-parse',
    'run-blocks',
    'scan-helper',
    'ensure-cmake4-helper',
    'ensure-linux-sanitizer-toolchain-helper',
    'mp4-smoke-helper',
    'runtime-smoke-suite',
    'mp4-smoke-suite',
    'required-snippets',
    'pgo-consume-helper',
    'raw-smoke',
    'mp4-smokes',
    'zimg-smoke',
    'warning-scan-runtime-smokes',
)
TARGETED_CHECKS = (
    'scan-helper',
    'required-snippets',
    'gnu20-diagnostic-steps',
    'warning-scan-dependencies',
    'windows-deps-checkout-scope',
    'windows-gcc-diagnostics-setup',
    'linux-gcc-smoke',
    'linux-cmake-setup',
    'linux-sanitizer-toolchain-setup',
    'build-pr-fast-gate',
    'dependency-update-anchors',
    'job-timeouts',
    'update-deps-concurrency',
    'build-workflow-concurrency',
    'build-matrix-scope',
    'checkout-scope',
    'metadata-history-scope',
    'pgo-fetch-scope',
    'windows-dependency-smoke-scope',
    'build-log-scope',
    'build-compile-scope',
    'package-scope',
    'warning-scan-full-gate',
    'pgo-consume-helper',
    'profiling-smoke-helper',
    'verify-ci-archive-helper',
    'ci-7z-helper',
    'profdata-metadata',
    'source-test-vector-scripts',
    'threaded-me-smoke',
    'threaded-me-stress-smoke',
    'cli-long-input-smoke',
    'mkv-smoke',
    'lavf-smoke',
    'qpfile-smoke',
    'nalu-file-smoke',
    'output-depth-invalid-smoke',
    'chunk-negative-smoke',
    'qpfile-oversized-smoke',
    'zonefile-smoke',
    'zonefile-oversized-smoke',
    'recon-smoke',
    'analysis-save-load-smoke',
    '2pass-stats-smoke',
    'abr-ladder-smoke',
    'video-signal-type-preset-oversized-smoke',
    'gop-output-smoke',
    'cli-nullptr-usage',
    'cli-volatile-usage',
    'json11-noexcept-usage',
    'json11-number-boundary-safety',
    'json11-unicode-escape-parse-safety',
    'json11-short-int-parse-safety',
    'json11-slow-float-token-bounds',
    'source-null-exception-usage',
    'remaining-null-boundaries',
    'fps-parse-safety',
    'frame-threads-parse-safety',
    'total-frames-parse-safety',
    'level-idc-parse-safety',
    'log-level-parse-safety',
    'qpstep-parse-safety',
    'qscale-mode-parse-safety',
    'subme-parse-safety',
    'cli-input-open-cleanup',
    'cli-input-validation-cleanup',
    'cli-output-open-cleanup',
    'cli-profile-apply-cleanup',
    'cli-deprecated-parallel-log-args',
    'scenecut-trailing-arg-diagnostics',
    'cli-recon-basename-cleanup',
    'cli-vmaf-input-open-cleanup',
    'cli-vmaf-recon-preconditions-cleanup',
    'cli-recon-open-guard',
    'svt-app-context-staging',
    'svt-param-storage-replace-safety',
    'svt-nal-buffer-replace-safety',
    'nal-takecontents-realloc-safety',
    'svt-rpu-payload-replace-safety',
    'configure-zone-svt-staging',
    'svt-pools-parse-safety',
    'svt-deblock-parse-usage',
    'svt-frame-threads-parse-safety',
    'dependency-suffixes',
    'release-needs',
    'compile-commands',
    'gnu20-legacy-guard-bundle',
    'pgo-consume-chain',
    'source-test-vectors',
    'source-legacy-patterns',
    'all-source-legacy-patterns',
    'csvlog-reopen-state',
    'csvlog-open-state',
    'reconplay-start-failure-guard',
    'threadpool-create-rollback',
    'threadpool-start-rollback',
    'frameencoder-start-failure-guard',
    'threadedme-start-failure-guard',
    'input-reader-start-failure-guard',
    'encoder-threadpool-start-failure-guard',
    'encoder-open-fail-cleanup',
    'lookahead-alloc-guards',
    'frameencoder-init-alloc-guards',
    'bitcost-alloc-guards',
    'scaler-chroma-dims-guard',
    'tonemap-payload-safety',
    'temporalfilter-alloc-counts',
    'frameencoder-substream-alloc-guards',
    'frameencoder-initialize-geoms-staging',
    'frame-create-subsample-staging',
    'frame-create-rowstate-alloc-guards',
    'frame-create-mcstf-refpic-guards',
    'frame-create-mcstf-fenc-pic-guards',
    'frame-create-top-alloc-guards',
    'frame-alloc-encode-data-guards',
    'x265-picture-init-null-guard',
    'x265-param-default-null-guard',
    'x265-param-default-preset-null-guard',
    'x265-param-parse-null-guard',
    'x265-param-apply-profile-null-guard',
    'param-api-null-guards',
    'zone-scenecut-param-parse-null-guards',
    'analysis-data-api-null-guards',
    'query-api-output-null-guards',
    'x265-dither-image-null-guards',
    'csvlog-api-null-guards',
    'vmaf-api-null-guards',
    'threadedme-create-guards',
    'threadpool-windows-numa-affinity-guard',
    'encoder-ctu-info-guards',
    'encoder-open-alloc-guard',
    'encoder-create-object-alloc-guards',
    'encoder-create-core-alloc-guards',
    'encoder-encode-frame-alloc-guards',
    'encoder-encode-setup-rollback',
    'lowres-aqlayer-alloc-guards',
    'lowres-histogram-alloc-guards',
    'frame-edge-aq-alloc-guards',
    'cutree-sharedmem-alloc-guards',
    'scaler-helper-alloc-guards',
    'lookahead-create-rollback',
    'lookahead-tld-yuv-guards',
    'sea-integral-buffer-lifecycle',
    'vmaf-temp-buffer-cleanup',
    'encoder-rps-list-alloc-guard',
    'encoder-headers-arg-guard',
    'wavefront-init-rollback',
    'framedata-create-rollback',
    'scaler-init-rollback',
    'reconfig-save-zone-rollback',
    'cli-config-file-parse-usage',
    'lambda-file-parse-usage',
    'lambda-file-error-state',
    'param-checked-parse-usage',
    'scenecut-qp-macro-cleanup',
    'zone-param-macro-cleanup',
    'param-parse-macro-cleanup',
    'qpfile-parse-usage',
    'qpfile-error-state',
    'strict-scan-parsing-usage',
    'zonefile-parse-usage',
    'external-input-atoi-usage',
    'lavf-framecount-parse-safety',
    'dolby-vision-rpu-parse-usage',
    'cmake-cxx20-contract',
    'nalu-file-parse-usage',
    'nalu-file-error-state',
    'analysis-reuse-refine-parse-safety',
    'analysis-output-fail-state',
    'scalinglist-parse-usage',
    'checked-parse-helper-safety',
    'param-uint-token-safety',
    'mkv-header-cleanup-state',
    'vmaf-file-cleanup-state',
    'vmaf-data-cleanup-state',
    'vmaf-frame-read-state',
    'vmaf-picture-read-failure',
    'vmaf-score-failure-propagation',
    'param-double-token-safety',
    'param-pair-parse-safety',
    'parse-name-assignment-safety',
    'ratecontrol-first-pass-parse-usage',
    'preset-index-parse-usage',
    'cpu-list-parse-usage',
    'interlace-parse-safety',
    'rdoq-level-parse-safety',
    'ratecontrol-numeric-helper-safety',
    'ratecontrol-stats-parse-usage',
    'ratecontrol-stats-line-parse-usage',
    'ratecontrol-stats-prefix-parse-usage',
    'param-bool-numeric-int-safety',
    'bitrate-mode-parse-safety',
    'qp-mode-parse-safety',
    'strict-cbr-parse-safety',
    'sao-create-rollback',
    'svt-bitrate-mode-parse-safety',
    'api-zone-open-staging',
    'copy-params-zone-replace-safety',
    'encoder-parameters-output-safety',
    'encoder-get-stats-size-guard',
    'cli-output-failure-full-cleanup',
    'lavf-openfile-cleanup',
    'svt-qp-mode-parse-safety',
    'reader-thread-alloc-guards',
    'scaler-thread-alloc-guards',
    'hdr10-json-metadata-ownership',
    'temporalfilter-refpic-rollback',
    'temporalfilter-refpic-state-init',
    'temporalfilter-metld-yuv-guards',
    'param-string-replace-safety',
    'zones-parse-safety',
    'raw-output-fail-state',
    'csvlog-fail-state',
    'cli-progress-file-state',
    'raw-output-write-guard',
    'raw-stdout-flush-state',
    'mkv-output-fail-state',
    'mkv-close-fail-state',
    'recon-output-write-guard',
    'recon-output-stream-state',
    'input-framecount-seek-guard',
    'y4m-recon-seek-guard',
    'recon-finalize-state',
    'gop-options-fail-state',
    'gop-output-fail-state',
    'gop-smart-fwrite-retry-guard',
    'y4m-yuv-row-buffer-alloc-guard',
    'output-open-alloc-guards',
    'vmaf-recon-state-safety',
    'reconplay-pipe-fail-state',
    'lambda-file-failfast',
    'lavf-buffer-replace-safety',
    'svt-pools-parse-usage',
    'threadpool-cpu-frequency-parse-usage',
    'threadpool-cpu-frequency-tail-guard',
    'gop-close-fail-state',
    'param-bool-numeric-double-safety',
    'csv-log-level-parse-safety',
    'bool-int-parse-safety',
    'aq-mode-parse-safety',
    'multiview-scc-parse-safety',
    'view-layer-limit-safety',
    'bframes-parse-safety',
    'bframe-bias-parse-safety',
    'keyint-parse-safety',
    'min-keyint-parse-safety',
    'ip-pb-ratio-parse-safety',
    'vbv-end-fr-adj-safety',
    'zone-alloc-size-safety',
    'ref-parse-safety',
    'radl-parse-safety',
    'cbqpoffs-parse-safety',
    'crqpoffs-parse-safety',
    'pass-parse-safety',
    'qg-size-parse-safety',
    'qpmin-parse-safety',
    'qpmax-parse-safety',
    'chromaloc-parse-safety',
    'vbv-maxrate-parse-safety',
    'vbv-bufsize-parse-safety',
    'log2-max-poc-lsb-parse-safety',
    'nr-intra-parse-safety',
    'nr-inter-parse-safety',
    'rc-lookahead-parse-safety',
    'slices-parse-safety',
    'limit-tu-parse-safety',
    'lookahead-threads-parse-safety',
    'vbv-fullness-parse-safety',
    'zonefile-startframe-safety',
    'reconfig-window-size-safety',
    'no-reset-zone-prefill-guard',
    'rdpenalty-parse-safety',
    'gop-lookahead-parse-safety',
    'gop-lookahead-usage-safety',
    'common-logfile-open-state',
    'common-logfile-close-state',
    'common-slurp-open-state',
    'common-slurp-close-state',
    'common-slurp-size-guard',
    'cutree-sharedmem-name-guard',
    'mkv-writer-open-state',
    'mkv-writer-close-state',
    'riscv-cpuinfo-open-state',
    'riscv-cpuinfo-close-state',
    'cli-destroy-close-state',
    'encoder-destroy-close-state',
    'lambda-file-close-state',
    'film-grain-close-state',
    'gop-cleanup-close-state',
    'mp4-preflight-close-state',
    'gop-early-close-state',
    'gop-intermediate-close-state',
    'ratecontrol-destroy-close-state',
    'ratecontrol-write-fail-state',
    'ratecontrol-cutree-read-fail-state',
    'mp4-handle-close-state',
    'mp4-header-sei-alloc-guard',
    'raw-close-state',
    'raw-open-cleanup-state',
    'x265-check-macro-open-state',
    'x265-check-macro-close-state',
    'scalinglist-close-state',
    'vmaf-encoder-log-close-state',
    'y4m-input-close-state',
    'yuv-input-close-state',
    'reconplay-pclose-state',
    'multiview-parse-close-state',
    'multiview-config-parse-usage',
    'scenecut-aware-qp-config-parse-usage',
    'scenecut-aware-qp-parse-safety',
    'abr-parse-cleanup-state',
    'scenecut-qp-cleanup-state',
    'x265-main-cleanup-state',
    'abr-config-parse-usage',
    'abr-init-result-propagation',
    'abr-init-helper-cleanup',
    'abr-init-reader-rollback',
    'abr-init-api-null',
    'abr-init-output-null',
    'abr-init-filter-null',
    'abr-init-reader-alloc',
    'abr-start-threads-failure-propagation',
    'abr-ladder-open-state',
    'abr-help-exit-precedence',
    'abr-primary-param-guards',
    'abr-ctor-top-guards',
    'abr-queue-picture-guards',
    'abr-thread-queue-state-guards',
    'abr-counter-state-guards',
    'abr-picture-state-guards',
    'abr-setreuselevel-ref',
    'abr-thread-multiview-field-guard',
    'abr-thread-multiview-input-guard',
    'abr-thread-reconplay-alloc-guard',
    'abr-thread-pic-in-reset-guard',
    'abr-thread-dolby-rpu-eof-guard',
    'abr-thread-output-null-guard',
    'abr-thread-fail-output',
    'abr-thread-fail-encoder',
    'abr-thread-output-picture',
    'abr-thread-layered-recon',
    'abr-thread-api-null',
    'abr-thread-dither-input',
    'abr-thread-field-buffer',
    'abr-thread-field-buffer-state',
    'abr-thread-field-view-usage',
    'abr-thread-field-layout',
    'abr-thread-field-plane',
    'abr-thread-field-reuse',
    'abr-thread-pts-queue-alloc',
    'abr-thread-recon-state',
    'abr-thread-recon-write',
    'abr-copyinfo-inter-arrays',
    'abr-copyinfo-intra-arrays',
    'abr-copyinfo-src',
    'abr-copyinfo-analysis-buffer',
    'abr-analysis-slot-wait',
    'abr-copyinfo-vbv-lookahead',
    'abr-allocbuffers-top-guards',
    'abr-allocbuffers-partial-cleanup',
    'abr-allocbuffers-queue-guards',
    'abr-allocbuffers-analysisread',
    'abr-allocbuffers-analysiswrite',
    'abr-allocbuffers-picidx',
    'abr-allocbuffers-readflag',
    'abr-readpicture-srcpic',
    'abr-readpicture-analysis',
    'abr-thread-readpicture-failure-guard',
    'abr-readpicture-analysis-queue',
    'abr-scaler-videodesc-alloc',
    'abr-scaler-videodesc-ownership',
    'abr-scaler-init-failure-handling',
    'abr-thread-analysis-read',
    'analysis-intra-alloc-guards',
    'analysis-inter-alloc-guards',
    'analysis-inter-motion-alloc-guards',
    'analysis-inter-temp-luma-alloc-guard',
    'analysis-inter-depth-run-guard',
    'analysis-cache-cost-guards',
    'scaled-analysis-load-alloc-guards',
    'analysis-2pass-load-cleanup',
    'picyuv-offset-rollback',
    'motion-reference-init-guards',
    'motionestimate-init-guard',
    'motion-sea-scratch-guard',
    'scaler-slice-linebuf-init',
    'analysis-load-staging-cleanup',
    'atc-sei-parse-safety',
    'chunk-start-parse-safety',
    'chunk-end-parse-safety',
    'deblock-parse-safety',
    'hash-parse-safety',
    'hme-parse-safety',
    'lookahead-slices-parse-safety',
    'merange-parse-safety',
    'misc-control-parse-safety',
    'pic-struct-parse-safety',
    'psy-scale-parse-safety',
    'rskip-parse-safety',
    'rskip-edge-threshold-parse-safety',
    'sar-parse-safety',
    'selective-sao-parse-safety',
    'ssim-rd-parse-safety',
    'temporal-layers-parse-safety',
    'uint32-token-parse-safety',
    'json11-number-boundary-safety',
    'cli-inputfn-alloc-guard',
    'cli-vmaf-format-cleanup',
    'input-filename-copy-usage',
    'print-status-progress-guard',
    'recon-basename-parse-usage',
    'zonefile-parse-no-exit',
    'svt-aud-parse-safety',
    'svt-base-layer-switch-mode-parse-safety',
    'svt-compressed-ten-bit-parse-safety',
    'svt-constrained-intra-parse-safety',
    'svt-fps-in-vps-parse-safety',
    'svt-frames-to-be-encoded-parse-safety',
    'svt-hdr-parse-safety',
    'svt-hierarchical-level-parse-safety',
    'svt-high-tier-parse-safety',
    'svt-hrd-parse-safety',
    'svt-input-depth-parse-safety',
    'svt-keyint-parse-safety',
    'svt-master-display-parse-safety',
    'svt-nalu-file-parse-safety',
    'svt-pred-struct-parse-safety',
    'svt-qpmax-parse-safety',
    'svt-qpmin-parse-safety',
    'svt-rc-lookahead-parse-safety',
    'svt-sao-parse-safety',
    'svt-scenecut-parse-safety',
    'svt-search-height-parse-safety',
    'svt-search-width-parse-safety',
    'svt-speed-control-parse-safety',
    'svt-vbv-bufsize-parse-safety',
    'svt-vbv-init-parse-safety',
    'svt-vbv-maxrate-parse-safety',
    'svt-vui-timing-info-parse-safety',
    'svt-hme-parse-safety',
    'svt-interlace-parse-safety',
    'svt-open-gop-parse-safety',
    'svt-pools-exclude-both-sockets-guard',
    'encoder-rpu-replace-safety',
    'copy-user-sei-staging',
    'dup-side-data-staging',
    'read-user-sei-staging',
    'copy-picture-staging',
    'dup-create-alloc-guards',
    'encode-quant-offsets-staging',
    'read-user-sei-cleanup',
    'log-progress-file-parse-safety',
    'negated-bool-alias-parse-safety',
    'rd-parse-safety',
    'limit-refs-parse-safety',
    'dup-threshold-parse-safety',
    'vmaf-flush-cleanup',
    'avs-buffer-replace-safety',
    'vpy-buffer-replace-safety',
    'zimg-token-parse-usage',
    'zimg-init-rollback',
    'dynamic-hdr10-legacy-patterns',
    'sei-unsigned-token-safety',
    'video-signal-type-preset-parse',
    'sei-mastering-display-parse',
    'sao-param-staging',
    'zone-parse-replace-safety',
    'cpu-name-strdup-safety',
    'x265-fclose-macro-state',
    'hme-param-sscanf-usage',
    'masking-strength-scan-usage',
    'reviewed-string-copy-usage',
    'analysis-open-state',
    'analysis-load-open-state',
    'cli-config-open-state',
    'cli-help-exit-cleanup',
    'lambda-file-open-state',
    'vmaf-input-open-state',
    'nalu-file-open-state',
    'tonemap-file-open-state',
    'scalinglist-open-state',
    'gop-open-state',
    'film-grain-open-state',
    'ratecontrol-stats-open-state',
)

DIRECT_WORKFLOW_VALIDATOR_EXCEPTIONS = {
    'check_dependency_patch_suffixes.py': 'dependency-suffixes',
    'check_profdata_metadata.py': 'profdata-metadata',
    'check_vbv_end_frame_adjust_safety.py': 'vbv-end-fr-adj-safety',
    'check_zone_and_scenecut_param_parse_null_guards.py': 'zone-scenecut-param-parse-null-guards',
    'check_frame_create_mcstffencpic_guards.py': 'frame-create-mcstf-fenc-pic-guards',
    'check_frame_create_top_alloc_guards.py': 'frame-create-top-alloc-guards',
}


def preferred_bash():
    try:
        return checker_module.bash_path(None)
    except checker_module.GuardFailure:
        return None


def run_checker(repo, checks=None):
    command = ['check_ci_guards.py', '--repo-root', str(repo)]
    bash = preferred_bash()
    if bash:
        command.extend(['--bash', bash])
    for check in checks or ():
        command.extend(['--only', check])

    stdout = io.StringIO()
    stderr = io.StringIO()
    argv = sys.argv
    exit_code = 0
    try:
        sys.argv = command
        with redirect_stdout(stdout), redirect_stderr(stderr):
            checker_module.main()
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            exit_code = code
        elif code is None:
            exit_code = 0
        else:
            exit_code = 1
            print(code, file=stderr)
    finally:
        sys.argv = argv

    output = stdout.getvalue() + stderr.getvalue()
    return SimpleNamespace(returncode=exit_code, stdout=output)


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


ACTIVE_CHANGE_TRACKER = None


class RepoChangeTracker:
    def __init__(self, repo):
        self.repo = Path(repo).resolve()
        self.original_files = {}
        self.created_dirs = set()

    def record_path(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.repo):
            raise AssertionError(f'change path escaped case repo: {path}')
        if path not in self.original_files:
            if path.exists():
                stat = path.stat()
                self.original_files[path] = (path.read_bytes(), stat.st_mtime_ns)
            else:
                self.original_files[path] = None
        for parent in path.parents:
            if parent == self.repo:
                break
            if not parent.exists():
                self.created_dirs.add(parent)

    def restore(self):
        for path, original in sorted(self.original_files.items(), key=lambda item: len(item[0].parts), reverse=True):
            if original is None:
                if path.exists():
                    path.unlink()
                continue
            original_bytes, original_mtime_ns = original
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_bytes() != original_bytes:
                path.write_bytes(original_bytes)
            os.utime(path, ns=(original_mtime_ns, original_mtime_ns))
        for path in sorted(self.created_dirs, key=lambda item: len(item.parts), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass


def track_repo_path(path):
    if ACTIVE_CHANGE_TRACKER is not None:
        ACTIVE_CHANGE_TRACKER.record_path(path)


def replace_text(path, old, new, count=1):
    track_repo_path(path)
    fixture_replace_text(path, old, new, count)


def assert_validator_coverage():
    covered = set(BASELINE_CHECKS) | set(TARGETED_CHECKS)
    missing = sorted(set(checker_module.VALIDATOR_NAMES) - covered)
    if missing:
        raise AssertionError(f'uncovered validators: {", ".join(missing)}')
    unexpected = sorted(covered - set(checker_module.VALIDATOR_NAMES))
    if unexpected:
        raise AssertionError(f'unknown covered validators: {", ".join(unexpected)}')


def direct_python_scripts(commands):
    direct_checkers = set()
    direct_tests = set()
    for command in commands:
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        if len(tokens) < 2 or tokens[0] != 'python':
            continue
        script_name = Path(tokens[1]).name
        if script_name.startswith('check_') and script_name.endswith('.py'):
            direct_checkers.add(script_name)
        elif script_name.startswith('test_check_') and script_name.endswith('.py'):
            direct_tests.add(script_name)
    return direct_checkers, direct_tests


def workflow_data_direct_script_names():
    commands = []
    for requirements in (build_step_requirements(), profiling_step_requirements(), pgo_step_requirements()):
        for _job_name, _step_name, required_items in requirements:
            commands.extend(required_items)
    return direct_python_scripts(commands)


def workflow_requirements_direct_script_names(requirements):
    commands = []
    for _job_name, _step_name, required_items in requirements:
        commands.extend(required_items)
    return direct_python_scripts(commands)


def workflow_direct_script_names(relative_path, requirements):
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / relative_path
    parsed = checker_module.load_yaml(repo_root, relative_path)
    commands = []
    for job_name, step_name, _required_items in requirements:
        commands.extend(
            checker_module.shell_active_logical_lines(
                checker_module.workflow_step_run(parsed, path, job_name, step_name)
            )
        )
    return direct_python_scripts(commands)


def assert_workflow_script_parity(label, relative_path, requirements):
    workflow_checkers, workflow_tests = workflow_direct_script_names(relative_path, requirements)
    data_checkers, data_tests = workflow_requirements_direct_script_names(requirements)

    missing_checkers = sorted(data_checkers - workflow_checkers)
    unexpected_checkers = sorted(workflow_checkers - data_checkers)
    if missing_checkers or unexpected_checkers:
        problems = []
        if missing_checkers:
            problems.append(f'missing {label} checkers: {", ".join(missing_checkers)}')
        if unexpected_checkers:
            problems.append(f'unexpected {label} checkers: {", ".join(unexpected_checkers)}')
        raise AssertionError('; '.join(problems))

    missing_tests = sorted(data_tests - workflow_tests)
    unexpected_tests = sorted(workflow_tests - data_tests)
    if missing_tests or unexpected_tests:
        problems = []
        if missing_tests:
            problems.append(f'missing {label} guard tests: {", ".join(missing_tests)}')
        if unexpected_tests:
            problems.append(f'unexpected {label} guard tests: {", ".join(unexpected_tests)}')
        raise AssertionError('; '.join(problems))


def assert_direct_workflow_script_parity():
    assert_workflow_script_parity('build workflow', checker_module.BUILD_WORKFLOW, build_workflow_step_requirements())
    assert_workflow_script_parity('build-profiling workflow', checker_module.BUILD_PROFILING_WORKFLOW, profiling_step_requirements())
    assert_workflow_script_parity('build-pgo workflow', checker_module.BUILD_PGO_WORKFLOW, pgo_step_requirements())


def workflow_data_direct_validator_names():
    direct_checkers = set()
    direct_tests = set()
    direct_checkers, direct_tests = workflow_data_direct_script_names()

    unknown = []
    validators = set()
    for checker in sorted(direct_checkers):
        if f'test_{checker}' not in direct_tests:
            continue
        if checker == 'check_ci_guards.py':
            continue
        if checker in DIRECT_WORKFLOW_VALIDATOR_EXCEPTIONS:
            validators.add(DIRECT_WORKFLOW_VALIDATOR_EXCEPTIONS[checker])
            continue

        stem = Path(checker).stem.removeprefix('check_').replace('_', '-')
        candidates = [stem]
        if stem.endswith('-guard'):
            candidates.append(stem[:-len('-guard')])
        if stem.endswith('-guards'):
            candidates.append(stem[:-len('-guards')])

        for candidate in candidates:
            if candidate in checker_module.VALIDATOR_NAMES:
                validators.add(candidate)
                break
        else:
            unknown.append(checker)

    if unknown:
        raise AssertionError(f'unmapped workflow-data direct checkers: {", ".join(unknown)}')
    return validators


def assert_direct_workflow_validator_parity():
    covered = set(BASELINE_CHECKS) | set(TARGETED_CHECKS)
    direct_validators = workflow_data_direct_validator_names()
    missing_coverage = sorted(direct_validators - covered)
    if missing_coverage:
        raise AssertionError(
            f'direct workflow validators missing aggregate coverage: {", ".join(missing_coverage)}'
        )


def assert_direct_workflow_validator_parity_includes_profiling_and_pgo_only_checks():
    repo_root = Path(__file__).resolve().parents[2]
    runner_text = (repo_root / checker_module.PYTHON_CI_GUARD_BUNDLE).read_text(encoding='utf-8')
    for required in (
        "('python', '.github/scripts/check_profdata_metadata.py', '--self-test'),",
        "('python', '.github/scripts/test_check_profdata_metadata.py'),",
        "('python', '.github/scripts/test_check_pgo_consume_chain.py'),",
    ):
        if required not in runner_text:
            raise AssertionError(f'Python CI guard bundle missing profiling/pgo-only suite command: {required}')


def assert_validate_yaml_parse_ruby_fallback():
    repo_root = Path(__file__).resolve().parents[2]
    calls = []
    stdout = io.StringIO()
    original_validate_pyyaml = helper_module.validate_yaml_parse_with_pyyaml
    original_validate_ruby = helper_module.validate_yaml_parse_with_ruby
    original_which = helper_module.shutil.which
    try:
        def missing_pyyaml(_repo_root, _workflow_dir, _action_dir):
            raise ModuleNotFoundError("No module named 'yaml'")

        def fake_validate_ruby(repo_root_arg, workflow_dir_arg, action_dir_arg, ruby):
            calls.append((repo_root_arg, workflow_dir_arg, action_dir_arg, ruby))

        helper_module.validate_yaml_parse_with_pyyaml = missing_pyyaml
        helper_module.validate_yaml_parse_with_ruby = fake_validate_ruby
        helper_module.shutil.which = lambda executable: 'ruby' if executable == 'ruby' else None
        with redirect_stdout(stdout):
            helper_module.validate_yaml_parse(repo_root, checker_module.WORKFLOW_DIR, checker_module.ACTION_DIR)
    finally:
        helper_module.validate_yaml_parse_with_pyyaml = original_validate_pyyaml
        helper_module.validate_yaml_parse_with_ruby = original_validate_ruby
        helper_module.shutil.which = original_which

    if calls != [(repo_root, checker_module.WORKFLOW_DIR, checker_module.ACTION_DIR, 'ruby')]:
        raise AssertionError(f'unexpected ruby fallback calls: {calls!r}')
    if stdout.getvalue().strip() != 'YAML files parsed with ruby':
        raise AssertionError(stdout.getvalue())


def assert_validate_yaml_parse_ruby_fallback_rejects(relative_path, parsed_mapping, expected_message):
    repo_root = Path(__file__).resolve().parents[2]
    expected_path = repo_root / relative_path
    original_yaml_module = helper_module.yaml_module
    original_parse_yaml_with_ruby = helper_module.parse_yaml_with_ruby
    original_which = helper_module.shutil.which
    try:
        def missing_yaml():
            raise ModuleNotFoundError("No module named 'yaml'")

        def fake_parse_yaml_with_ruby(path, ruby):
            if ruby != 'ruby':
                raise AssertionError(f'unexpected ruby executable: {ruby!r}')
            if path == expected_path:
                return parsed_mapping
            if path.parent == repo_root / checker_module.WORKFLOW_DIR:
                return {'jobs': {'build': {}}}
            if path.name == 'action.yml':
                return {'runs': {'using': 'composite', 'steps': []}}
            raise AssertionError(f'unexpected yaml path: {path}')

        helper_module.yaml_module = missing_yaml
        helper_module.parse_yaml_with_ruby = fake_parse_yaml_with_ruby
        helper_module.shutil.which = lambda executable: 'ruby' if executable == 'ruby' else None

        try:
            helper_module.validate_yaml_parse(repo_root, checker_module.WORKFLOW_DIR, checker_module.ACTION_DIR)
        except helper_module.GuardFailure as exc:
            if exc.message != expected_message:
                raise AssertionError(f'unexpected failure message: {exc.message!r}')
            if exc.path != expected_path:
                raise AssertionError(f'unexpected failure path: {exc.path!r}')
        else:
            raise AssertionError('validate_yaml_parse unexpectedly accepted an invalid ruby fallback structure')
    finally:
        helper_module.yaml_module = original_yaml_module
        helper_module.parse_yaml_with_ruby = original_parse_yaml_with_ruby
        helper_module.shutil.which = original_which
        helper_module.clear_runtime_caches()


def assert_validate_yaml_parse_ruby_fallback_rejects_non_mapping():
    assert_validate_yaml_parse_ruby_fallback_rejects(
        checker_module.BUILD_WORKFLOW,
        ['not', 'a', 'mapping'],
        'YAML file did not parse to a mapping',
    )


def assert_validate_yaml_parse_ruby_fallback_rejects_missing_jobs():
    assert_validate_yaml_parse_ruby_fallback_rejects(
        checker_module.BUILD_WORKFLOW,
        {'name': 'build'},
        'workflow YAML is missing a jobs mapping',
    )


def assert_validate_yaml_parse_ruby_fallback_rejects_missing_runs():
    assert_validate_yaml_parse_ruby_fallback_rejects(
        checker_module.WINDOWS_DEPS_ACTION,
        {'name': 'setup'},
        'action YAML is missing a runs mapping',
    )


def assert_load_yaml_ruby_fallback_handles_boolean_on_key():
    repo_root = Path(__file__).resolve().parents[2]
    relative_path = checker_module.BUILD_WORKFLOW
    expected_path = repo_root / relative_path
    expected_on = {'pull_request': None}
    parsed_mapping = {True: expected_on, 'jobs': {'build': {'steps': []}}}
    calls = []
    original_yaml_module = helper_module.yaml_module
    original_parse_yaml_with_ruby = helper_module.parse_yaml_with_ruby
    original_which = helper_module.shutil.which
    helper_module.clear_runtime_caches()
    try:
        def missing_yaml():
            raise ModuleNotFoundError("No module named 'yaml'")

        def fake_parse_yaml_with_ruby(path, ruby):
            calls.append((path, ruby))
            return parsed_mapping

        helper_module.yaml_module = missing_yaml
        helper_module.parse_yaml_with_ruby = fake_parse_yaml_with_ruby
        helper_module.shutil.which = lambda executable: 'ruby' if executable == 'ruby' else None

        parsed = helper_module.load_yaml(repo_root, relative_path)
        on_block = helper_module.workflow_on(parsed, expected_path)
    finally:
        helper_module.yaml_module = original_yaml_module
        helper_module.parse_yaml_with_ruby = original_parse_yaml_with_ruby
        helper_module.shutil.which = original_which
        helper_module.clear_runtime_caches()

    if calls != [(expected_path, 'ruby')]:
        raise AssertionError(f'unexpected load_yaml ruby fallback calls: {calls!r}')
    if parsed is not parsed_mapping:
        raise AssertionError('load_yaml did not return the ruby fallback mapping')
    if on_block != expected_on:
        raise AssertionError(f'unexpected workflow on mapping: {on_block!r}')


def main():
    assert_validate_yaml_parse_ruby_fallback()
    assert_validate_yaml_parse_ruby_fallback_rejects_non_mapping()
    assert_validate_yaml_parse_ruby_fallback_rejects_missing_jobs()
    assert_validate_yaml_parse_ruby_fallback_rejects_missing_runs()
    assert_load_yaml_ruby_fallback_handles_boolean_on_key()

    if not preferred_bash():
        print('bash is unavailable; skipping CI guard tests')
        return

    assert_validator_coverage()
    assert_direct_workflow_script_parity()
    assert_direct_workflow_validator_parity()
    assert_direct_workflow_validator_parity_includes_profiling_and_pgo_only_checks()

    def build_workflow(repo):
        return repo / '.github' / 'workflows' / 'build.yml'

    def profiling_workflow(repo):
        return repo / '.github' / 'workflows' / 'build-profiling.yml'

    def build_pgo_workflow(repo):
        return repo / '.github' / 'workflows' / 'build-pgo.yml'

    def update_deps_workflow(repo):
        return repo / '.github' / 'workflows' / 'update-deps.yml'

    def windows_deps_action(repo):
        return repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml'

    def profiling_action(repo):
        return repo / '.github' / 'actions' / 'build-x265-profiling' / 'action.yml'

    def scan_helper(repo):
        return repo / '.github' / 'scripts' / 'cxx20_scan_helpers.sh'

    def ensure_cmake4_helper(repo):
        return repo / '.github' / 'scripts' / 'ensure_cmake4.sh'

    def ensure_linux_sanitizer_toolchain_helper(repo):
        return repo / '.github' / 'scripts' / 'ensure_linux_sanitizer_toolchain.sh'

    def runtime_suite(repo):
        return repo / '.github' / 'scripts' / 'runtime_smoke_suite.sh'

    def mp4_suite(repo):
        return repo / '.github' / 'scripts' / 'mp4_smoke_suite.sh'

    def profiling_smoke_helper(repo):
        return repo / '.github' / 'scripts' / 'profiling_smoke_package_verify.sh'

    def archive_verify_helper(repo):
        return repo / '.github' / 'scripts' / 'verify_ci_archive.sh'

    def ci_7z_helper(repo):
        return repo / '.github' / 'scripts' / 'ci_7z.sh'

    def ci_version_helper(repo):
        return repo / '.github' / 'scripts' / 'ci_version_helpers.sh'

    def python_ci_guard_bundle_runner(repo):
        return repo / '.github' / 'scripts' / 'run_python_ci_guard_bundle.py'

    def release_asset_validator(repo):
        return repo / '.github' / 'scripts' / 'validate_release_assets.sh'

    def source_test_vector_checker(repo):
        return repo / '.github' / 'scripts' / 'check_source_test_vectors.py'

    def source_test_vector_guard_test(repo):
        return repo / '.github' / 'scripts' / 'test_check_source_test_vectors.py'

    def build_getopt_c_fixture():
        lines = ['int line_%d = 0;' % i for i in range(1, 965)]
        replacements = {
            321: 'if (new_str == NULL) {}',
            395: 'nextchar = NULL;',
            411: 'else if (posixly_correct != NULL) {}',
            417: 'if (posixly_correct == NULL) {}',
            422: 'if (__getopt_nonoption_flags == NULL) {}',
            433: 'if (__getopt_nonoption_flags == NULL) {}',
            521: 'optarg = NULL;',
            543: "if (nextchar == NULL || *nextchar == '\\0') {}",
            617: 'if (longopts != NULL) {}',
            635: 'if (longopts != NULL) {}',
            641: 'const struct option *pfound = NULL;',
            664: 'else if (pfound == NULL) {}',
            689: 'if (pfound != NULL) {}',
            737: 'if (longind != NULL) {}',
            752: 'if (my_index(optstring, *nextchar) == NULL) {}',
            782: "if (temp == NULL || c == ':') {}",
            802: 'const struct option *pfound = NULL;',
            855: 'else if (pfound == NULL) {}',
            874: 'if (pfound != NULL) {}',
            909: 'if (longind != NULL) {}',
            918: 'nextchar = NULL;',
            932: 'optarg = NULL;',
            933: 'nextchar = NULL;',
            964: 'nextchar = NULL;',
        }
        for line, text in replacements.items():
            lines[line - 1] = text
        return '\n'.join(lines) + '\n'

    def build_getopt_h_fixture():
        lines = ['int line_%d = 0;' % i for i in range(1, 183)]
        lines[84] = "/* If the field `flag' is not NULL, it points to a variable that is set */"
        return '\n'.join(lines) + '\n'

    def write_repo_file(repo, relative, text):
        path = repo / relative
        track_repo_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def remove_repo_file(path):
        track_repo_path(path)
        path.unlink()

    def seed_abr_guard_sources(repo):
        write_repo_file(
            repo,
            Path('source/abrEncApp.cpp'),
            '\n'.join(
                (
                    'bool AbrEncoder::allocBuffers()',
                    '{',
                    'if (primaryParam->numViews > 1)',
                    '{',
                    '    if (pass == 0)',
                    '    {',
                    '        m_analysisWrite[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];',
                    '        if (!m_analysisWrite[pass])',
                    '            goto fail;',
                    '    }',
                    '}',
                    'else',
                    '{',
                    '    for (uint8_t pass = 0; pass < m_numEncodes; pass++)',
                    '    {',
                    '        m_analysisWrite[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];',
                    '        if (!m_analysisWrite[pass])',
                    '            goto fail;',
                    '    }',
                    '}',
                    '#if ENABLE_MULTIVIEW',
                    'fail:',
                    '    return false;',
                    '#endif',
                    '}',
                    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
                    '{',
                    'int analysisQId = m_cliopt.refId;',
                    'PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];',
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int written = analysisWrite * analysisPass->m_cliopt.numRefs;',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    'int write = m_parent->m_analysisWrite[analysisQId][i].get() * analysisPass->m_cliopt.numRefs;',
                    'analysisIdx = analysisRead % m_parent->m_queueSize;',
                    'resultData = &m_parent->m_analysisBuffer[analysisQId][analysisIdx];',
                    'int slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].get();',
                    'while (m_threadActive.load() && resultData->poc == (uint32_t)ipread && !slotWrite)',
                    '{',
                    '    slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].waitForChange(slotWrite);',
                    '}',
                    'int write = slotWrite * analysisPass->m_cliopt.numRefs;',
                    'int read = m_parent->m_analysisRead[analysisQId][analysisIdx].get();',
                    'if ((resultData->poc != (uint32_t)ipread) || (read >= write))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Mismatched no-lookahead analysis slot for frame %d at slot %d encoder %u\\n", ipread, analysisIdx, m_id);',
                    '    m_ret = 4;',
                    '    return false;',
                    '}',
                    'readPos = resultData->poc % m_parent->m_queueSize;',
                    '}',
                    'void PassEncoder::copyInfo(x265_analysis_data * src)',
                    '{',
                    'int index = selectAnalysisWriteIndex(written);',
                    'if (m_ret)',
                    '    return;',
                    'if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])',
                    '{',
                    '}',
                    '}',
                    'int PassEncoder::selectAnalysisWriteIndex(uint32_t written)',
                    '{',
                    'while (!emptyIdxFound && overwrite)',
                    '{',
                    '    if (read == write)',
                    '    {',
                    '        break;',
                    '    }',
                    '    if (!emptyIdxFound && m_threadActive.load())',
                    '    {',
                    '        int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();',
                    '        m_parent->m_analysisReadCnt[m_id].waitForChange(prevReadCnt);',
                    '    }',
                    '}',
                    'if (!emptyIdxFound && overwrite)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Timed out waiting for reusable analysis queue slot for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (m_cliopt.loadLevel && picInput)',
                    '{',
                    '    if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '        !m_parent->m_analysisReadCnt)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '        goto fail;',
                    '    }',
                    '    m_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    '    m_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    'fail:',
                    'if (m_cliopt.loadLevel && m_parent && m_parent->m_analysisReadCnt)',
                    '{',
                    '    m_parent->m_analysisReadCnt[m_cliopt.refId].poke();',
                    '}',
                    '}',
                    'if (!src || !dst)',
                    'delete src;',
                    'delete dst;',
                    'x265_log(m_param, X265_LOG_ERROR, "\\n MALLOC failure in Scaler");',
                    'result = 4;',
                    'm_ret = 4;',
                    'return -1;',
                    'm_scaler = new (std::nothrow) Scaler(0, 1, m_id, src, dst, this);',
                    'if (!m_scaler)',
                    'else if (!m_scaler->m_initOk)',
                    'm_scaler->destroy();',
                    'delete m_scaler;',
                    'm_scaler = nullptr;',
                    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
                    '    pic_in[view] = nullptr;',
                    'else if (readPicture(pic_in[view], view)){',
                    '    if(view == viewCount - 1)',
                    '        inFrameCount++;',
                    '}',
                    'else if (m_ret != 0)',
                    '    goto fail;',
                    'else',
                    '    pic_in[view] = nullptr;',
                    'if (m_input[view]->readPicture(*src))',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].incr();',
                    'else if (m_input[view]->isFail())',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Reader input failed for view %d\\n", view);',
                    '    m_parentEnc->m_ret = 4;',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    break;',
                    '}',
                    'else',
                    '{',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    break;',
                    '}',
                )
            ) + '\n',
        )
        write_repo_file(
            repo,
            Path('source/input/lavf.cpp'),
            '\n'.join(
                (
                    'if(ret < 0)',
                    '{',
                    '    av_packet_unref(pkt);',
                    '    if (ret != AVERROR_EOF)',
                    '    {',
                    '        general_log(nullptr, "lavf", X265_LOG_WARNING, "reading input failed on frame %d\\n", h->next_frame);',
                    '        b_fail = true;',
                    '        fail = 1;',
                    '        break;',
                    '    }',
                    '}',
                    'if(codec_ret == AVERROR(EINVAL))',
                    '{',
                    '    general_log(nullptr, "lavf", X265_LOG_WARNING, "feeding input to decoder failed on frame %d\\n", h->next_frame);',
                    '    b_fail = true;',
                    '    fail = 1;',
                    '}',
                    'if(codec_ret == AVERROR(EINVAL))',
                    '{',
                    '    general_log(nullptr, "lavf", X265_LOG_WARNING, "video decoding failed on frame %d\\n", h->next_frame);',
                    '    b_fail = true;',
                    '    fail = 1;',
                    '}',
                )
            ) + '\n',
        )

    def seed_gnu20_foundation_sources(repo):
        for relative in cli_nullptr_checker.TARGETS:
            write_repo_file(repo, relative, 'void ok() { void* p = nullptr; }\n')

        write_repo_file(repo, Path('source/abrEncApp.cpp'), 'static volatile sig_atomic_t b_ctrl_c /* = 0 */;\n')
        write_repo_file(repo, Path('source/common/cpu.cpp'), 'static volatile sig_atomic_t canjump = 0;\n')
        write_repo_file(
            repo,
            Path('source/common/threading.h'),
            '\n'.join(
                (
                    '#define ATOMIC_INC(ptr)       InterlockedIncrement((volatile LONG*)ptr)',
                    '#define ATOMIC_DEC(ptr)       InterlockedDecrement((volatile LONG*)ptr)',
                    '#define ATOMIC_ADD(ptr, val)  (sizeof(*(ptr)) == 8 ? \\',
                    '                               InterlockedExchangeAdd64((volatile LONGLONG*)ptr, (LONGLONG)(val)) : \\',
                    '                               InterlockedExchangeAdd((volatile LONG*)ptr, (LONG)(val)))',
                    '#define ATOMIC_OR(ptr, mask)  _InterlockedOr((volatile LONG*)ptr, (LONG)mask)',
                    '#define ATOMIC_AND(ptr, mask) _InterlockedAnd((volatile LONG*)ptr, (LONG)mask)',
                )
            ) + '\n',
        )
        write_repo_file(
            repo,
            Path('source/dynamicHDR10/json11/json11.h'),
            '\n'.join(
                (
                    '#ifdef _MSC_VER',
                    '    #if _MSC_VER <= 1800 // VS 2013',
                    '        #define JSON11_NOEXCEPT',
                    '    #else',
                    '        #define JSON11_NOEXCEPT noexcept',
                    '    #endif',
                    '#else',
                    '    #define JSON11_NOEXCEPT noexcept',
                    '#endif',
                    'class Json {',
                    'public:',
                    '    Json() JSON11_NOEXCEPT;',
                    '    Json(std::nullptr_t) JSON11_NOEXCEPT;',
                    '};',
                    '#undef JSON11_NOEXCEPT',
                )
            ) + '\n',
        )
        write_repo_file(
            repo,
            Path('source/dynamicHDR10/json11/json11.cpp'),
            '\n'.join(
                (
                    'Json::Json() JSON11_NOEXCEPT {}',
                    'Json::Json(std::nullptr_t) JSON11_NOEXCEPT {}',
                )
            ) + '\n',
        )
        write_repo_file(repo, Path('source/common/common.h'), 'static const int ok = 1;\n')
        write_repo_file(
            repo,
            Path('source/common/threadpool.cpp'),
            '\n'.join(
                (
                    'if (std::strcmp(p->numaPools, "NULL") == 0) {}',
                    'else if (!strcasecmp(nodeStr, "NULL")) {}',
                )
            ) + '\n',
        )
        write_repo_file(repo, Path('source/x265.h'), 'static const int ok = 0;\n/* NULL in comment is fine */\n')
        write_repo_file(repo, Path('source/compat/getopt/getopt.c'), build_getopt_c_fixture())
        write_repo_file(repo, Path('source/compat/getopt/getopt.h'), build_getopt_h_fixture())

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        repo = tmp_root / 'pass-repo'
        write_repo(repo, __file__)
        expect_pass(run_checker(repo, checks=BASELINE_CHECKS))
        seed_abr_guard_sources(repo)
        for check in (
            'abr-analysis-slot-wait',
            'abr-allocbuffers-analysiswrite',
            'abr-thread-readpicture-failure-guard',
            'abr-readpicture-analysis-queue',
            'abr-scaler-init-failure-handling',
            'abr-thread-analysis-read',
        ):
            expect_pass(run_checker(repo, checks=(check,)))

        case_repo = tmp_root / 'case-repo'
        write_repo(case_repo, __file__)

        def fail_case(modifier, expected, check):
            global ACTIVE_CHANGE_TRACKER
            tracker = RepoChangeTracker(case_repo)
            ACTIVE_CHANGE_TRACKER = tracker
            try:
                modifier(case_repo)
                expect_fail(run_checker(case_repo, checks=(check,)), expected)
            finally:
                ACTIVE_CHANGE_TRACKER = None
                tracker.restore()

        def replace_profiling_scan_helper_arg(repo, old, new):
            path = scan_helper(repo)
            text = path.read_text()
            start_marker = 'check_cxx20_commands_profiling() {'
            end_marker = '\n}\n\ncheck_cxx20_commands_pgo_consume()'
            start = text.index(start_marker)
            end = text.index(end_marker, start)
            block = text[start:end]
            if old not in block:
                raise AssertionError(f'missing text {old!r} in profiling scan helper block')
            track_repo_path(path)
            path.write_text(text[:start] + block.replace(old, new, 1) + text[end:])

        cases = (
            case(lambda repo: replace_text(scan_helper(repo), '--forbidden-flag=-fprofile-instr-use', '--forbidden-flag=-fprofile-instr-generate'), 'missing profiling compile_commands guard: --forbidden-flag=-fprofile-instr-use', 'scan-helper'),
            case(lambda repo: replace_text(scan_helper(repo), '--forbidden-flag-substring=-fprofile-instr-use=', '--forbidden-flag-substring=-fprofile-instr-generate='), 'missing profiling compile_commands guard: --forbidden-flag-substring=-fprofile-instr-use=', 'scan-helper'),
            case(lambda repo: replace_text(scan_helper(repo), '--required-flag="$pgo_flag"', '--required-flag-prefix=-fprofile-instr-use='), 'missing profiling compile_commands guard: --required-flag=$pgo_flag', 'scan-helper'),
            case(lambda repo: replace_profiling_scan_helper_arg(repo, '"${cxx20_common_check_args[@]}"', '"${cxx20_common_check_args_disabled[@]}"'), 'missing profiling compile_commands guard: "${cxx20_common_check_args[@]}"', 'scan-helper'),
            case(lambda repo: replace_profiling_scan_helper_arg(repo, '"${cxx20_clang_check_args[@]}"', '"${cxx20_clang_check_args_disabled[@]}"'), 'missing profiling compile_commands guard: "${cxx20_clang_check_args[@]}"', 'scan-helper'),
            case(lambda repo: replace_text(ensure_cmake4_helper(repo), 'ensure_cmake4() {', 'ensure_cmake4_disabled() {'), 'CMake 4 helper missing detail: ensure_cmake4() {', 'ensure-cmake4-helper'),
            case(lambda repo: replace_text(ensure_linux_sanitizer_toolchain_helper(repo), 'ensure_linux_sanitizer_toolchain() {', 'ensure_linux_sanitizer_toolchain_disabled() {'), 'Linux sanitizer toolchain helper missing detail: ensure_linux_sanitizer_toolchain() {', 'ensure-linux-sanitizer-toolchain-helper'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_pgo_consume "$build_dir" "$pgo_flag" --min-cpp-commands="$min_cpp_commands"', ': # check_cxx20_commands_pgo_consume "$build_dir" "$pgo_flag" --min-cpp-commands="$min_cpp_commands"'), 'missing required Build workflow guard snippet: check_cxx20_commands_pgo_consume "$build_dir" "$pgo_flag" --min-cpp-commands="$min_cpp_commands"', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), 'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'c++ -O2 --std=gnu++20 --std=gnu++17 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o'), 'missing required setup-windows-deps guard snippet: c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), 'git -c core.autocrlf=false reset --hard HEAD\n        git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}', 'git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}'), 'missing required setup-windows-deps guard snippet: git -c core.autocrlf=false reset --hard HEAD', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), 'cp -R ffmpeg-install/include/. /usr/local/include/', 'cp -R ffmpeg-install/include/. /tmp/ffmpeg-include/'), 'missing required setup-windows-deps guard snippet: cp -R ffmpeg-install/include/. /usr/local/include/', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), '        fetch-depth: 1', '        fetch-depth: 0'), 'Checkout FFmpeg must use fetch-depth: 1', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), "  use-ffmpeg:\n    description: Whether to build and install FFmpeg\n    required: false\n    default: 'true'\n", ''), 'setup-windows-deps action must define input: use-ffmpeg', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), "  use-obuparse:\n    description: Whether to build and install obuparse\n    required: false\n    default: 'true'\n", ''), 'setup-windows-deps action must define input: use-obuparse', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), "  use-lsmash:\n    description: Whether to build and install L-SMASH\n    required: false\n    default: 'true'\n", ''), 'setup-windows-deps action must define input: use-lsmash', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), '        sparse-checkout: |\n          Makefile\n          obuparse.c\n          obuparse.h\n        sparse-checkout-cone-mode: false', '        sparse-checkout: Makefile\n        sparse-checkout-cone-mode: false', count=1), 'Checkout Obuparse must sparse-checkout only the static library build inputs', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), '        sparse-checkout: |\n          Makefile\n          configure\n          lsmash.h\n          liblsmash.v\n          cli\n          codecs\n          common\n          core\n          importer', '        sparse-checkout: .', count=1), 'Checkout L-SMASH must sparse-checkout only configure and static-library source inputs', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), '        sparse-checkout-cone-mode: false\n\n    - name: Checkout GOP muxer', '\n    - name: Checkout GOP muxer', count=1), 'Checkout L-SMASH must disable sparse-checkout cone mode for mixed file/directory checkout', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), '        sparse-checkout: gop_muxer.cpp', '        sparse-checkout: .'), 'Checkout GOP muxer must sparse-checkout only gop_muxer.cpp', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), '          mingw-w64-clang-x86_64-python\n', ''), 'Setup Windows dependencies must install CLANG64 Python for C++20 guard helpers', 'windows-deps-checkout-scope'),
            case(lambda repo: replace_text(windows_deps_action(repo), '          base-devel', '          p7zip\n          base-devel'), 'Setup Windows dependencies must not install p7zip globally; package steps install it on demand', 'windows-deps-checkout-scope'),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/threadpool.cpp'),
                    '\n'.join((
                        'm_workers = X265_MALLOC(WorkerThread, numThreads);',
                        'm_jpTable = X265_MALLOC(JobProvider*, maxProviders);',
                        'return m_workers && m_jpTable;',
                    )) + '\n',
                ),
                'forbidden threadpool create rollback regression',
                'threadpool-create-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/threadpool.cpp'),
                    '\n'.join((
                        'bool ThreadPool::start()',
                        '{',
                        '    if (!m_workers[i].start())',
                        '        return false;',
                        '}',
                    )) + '\n',
                ),
                'missing threadpool start rollback guardrail',
                'threadpool-start-rollback',
            ),
            case(
                lambda repo: (
                    write_repo_file(repo, Path('source/common/wavefront.cpp'), 'return m_internalDependencyBitmap && m_externalDependencyBitmap;\n'),
                    write_repo_file(repo, Path('source/common/wavefront.h'), 'void releaseState();\n'),
                ),
                'forbidden WaveFront init rollback regression',
                'wavefront-init-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/framedata.cpp'),
                    '\n'.join((
                        'm_slice  = new Slice;',
                        'm_picCTU = new CUData[sps.numCUsInFrame];',
                        'else',
                        '        return false;',
                        'X265_FREE(m_slice->m_ctuMV);',
                    )) + '\n',
                ),
                'forbidden FrameData create rollback regression',
                'framedata-create-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/slicetype.cpp'),
                    '\n'.join((
                        '#include <new>',
                        'Lookahead::Lookahead(x265_param *param, ThreadPool* pool)',
                        '{',
                        '    m_metld = nullptr;',
                        '    m_accHistDiffRunningAvgCb = nullptr;',
                        '    m_accHistDiffRunningAvgCr = nullptr;',
                        '    m_accHistDiffRunningAvg = nullptr;',
                        '    m_accHistDiffRunningAvgCb = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);',
                        '    if (m_accHistDiffRunningAvgCb)',
                        '    {',
                        '        m_accHistDiffRunningAvgCb[0] = X265_MALLOC(uint32_t, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
                        '        if (m_accHistDiffRunningAvgCb[0])',
                        '        {',
                        '            std::fill_n(m_accHistDiffRunningAvgCb[0], NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT, uint32_t(0));',
                        '        }',
                        '    }',
                        '    m_accHistDiffRunningAvgCr = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);',
                        '    if (m_accHistDiffRunningAvgCr)',
                        '    {',
                        '        m_accHistDiffRunningAvgCr[0] = X265_MALLOC(uint32_t, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
                        '        if (m_accHistDiffRunningAvgCr[0])',
                        '        {',
                        '            std::fill_n(m_accHistDiffRunningAvgCr[0], NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT, uint32_t(0));',
                        '            for (uint32_t w = 1; w < NUMBER_OF_SEGMENTS_IN_WIDTH; w++)',
                        '                m_accHistDiffRunningAvgCr[w] = m_accHistDiffRunningAvgCr[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
                        '        }',
                        '    }',
                        '    m_accHistDiffRunningAvg = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);',
                        '    if (m_accHistDiffRunningAvg)',
                        '    {',
                        '        m_accHistDiffRunningAvg[0] = X265_MALLOC(uint32_t, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
                        '        if (m_accHistDiffRunningAvg[0])',
                        '        {',
                        '            std::fill_n(m_accHistDiffRunningAvg[0], NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT, uint32_t(0));',
                        '            for (uint32_t w = 1; w < NUMBER_OF_SEGMENTS_IN_WIDTH; w++)',
                        '                m_accHistDiffRunningAvg[w] = m_accHistDiffRunningAvg[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
                        '        }',
                        '    }',
                        '}',
                        'bool Lookahead::create()',
                        '{',
                        '    if (!m_accHistDiffRunningAvgCb || !m_accHistDiffRunningAvgCb[0] ||',
                        '        !m_accHistDiffRunningAvgCr || !m_accHistDiffRunningAvgCr[0] ||',
                        '        !m_accHistDiffRunningAvg || !m_accHistDiffRunningAvg[0])',
                        '    {',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead histogram buffers\\n");',
                        '        return false;',
                        '    }',
                        '    int numTLD = 1;',
                        '    LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];',
                        '    int* scratch = nullptr;',
                        '    MotionEstimatorTLD* metld = nullptr;',
                        '    OrigPicBuffer* origPicBuf = nullptr;',
                        '    if (!tld)',
                        '    {',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead thread-local data\\n");',
                        '        return false;',
                        '    }',
                        '    scratch = X265_MALLOC(int, tld[0].widthInCU);',
                        '    if (!scratch)',
                        '    {',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead scratch buffer\\n");',
                        '        goto fail;',
                        '    }',
                        '    metld = new (std::nothrow) MotionEstimatorTLD[numTLD];',
                        '    if (!metld)',
                        '    {',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead motion-estimator buffers\\n");',
                        '        goto fail;',
                        '    }',
                        '    origPicBuf = new (std::nothrow) OrigPicBuffer();',
                        '    if (!origPicBuf)',
                        '    {',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead original-picture buffer\\n");',
                        '        goto fail;',
                        '    }',
                        '    m_tld = tld;',
                        '    m_scratch = scratch;',
                        '    m_metld = metld;',
                        '    m_origPicBuf = origPicBuf;',
                        '    return true;',
                        'fail:',
                        '    delete origPicBuf;',
                        '    delete[] metld;',
                        '    X265_FREE(scratch);',
                        '    delete[] tld;',
                        '    return false;',
                        '}',
                        'void Lookahead::destroy()',
                        '{',
                        '    if (m_accHistDiffRunningAvgCb)',
                        '        X265_FREE(m_accHistDiffRunningAvgCb[0]);',
                        '    if (m_accHistDiffRunningAvgCr)',
                        '        X265_FREE(m_accHistDiffRunningAvgCr[0]);',
                        '    if (m_accHistDiffRunningAvg)',
                        '        X265_FREE(m_accHistDiffRunningAvg[0]);',
                        '}',
                    )) + '\n',
                ),
                'missing lookahead allocation guardrail: m_accHistDiffRunningAvgCb[w] = m_accHistDiffRunningAvgCb[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
                'lookahead-alloc-guards',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/encoder/frameencoder.cpp'),
                        '\n'.join((
                            '#include <new>',
                            'FrameEncoder::FrameEncoder()',
                            '{',
                            '    m_sliceBaseRow = nullptr;',
                            '    m_sliceMaxBlockRow = nullptr;',
                            '    m_retFrameBuffer = nullptr;',
                            '}',
                            'void FrameEncoder::destroy()',
                            '{',
                            '    if (m_tld)',
                            '    {',
                            '    }',
                            '    if (m_param && (m_param->bEmitHRDSEI || m_param->interlaceMode != 0))',
                            '    {',
                            '    }',
                            '}',
                            'bool FrameEncoder::init(Encoder *top, int numRows, int numCols)',
                            '{',
                            '    m_rows = new CTURow[m_numRows];',
                            '    if (!m_rows)',
                            '    {',
                            '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder row state\\n");',
                            '        return false;',
                            '    }',
                            '    m_sliceBaseRow = X265_MALLOC(uint32_t, m_param->maxSlices + 1);',
                            '    m_bAllRowsStop = new (std::nothrow) std::atomic<bool>[m_param->maxSlices];',
                            '    m_vbvResetTriggerRow = new (std::nothrow) std::atomic<int>[m_param->maxSlices];',
                            '    if (!m_sliceBaseRow || !m_bAllRowsStop || !m_vbvResetTriggerRow)',
                            '    {',
                            '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder slice state\\n");',
                            '        return false;',
                            '    }',
                            '    m_sliceMaxBlockRow = X265_MALLOC(uint32_t, m_param->maxSlices + 1);',
                            '    if (!m_sliceMaxBlockRow)',
                            '    {',
                            '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder block-row state\\n");',
                            '        return false;',
                            '    }',
                            '    m_frameFilter.init(top, this, numRows, numCols);',
                            '    if (!m_frameFilter.m_parallelFilter)',
                            '    {',
                            '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder parallel filter state\\n");',
                            '        return false;',
                            '    }',
                            '    m_rce.picTimingSEI = new (std::nothrow) SEIPictureTiming;',
                            '    m_rce.hrdTiming = new (std::nothrow) HRDTiming;',
                            '    if (!m_rce.picTimingSEI || !m_rce.hrdTiming)',
                            '    {',
                            '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder HRD timing state\\n");',
                            '        return false;',
                            '    }',
                            '    m_retFrameBuffer = X265_MALLOC(Frame*, m_param->numLayers);',
                            '    if (!m_retFrameBuffer)',
                            '    {',
                            '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder return buffer\\n");',
                            '        return false;',
                            '    }',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/encoder/framefilter.cpp'),
                        '\n'.join((
                            '#include <new>',
                            'void FrameFilter::init(Encoder *top, FrameEncoder *frame, int numRows, uint32_t numCols)',
                            '{',
                            '    m_parallelFilter = new (std::nothrow) ParallelFilter[numRows];',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/encoder/encoder.cpp'),
                        '\n'.join((
                            'void Encoder::create()',
                            '{',
                            'int numRows = (m_param->sourceHeight + m_param->maxCUSize - 1) / m_param->maxCUSize;',
                            'int numCols = (m_param->sourceWidth  + m_param->maxCUSize - 1) / m_param->maxCUSize;',
                            'for (int i = 0; i < m_param->frameNumThreads; i++)',
                            '{',
                            '    if (!m_frameEncoder[i]->init(this, numRows, numCols))',
                            '    {',
                            '        x265_log(m_param, X265_LOG_ERROR, "Unable to initialize frame encoder, aborting\\n");',
                            '        m_aborted = true;',
                            '        break;',
                            '    }',
                            '}',
                            'for (int i = 0; i < m_param->frameNumThreads; i++)',
                            '{',
                            '    if (!m_frameEncoder[i]->start())',
                            '    {',
                            '    }',
                            '}',
                            '}',
                        )) + '\n',
                    ),
                ),
                'missing frame encoder init alloc guardrail: if (m_aborted)',
                'frameencoder-init-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/bitcost.cpp'),
                    '\n'.join((
                        'void BitCost::setQP(unsigned int qp)',
                        '{',
                        '    CalculateLogs();',
                        '    uint16_t* costs = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1);',
                        '    if (!costs)',
                        '    {',
                        '        x265_log(nullptr, X265_LOG_ERROR, "BitCost s_costs buffer allocation failure\\n");',
                        '        return;',
                        '    }',
                        '    s_costs[qp] = costs + 2 * BC_MAX_MV;',
                        '    uint16_t* fpelMvCosts = X265_MALLOC(uint16_t, BC_MAX_MV + 1);',
                        '    if (!fpelMvCosts)',
                        '    {',
                        '        x265_log(nullptr, X265_LOG_ERROR, "BitCost s_fpelMvCosts buffer allocation failure\\n");',
                        '        return;',
                        '    }',
                        '    s_fpelMvCosts[qp][j] = fpelMvCosts + (BC_MAX_MV >> 1);',
                        '}',
                        'void BitCost::CalculateLogs()',
                        '{',
                        '    float* bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1);',
                        '    if (!bitsizes)',
                        '    {',
                        '        x265_log(nullptr, X265_LOG_ERROR, "BitCost s_bitsizes buffer allocation failure\\n");',
                        '        return;',
                        '    }',
                        '    s_bitsizes = bitsizes + 2 * BC_MAX_MV;',
                        '}',
                    )) + '\n',
                ),
                'missing BitCost allocation guardrail: if (!s_bitsizes)',
                'bitcost-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/scaler.cpp'),
                    '\n'.join((
                        'int ScalerFilterManager::init(int algorithmFlags, VideoDesc *srcVideoDesc, VideoDesc *dstVideoDesc)',
                        '{',
                        '    if (x265_cli_csps[srcCsp].planes <= 1)',
                        '    {',
                        '        x265_log(nullptr, X265_LOG_ERROR, "scaler: monochrome ABR ladder scaling is unsupported\\n");',
                        '        return -1;',
                        '    }',
                        '    crXInc = (((int64_t)m_crSrcW << 16) + (m_crDstW >> 1)) / m_crDstW;',
                        '    crYInc = (((int64_t)m_crSrcH << 16) + (m_crDstH >> 1)) / m_crDstH;',
                        '}',
                    )) + '\n',
                ),
                'missing scaler chroma-dimension guardrail: if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)',
                'scaler-chroma-dims-guard',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/encoder/encoder.cpp'),
                        '\n'.join((
                            'void Encoder::copyUserSEIMessages(Frame *frame, const x265_picture* pic_in)',
                            '{',
                            '    x265_sei_payload toneMap = {};',
                            '    toneMap.payloadType = USER_DATA_REGISTERED_ITU_T_T35;',
                            '    const int toneMapMetadataBytes = 509;',
                            '    if (currentPOC >= 0 && currentPOC < m_numCimInfo && m_cim && m_cim[currentPOC])',
                            '    {',
                            '        while (m_cim[currentPOC][i] == 0xFF)',
                            '        {',
                            '            if (payloadSize > INT_MAX - 0xFF)',
                            '            {',
                            '                payloadSize = -1;',
                            '                break;',
                            '            }',
                            '            payloadSize += 0xFF;',
                            '            payloadPrefixBytes++;',
                            '        }',
                            '        if (payloadPrefixBytes >= toneMapMetadataBytes || payloadSize < 0 ||',
                            '            payloadSize > INT_MAX - m_cim[currentPOC][payloadPrefixBytes])',
                            '        {',
                            '            x265_log(m_param, X265_LOG_ERROR, "Invalid HDR10+ tone-map payload prefix for frame %d\\n", currentPOC);',
                            '        }',
                            '        else if (payloadSize > toneMapMetadataBytes - payloadPrefixBytes - 1)',
                            '        {',
                            '            x265_log(m_param, X265_LOG_ERROR, "HDR10+ tone-map payload exceeds frame metadata buffer for frame %d\\n", currentPOC);',
                            '        }',
                            '        else if (payloadSize > 0)',
                            '        {',
                            '            uint8_t* stagedToneMapPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payloadSize);',
                            '            if (!stagedToneMapPayload)',
                            '                x265_log(m_param, X265_LOG_ERROR, "Unable to allocate HDR10+ tone-map payload buffer\\n");',
                            '            else',
                            '            {',
                            '                toneMap.payload = stagedToneMapPayload;',
                            '                toneMap.payloadSize = payloadSize;',
                            '            }',
                            '        }',
                            '    }',
                            '    for (int i = 0; i < numPayloads; i++)',
                            '    {',
                            '        if (i < pic_in->userSEI.numPayloads)',
                            '            input = pic_in->userSEI.payloads[i];',
                            '        else if (userPayload && i == pic_in->userSEI.numPayloads)',
                            '            input = seiMsg;',
                            '        else',
                            '            input = toneMap;',
                            '    }',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/encoder/frameencoder.cpp'),
                        '\n'.join((
                            'bool FrameEncoder::writeToneMapInfo(x265_sei_payload *payload)',
                            '{',
                            '    if (payloadChange)',
                            '    {',
                            '        uint8_t* stagedPayload = nullptr;',
                            '        stagedPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payload->payloadSize);',
                            '        if (!stagedPayload)',
                            '        {',
                            '            x265_log(m_param, X265_LOG_ERROR, "Unable to allocate tone-map payload history buffer\\n");',
                            '            return true;',
                            '        }',
                            '        std::memcpy(stagedPayload, payload->payload, payload->payloadSize);',
                            '        x265_free(m_top->m_prevTonemapPayload.payload);',
                            '        m_top->m_prevTonemapPayload.payload = stagedPayload;',
                            '    }',
                            '}',
                        )) + '\n',
                    ),
                ),
                'forbidden tone-map payload safety regression',
                'tonemap-payload-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/temporalfilter.cpp'),
                    '\n'.join((
                        'int TemporalFilter::createRefPicInfo(TemporalFilterRefPicInfo* refFrame, x265_param* param)',
                        '{',
                        '    CHECKED_MALLOC_ZERO(refFrame->mvs, MV, sizeof(MV)* ((m_sourceWidth ) / 4) * ((m_sourceHeight ) / 4));',
                        '    CHECKED_MALLOC_ZERO(refFrame->mvs0, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
                        '    CHECKED_MALLOC_ZERO(refFrame->mvs1, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
                        '    CHECKED_MALLOC_ZERO(refFrame->mvs2, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
                        '    CHECKED_MALLOC_ZERO(refFrame->noise, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
                        '    CHECKED_MALLOC_ZERO(refFrame->error, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
                        '}',
                    )) + '\n',
                ),
                'forbidden temporalfilter allocation-count regression',
                'temporalfilter-alloc-counts',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/frameencoder.cpp'),
                    '\n'.join((
                        'if (!m_outStreams)',
                        '{',
                        '    m_outStreams = new Bitstream[numSubstreams];',
                        '    if (!stagedOutStreams)',
                        '    {',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder substream bitstreams\\n");',
                        '        m_top->m_aborted = true;',
                        '        return;',
                        '    }',
                        '    Bitstream* stagedBackupStreams = nullptr;',
                        '    stagedBackupStreams = new (std::nothrow) Bitstream[numSubstreams];',
                        '    if (!stagedBackupStreams)',
                        '    {',
                        '        delete[] stagedOutStreams;',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder backup substream bitstreams\\n");',
                        '        m_top->m_aborted = true;',
                        '        return;',
                        '    }',
                        '    uint32_t* stagedSubstreamSizes = X265_MALLOC(uint32_t, numSubstreams);',
                        '    if (!stagedSubstreamSizes)',
                        '    {',
                        '        delete[] stagedOutStreams;',
                        '        delete[] stagedBackupStreams;',
                        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder substream size table\\n");',
                        '        m_top->m_aborted = true;',
                        '        return;',
                        '    }',
                        '    m_outStreams = stagedOutStreams;',
                        '    m_backupStreams = stagedBackupStreams;',
                        '    m_substreamSizes = stagedSubstreamSizes;',
                        '}',
                    )) + '\n',
                ),
                'forbidden frameencoder substream allocation regression',
                'frameencoder-substream-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/frameencoder.cpp'),
                    '\n'.join((
                        'bool FrameEncoder::initializeGeoms()',
                        '{',
                        '    m_ctuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);',
                        '    CUGeom* stagedCuGeoms = X265_MALLOC(CUGeom, allocGeoms * CUGeom::MAX_GEOMS);',
                        '    if (!stagedCuGeoms || !m_ctuGeomMap)',
                        '        return false;',
                        '    CUData::calcCTUGeoms(maxCUSize, maxCUSize, maxCUSize, minCUSize, stagedCuGeoms);',
                        '    std::fill_n(m_ctuGeomMap, m_numRows * m_numCols, uint32_t(0));',
                        '    m_cuGeoms = stagedCuGeoms;',
                        '    return true;',
                        '}',
                    )) + '\n',
                ),
                'forbidden frameencoder initializeGeoms staging regression: m_ctuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);',
                'frameencoder-initialize-geoms-staging',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/frame.cpp'),
                    '\n'.join((
                        '#include <new>',
                        'bool Frame::createSubSample()',
                        '{',
                        '    m_fencPicSubsampled2 = new PicYuv;',
                        '    PicYuv* stagedFencPicSubsampled4 = new (std::nothrow) PicYuv;',
                        '    int* stagedIsSubSampled = nullptr;',
                        '    if (!m_fencPicSubsampled2 || !stagedFencPicSubsampled4)',
                        '        return false;',
                        '    CHECKED_MALLOC_ZERO(stagedIsSubSampled, int, 1);',
                        '    m_fencPicSubsampled4 = stagedFencPicSubsampled4;',
                        '    m_isSubSampled = stagedIsSubSampled;',
                        '    return true;',
                        '}',
                    )) + '\n',
                ),
                'forbidden frame createSubSample staging regression: m_fencPicSubsampled2 = new PicYuv;',
                'frame-create-subsample-staging',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/frame.cpp'),
                    '\n'.join((
                        'bool Frame::create(x265_param *param, float* quantOffsets)',
                        '{',
                        '    m_reconRowFlag = new ThreadSafeInteger[m_numRows];',
                        '    ThreadSafeInteger* stagedReconColCount = new (std::nothrow) ThreadSafeInteger[m_numRows];',
                        '    ThreadSafeInteger* stagedCtuMEFlags = new (std::nothrow) ThreadSafeInteger[m_numRows * m_numCols];',
                        '    float* stagedQuantOffsets = nullptr;',
                        '    stagedQuantOffsets = new (std::nothrow) float[cuCount];',
                        '    if (!m_reconRowFlag || !stagedReconColCount || !stagedCtuMEFlags || (quantOffsets && !stagedQuantOffsets))',
                        '        return false;',
                        '    m_reconColCount = stagedReconColCount;',
                        '    m_ctuMEFlags = stagedCtuMEFlags;',
                        '    m_quantOffsets = stagedQuantOffsets;',
                        '    return true;',
                        '}',
                    )) + '\n',
                ),
                'forbidden frame create row-state allocation regression: m_reconRowFlag = new ThreadSafeInteger[m_numRows];',
                'frame-create-rowstate-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/frame.cpp'),
                    '\n'.join((
                        'bool Frame::create(x265_param *param, float* quantOffsets)',
                        '{',
                        '    for (int i = 0; i < (m_mcstf->m_range << 1); i++)',
                        '    {',
                        '        m_mcstf->createRefPicInfo(&m_mcstfRefList[i], m_param);',
                        '    }',
                        '    return true;',
                        '}',
                    )) + '\n',
                ),
                'forbidden frame create MCSTF refpic regression: ignored createRefPicInfo() result',
                'frame-create-mcstf-refpic-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/frame.cpp'),
                    '\n'.join((
                        'bool Frame::create(x265_param *param, float* quantOffsets)',
                        '{',
                        '    if (m_param->bEnableTemporalFilter)',
                        '    {',
                        '        m_mcstffencPic->create(param, m_param->bCopyPicToFrame != 0);',
                        '    }',
                        '    return true;',
                        '}',
                    )) + '\n',
                ),
                'forbidden frame create MCSTF fenc pic regression: ignored PicYuv::create() result',
                'frame-create-mcstf-fenc-pic-guards',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/common/frame.cpp'),
                        '\n'.join((
                            'bool Frame::allocEncodeData(x265_param *param, const SPS& sps)',
                            '{',
                            '    m_encData = new FrameData;',
                            '    PicYuv* stagedReconPic[NUM_RECON_VERSION] = { nullptr };',
                            '    const bool sccEnabled = param->bEnableSCC != 0;',
                            '    const int reconPicCount = sccEnabled ? 2 : 1;',
                            '    for (int i = 0; i < reconPicCount; i++)',
                            '    {',
                            '        stagedReconPic[i] = new (std::nothrow) PicYuv;',
                            '    }',
                            '    if (!stagedReconPic[0]->create(param))',
                            '        return false;',
                            '    m_encData = stagedEncData;',
                            '    return true;',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/encoder/encoder.cpp'),
                        '\n'.join((
                            'if (!frameEnc[layer]->allocEncodeData(m_reconfigure ? m_latestParam : m_param, m_sps))',
                            '{',
                            '    m_aborted = true;',
                            '    x265_log(m_param, X265_LOG_ERROR, "memory allocation failure, aborting encode\\n");',
                            '    return -1;',
                            '}',
                            'Slice* slice = frameEnc[layer]->m_encData->m_slice;',
                        )) + '\n',
                    ),
                ),
                'forbidden frame allocEncodeData regression: m_encData = new FrameData;',
                'frame-alloc-encode-data-guards',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/common/frame.cpp'),
                        '\n'.join((
                            'Frame::Frame()',
                            '{',
                            '    m_fencPic = nullptr;',
                            '    m_fencPicSubsampled2 = nullptr;',
                            '    m_fencPicSubsampled4 = nullptr;',
                            '    m_mcstffencPic = nullptr;',
                            '}',
                            'bool Frame::create(x265_param *param, float* quantOffsets)',
                            '{',
                            '    m_fencPic = new PicYuv;',
                            '    if (m_param->bEnableTemporalFilter)',
                            '    {',
                            '        m_mcstf = new TemporalFilter;',
                            '        m_mcstffencPic = new PicYuv;',
                            '        m_mcstf->init(param);',
                            '        m_fencPicSubsampled2 = new PicYuv;',
                            '        m_fencPicSubsampled4 = new PicYuv;',
                            '    }',
                            '    return true;',
                            '}',
                            'void Frame::destroy()',
                            '{',
                            '    if (m_param->bEnableTemporalFilter)',
                            '    {',
                            '        delete m_mcstf->m_metld;',
                            '        delete m_mcstf;',
                            '    }',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/common/temporalfilter.cpp'),
                        '\n'.join((
                            'bool TemporalFilter::init(const x265_param* param)',
                            '{',
                            '    m_metld = new MotionEstimatorTLD;',
                            '    return true;',
                            '}',
                        )) + '\n',
                    ),
                ),
                'forbidden frame create top alloc regression: m_fencPic = new PicYuv;',
                'frame-create-top-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'void x265_picture_init(x265_param *param, x265_picture *pic)',
                        '{',
                        '    std::fill_n(reinterpret_cast<uint8_t*>(pic), sizeof(x265_picture), uint8_t(0));',
                        '    pic->bitDepth = param->internalBitDepth;',
                        '}',
                    )) + '\n',
                ),
                'missing x265_picture_init null guardrail: if (!param || !pic)',
                'x265-picture-init-null-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'void x265_param_default(x265_param* param)',
                        '{',
                        '#ifdef SVT_HEVC',
                        '    EB_H265_ENC_CONFIGURATION* svtParam = getSvtHevcParamStorage(param);',
                        '#endif',
                        '    std::fill_n(reinterpret_cast<uint8_t*>(param), sizeof(x265_param), uint8_t(0));',
                        '}',
                    )) + '\n',
                ),
                'missing x265_param_default null guardrail: if (!param)',
                'x265-param-default-null-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'int x265_param_default_preset(x265_param* param, const char* preset, const char* tune)',
                        '{',
                        '#if EXPORT_C_API',
                        '    ::x265_param_default(param);',
                        '#else',
                        '    X265_NS::x265_param_default(param);',
                        '#endif',
                        '}',
                        '#undef atoi',
                    )) + '\n',
                ),
                'missing x265_param_default_preset null guardrail: if (!param)',
                'x265-param-default-preset-null-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'int x265_param_parse(x265_param* p, const char* name, const char* value)',
                        '{',
                        '    if (!name)',
                        '        return X265_PARAM_BAD_NAME;',
                        '    if (p->bEnableSvtHevc)',
                        '    {',
                        '    }',
                        '    p->cpuid = X265_NS::cpu_detect(true);',
                        '}',
                    )) + '\n',
                ),
                'missing x265_param_parse null guardrail: if (!p)\n        return X265_PARAM_BAD_VALUE;',
                'x265-param-parse-null-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'int x265_check_params(x265_param* param)',
                        '{',
                        '#define CHECK(expr, msg) check_failed |= _confirm(param, expr, msg)',
                        '}',
                        'void x265_param_apply_fastfirstpass(x265_param* param)',
                        '{',
                        '    if (param->rc.bStatWrite && !param->rc.bStatRead)',
                        '    {',
                        '    }',
                        '}',
                        'void x265_print_params(x265_param* param)',
                        '{',
                        '    if (param->logLevel < X265_LOG_INFO)',
                        '        return;',
                        '}',
                    )) + '\n',
                ),
                'missing x265_check_params null guardrail: if (!param)',
                'param-api-null-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)',
                        '{',
                        '    if (!name)',
                        '        return X265_PARAM_BAD_NAME;',
                        '    p->bEnableSceneCutAwareQp = sceneCutAwareQp;',
                        '}',
                        'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
                        '{',
                        '    if (!name)',
                        '        return X265_PARAM_BAD_NAME;',
                        '    p->maxNumReferences = maxNumReferences;',
                        '}',
                    )) + '\n',
                ),
                'missing x265_scenecut_aware_qp_param_parse null guardrail: if (!p)\n        return X265_PARAM_BAD_VALUE;',
                'zone-scenecut-param-parse-null-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'void x265_alloc_analysis_data(x265_param *param, x265_analysis_data* analysis)',
                        '{',
                        '    x265_analysis_inter_data *interData = analysis->interData = nullptr;',
                        '}',
                        'void x265_free_analysis_data(x265_param *param, x265_analysis_data* analysis)',
                        '{',
                        '    int maxReuseLevel = X265_MAX(param->analysisSaveReuseLevel, param->analysisLoadReuseLevel);',
                        '}',
                    )) + '\n',
                ),
                'missing x265_alloc_analysis_data null guardrail: if (!param || !analysis)',
                'analysis-data-api-null-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'int x265_get_slicetype_poc_and_scenecut(x265_encoder *enc, int *slicetype, int *poc, int *sceneCut)',
                        '{',
                        '    if (!enc)',
                        '        return -1;',
                        '    if (!encoder->copySlicetypePocAndSceneCut(slicetype, poc, sceneCut, 0))',
                        '        return 0;',
                        '    return -1;',
                        '}',
                        'int x265_get_ref_frame_list(x265_encoder *enc, x265_picyuv** l0, x265_picyuv** l1, int sliceType, int poc, int* pocL0, int* pocL1)',
                        '{',
                        '    if (!enc)',
                        '        return -1;',
                        '    return encoder->getRefFrameList((PicYuv**)l0, (PicYuv**)l1, sliceType, poc, pocL0, pocL1);',
                        '}',
                    )) + '\n',
                ),
                'missing x265_get_slicetype_poc_and_scenecut output null guardrail: if (!enc || !slicetype || !poc || !sceneCut)',
                'query-api-output-null-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'void x265_dither_image(x265_picture* picIn, int picWidth, int picHeight, int16_t *errorBuf, int bitDepth)',
                        '{',
                        '    const x265_api* api = x265_api_get(0);',
                        '    if (sizeof(x265_picture) != api->sizeof_picture)',
                        '    {',
                        '        return;',
                        '    }',
                        '}',
                    )) + '\n',
                ),
                'missing x265_dither_image null guardrail: if (!picIn || !errorBuf)',
                'x265-dither-image-null-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'FILE* x265_csvlog_open(const x265_param* param)',
                        '{',
                        '    FILE *csvfp = x265_fopen(param->csvfn, "r");',
                        '}',
                        'void x265_csvlog_frame(const x265_param* param, const x265_picture* pic)',
                        '{',
                        '    if (!param->csvfpt)',
                        '        return;',
                        '    const x265_frame_stats* frameStats = &pic->frameData;',
                        '}',
                        'void x265_csvlog_encode(const x265_param *p, const x265_stats *stats, int padx, int pady, int argc, char** argv)',
                        '{',
                        '    if (!p->csvfpt)',
                        '        return;',
                        '    const x265_api * api = x265_api_get(0);',
                        '    if (argc)',
                        '        fputs(argv[i], p->csvfpt);',
                        '    fprintf(p->csvfpt, "%.2f,", stats->elapsedEncodeTime);',
                        '    fprintf(p->csvfpt, " %s\\n", api->version_str);',
                        '}',
                    )) + '\n',
                ),
                'missing x265_csvlog_open null guardrail: if (!param)',
                'csvlog-api-null-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'void x265_vmaf_encoder_log(x265_encoder* enc, int argc, char **argv, x265_param *param, x265_vmaf_data *vmafdata)',
                        '{',
                        '    Encoder *encoder = static_cast<Encoder*>(enc);',
                        '}',
                        'double x265_calculate_vmafscore(x265_param *param, x265_vmaf_data *data)',
                        '{',
                        '    data->width = param->sourceWidth;',
                        '}',
                        'double x265_calculate_vmaf_framelevelscore(x265_param *param, x265_vmaf_framedata *vmafframedata)',
                        '{',
                        '    if (param->internalCsp == X265_CSP_I420)',
                        '        return 0.0;',
                        '}',
                    )) + '\n',
                ),
                'missing x265_vmaf_encoder_log null guardrail: if (!enc || !param || !vmafdata)',
                'vmaf-api-null-guards',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/encoder/threadedme.cpp'),
                        '\n'.join((
                            'bool ThreadedME::create()',
                            '{',
                            '    m_tld = new ThreadLocalData[m_tldCount];',
                            '    if (!m_tld[i].analysis.create(m_tld))',
                            '        return false;',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/encoder/encoder.cpp'),
                        '\n'.join((
                            'if (!m_threadedME->create())',
                            '{',
                            '    X265_FREE(m_threadedME);',
                            '    m_threadedME = nullptr;',
                            '}',
                        )) + '\n',
                    ),
                ),
                'missing ThreadedME create guardrail: m_tld = new (std::nothrow) ThreadLocalData[m_tldCount];',
                'threadedme-create-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/threadpool.cpp'),
                    '\n'.join((
                        'ThreadPool* ThreadPool::allocThreadPools(x265_param* p, int& numPools, bool isThreadsReserved)',
                        '{',
                        '    for (int i = 0; i < numNumaNodes; i++)',
                        '    {',
                        '        PGROUP_AFFINITY groupAffinityPointer = new GROUP_AFFINITY;',
                        '        GetNumaNodeProcessorMaskEx((UCHAR)i, groupAffinityPointer);',
                        '        cpusPerNode[i] = popCount(groupAffinityPointer->Mask);',
                        '    }',
                        '}',
                        'int ThreadPool::getCpuCount()',
                        '{',
                        '    int cpus = 0;',
                        '    for (int i = 0; i < numNumaNodes; i++)',
                        '    {',
                        '        GROUP_AFFINITY groupAffinity;',
                        '        GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity);',
                        '        cpus += popCount(groupAffinity.Mask);',
                        '    }',
                        '    return cpus;',
                        '}',
                    )) + '\n',
                ),
                'forbidden threadpool Windows NUMA affinity regression: PGROUP_AFFINITY groupAffinityPointer = new GROUP_AFFINITY;',
                'threadpool-windows-numa-affinity-guard',
            ),
            case(
                lambda repo: (
                    write_repo_file(repo, Path('source/common/frame.h'), 'x265_ctu_info_t**      m_ctuInfo;\n'),
                    write_repo_file(repo, Path('source/common/frame.cpp'), 'X265_FREE((*m_ctuInfo + i)->ctuInfo);\nX265_FREE(*m_ctuInfo);\n'),
                    write_repo_file(repo, Path('source/encoder/dpb.cpp'), 'X265_FREE((*curFrame->m_ctuInfo + i)->ctuInfo);\nX265_FREE(*curFrame->m_ctuInfo);\n'),
                    write_repo_file(repo, Path('source/encoder/analysis.cpp'), '\n'.join((
                        'void Analysis::compressCTU(CUData& ctu, FrameData& frame, const CUGeom& cuGeom, int32_t qp)',
                        '{',
                        '    if (m_param->bCTUInfo && m_frame->m_ctuInfo && m_frame->m_ctuInfo[ctu.m_cuAddr])',
                        '    {',
                        '        x265_ctu_info_t* ctuTemp = m_frame->m_ctuInfo[ctu.m_cuAddr];',
                        '    }',
                        '}',
                    )) + '\n'),
                    write_repo_file(repo, Path('source/encoder/encoder.h'), 'void copyCtuInfo(x265_ctu_info_t** frameCtuInfo, int poc);\n'),
                    write_repo_file(repo, Path('source/encoder/encoder.cpp'), '\n'.join((
                        'bool Encoder::copyCtuInfo(x265_ctu_info_t *const* frameCtuInfo, int poc)',
                        '{',
                        '    CHECKED_MALLOC(curFrame->m_ctuInfo, x265_ctu_info_t*, 1);',
                        '    CHECKED_MALLOC(*curFrame->m_ctuInfo, x265_ctu_info_t, numCUsInFrame);',
                        '    ctuTemp = *curFrame->m_ctuInfo + i;',
                        '    prevCtuTemp = *prevFrame->m_ctuInfo + i;',
                        '    X265_FREE((*curFrame->m_ctuInfo + i)->ctuInfo);',
                        '}',
                    )) + '\n'),
                    write_repo_file(repo, Path('source/encoder/api.cpp'), '\n'.join((
                        'int x265_encoder_ctu_info(x265_encoder *enc, int poc, x265_ctu_info_t** ctu)',
                        '{',
                        '    if (!ctu || !enc)',
                        '        return -1;',
                        '    Encoder* encoder = static_cast<Encoder*>(enc);',
                        '    encoder->copyCtuInfo(ctu, poc);',
                        '    return 0;',
                        '}',
                    )) + '\n'),
                ),
                'forbidden Frame CTU-info storage regression: x265_ctu_info_t**      m_ctuInfo;',
                'encoder-ctu-info-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'x265_encoder *x265_encoder_open(x265_param *p)',
                        '{',
                        '    Encoder* encoder = new Encoder;',
                        '    encoder->m_paramBase[0] = PARAM_NS::x265_param_alloc();',
                        '}',
                    )) + '\n',
                ),
                'missing x265_encoder_open allocation guardrail: Encoder* encoder = new (std::nothrow) Encoder;',
                'encoder-open-alloc-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/encoder.cpp'),
                    '\n'.join((
                        'for (int i = 0; i < m_param->frameNumThreads; i++)',
                        '{',
                        '    m_frameEncoder[i] = new FrameEncoder;',
                        '    m_frameEncoder[i]->m_nalList.m_annexB = m_param->bAnnexB != 0;',
                        '}',
                        'if (p->bThreadedME)',
                        '{',
                        '    m_threadedME = new ThreadedME(m_param, *this);',
                        '}',
                    )) + '\n',
                ),
                'forbidden encoder create object alloc regression: m_frameEncoder[i] = new FrameEncoder;',
                'encoder-create-object-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/encoder.cpp'),
                    '\n'.join((
                        'm_lookahead = new Lookahead(m_param, lookAheadThreadPool);',
                        'm_dpb = new DPB(m_param);',
                        'm_rateControl = new RateControl(*m_param, this);',
                        'zoneReadCount = new ThreadSafeInteger[m_param->rc.zonefileCount];',
                        'zoneWriteCount = new ThreadSafeInteger[m_param->rc.zonefileCount];',
                    )) + '\n',
                ),
                'forbidden encoder create core alloc regression: m_lookahead = new Lookahead(m_param, lookAheadThreadPool);',
                'encoder-create-core-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/encoder.cpp'),
                    '\n'.join((
                        'inFrame[layer] = new Frame;',
                        'Frame* dupFrame = new Frame;',
                    )) + '\n',
                ),
                'forbidden encoder encode frame alloc regression: inFrame[layer] = new Frame;',
                'encoder-encode-frame-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/encoder.cpp'),
                    '\n'.join((
                        'Frame* inFrame[MAX_LAYERS];',
                        'if (!copyPicture(m_dupBuffer[0]->dupPic, m_dupBuffer[1]->dupPic))',
                        '    return -1;',
                        'm_lookahead->m_origPicBuf->addEncPicture(dupFrame);',
                    )) + '\n',
                ),
                'missing encoder encode setup rollback guardrail: Frame* inFrame[MAX_LAYERS] = {};',
                'encoder-encode-setup-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/lowres.cpp'),
                    '\n'.join((
                        'pAQLayer = new PicQPAdaptationLayer[4];',
                        'pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight);',
                        'if (maxAQDepth > 0)',
                    )) + '\n',
                ),
                'forbidden lowres AQ-layer regression: pAQLayer = new PicQPAdaptationLayer[4];',
                'lowres-aqlayer-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/lowres.cpp'),
                    '\n'.join((
                        'picHistogram = X265_MALLOC(uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);',
                        'picHistogram[0] = X265_MALLOC(uint32_t**, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
                        'picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex] = X265_MALLOC(uint32_t*, histogramPlanes);',
                        'picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0] = X265_MALLOC(uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);',
                    )) + '\n',
                ),
                'missing lowres histogram allocation guardrail: CHECKED_MALLOC_ZERO(picHistogram, uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);',
                'lowres-histogram-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/frame.cpp'),
                    '\n'.join((
                        'm_edgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
                        'm_gaussianPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
                        'm_thetaPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
                    )) + '\n',
                ),
                'missing frame edge-AQ allocation guardrail: pixel* stagedEdgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
                'frame-edge-aq-alloc-guards',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/encoder/ratecontrol.cpp'),
                        '\n'.join((
                            'm_cutreeShrMem = new RingMem();',
                            'if (!m_cutreeShrMem)',
                            '    return false;',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/common/ringmem.cpp'),
                        '\n'.join((
                            'm_writeSem = new NamedSemaphore();',
                            'm_readSem = new NamedSemaphore();',
                        )) + '\n',
                    ),
                ),
                'forbidden CUTree shared-memory allocation regression: m_cutreeShrMem = new RingMem();',
                'cutree-sharedmem-alloc-guards',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/common/scaler.h'),
                        '\n'.join((
                            'ScalerHLumFilter(int bitDepth) { bitDepth == 8 ? m_hFilterScaler = new HFilterScaler8Bit : bitDepth == 10 ? m_hFilterScaler = new HFilterScaler10Bit : nullptr;}',
                            'ScalerVLumFilter(int bitDepth) { bitDepth == 8 ? m_vFilterScaler = new VFilterScaler8Bit : bitDepth == 10 ? m_vFilterScaler = new VFilterScaler10Bit : nullptr;}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/common/scaler.cpp'),
                        '\n'.join((
                            'if (!m_ScalerFilters[0] || m_ScalerFilters[0]->initCoeff(...) < 0)',
                            'if (!m_ScalerFilters[2] || m_ScalerFilters[2]->initCoeff(...) < 0)',
                        )) + '\n',
                    ),
                ),
                'forbidden scaler helper allocation regression: ScalerHLumFilter(int bitDepth) { bitDepth == 8 ? m_hFilterScaler = new HFilterScaler8Bit : bitDepth == 10 ? m_hFilterScaler = new HFilterScaler10Bit : nullptr;}',
                'scaler-helper-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/slicetype.cpp'),
                    '\n'.join((
                        'int* scratch = nullptr;',
                        'MotionEstimatorTLD* metld = nullptr;',
                        'OrigPicBuffer* origPicBuf = nullptr;',
                        'if (!scratch)',
                        '{',
                        '    return false;',
                        '}',
                        'if (!metld)',
                        '{',
                        '    return false;',
                        '}',
                        'if (!origPicBuf)',
                        '{',
                        '    return false;',
                        '}',
                    )) + '\n',
                ),
                'missing lookahead create rollback guardrail: goto fail;',
                'lookahead-create-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/slicetype.cpp'),
                    '\n'.join((
                        'LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];',
                        'if (!tld)',
                        '{',
                        '    return false;',
                        '}',
                        'scratch = X265_MALLOC(int, tld[0].widthInCU);',
                        'metld = new (std::nothrow) MotionEstimatorTLD[numTLD];',
                        'm_tld = tld;',
                        'm_scratch = scratch;',
                        'm_metld = metld;',
                        'm_origPicBuf = origPicBuf;',
                    )) + '\n',
                ),
                'missing lookahead TLD YUV guardrail: inline bool hasLookaheadTLDYuvBuffers(LookaheadTLD* tld, int numTLD)',
                'lookahead-tld-yuv-guards',
            ),
            case(
                lambda repo: (
                    write_repo_file(repo, Path('source/common/framedata.h'), 'void destroySEAIntegralBuffers();\n'),
                    write_repo_file(
                        repo,
                        Path('source/common/framedata.cpp'),
                        '\n'.join((
                            'void FrameData::destroySEAIntegralBuffers()',
                            '{',
                            '    X265_FREE(m_meIntegral[i]);',
                            '}',
                            'void FrameData::destroy()',
                            '{',
                            '    destroySEAIntegralBuffers();',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(repo, Path('source/encoder/dpb.cpp'), 'curFrame->m_encData->destroySEAIntegralBuffers();\n'),
                    write_repo_file(
                        repo,
                        Path('source/encoder/encoder.cpp'),
                        '\n'.join((
                            'frameEnc[layer]->m_encData->destroySEAIntegralBuffers();',
                            'for (int i = 0; i < INTEGRAL_PLANE_NUM; i++)',
                            '{',
                            '    frameEnc[layer]->m_encData->m_meBuffer[i] = X265_MALLOC(uint32_t, needed);',
                            '    if (frameEnc[layer]->m_encData->m_meBuffer[i])',
                            '    {',
                            '        continue;',
                            '    }',
                            '    frameEnc[layer]->m_encData->destroySEAIntegralBuffers();',
                            '    m_aborted = true;',
                            '    return -1;',
                            '}',
                        )) + '\n',
                    ),
                ),
                'forbidden SEA integral buffer lifecycle regression: X265_FREE(m_meIntegral[i]);',
                'sea-integral-buffer-lifecycle',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'printf("problem loading model file: %s\\n", model_path);',
                        '\t\tgoto end;',
                        'printf("problem loading feature extractors from model file: %s\\n", model_path);',
                        '\t\tgoto end;',
                        'err = load_feature(vmaf, "psnr", d);',
                        '\t\tif (err) goto end;',
                    )) + '\n',
                ),
                'forbidden VMAF temp-buffer cleanup regression: \t\tgoto end;',
                'vmaf-temp-buffer-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/encoder.cpp'),
                    '\n'.join((
                        'RPSListNode* newIdxNode = new RPSListNode();',
                        'if (newIdxNode == nullptr)',
                        '    goto fail;',
                    )) + '\n',
                ),
                'forbidden encoder RPS-list allocation regression: RPSListNode* newIdxNode = new RPSListNode();',
                'encoder-rps-list-alloc-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'int x265_encoder_headers(x265_encoder *enc, x265_nal **pp_nal, uint32_t *pi_nal)',
                        '{',
                        '    if (pp_nal && enc)',
                        '    {',
                        '        Encoder *encoder = static_cast<Encoder*>(enc);',
                        '        return 0;',
                        '    }',
                        '    if (enc)',
                        '    {',
                        '        Encoder *encoder = static_cast<Encoder*>(enc);',
                        '        encoder->m_aborted = true;',
                        '    }',
                        '    return -1;',
                        '}',
                    )) + '\n',
                ),
                'missing x265_encoder_headers argument guardrail: if (!enc || !pp_nal)',
                'encoder-headers-arg-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/level.cpp'),
                    '\n'.join((
                        'int x265_param_apply_profile(x265_param *param, const char *profile)',
                        '{',
                        '    if (!param || !profile)',
                        '        return 0;',
                        '#ifdef SVT_HEVC',
                        '    return 0;',
                        '#endif',
                        '}',
                    )) + '\n',
                ),
                'x265_param_apply_profile must not treat null param and null profile as the same success path',
                'x265-param-apply-profile-null-guard',
            ),
            case(
                lambda repo: (
                    write_repo_file(repo, Path('source/common/scaler.h'), 'class ScalerFilterManager {};\n'),
                    write_repo_file(repo, Path('source/common/scaler.cpp'), 'int ScalerFilterManager::init(int algorithmFlags, VideoDesc *srcVideoDesc, VideoDesc *dstVideoDesc)\n'),
                ),
                'missing scaler init rollback guardrail',
                'scaler-init-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'x265_copy_params(&save, encoder->m_latestParam);',
                        'int ret = encoder->reconfigureParam(encoder->m_latestParam, param_in);',
                    )) + '\n',
                ),
                'missing reconfig save zone rollback guardrail',
                'reconfig-save-zone-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("me") p->searchMethod = parseName(value, x265_motion_est_names, bError);',
                        'p->vui.videoFormat = parseName(value, x265_video_format_names, bError);',
                    )) + '\n',
                ),
                'forbidden parseName regression',
                'parse-name-assignment-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/ratecontrol.cpp'),
                    'if (p && sscanf(p, opt "=%d%n" , &i, &consumedOpt) == 1 && (p[consumedOpt] == \' \' || p[consumedOpt] == \'\\0\') && param_val != i)\n',
                ),
                'forbidden ratecontrol first-pass parse regression',
                'ratecontrol-first-pass-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'int i = strtol(preset, &end, 10);\n',
                ),
                'forbidden preset index parse regression',
                'preset-index-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'for (init = buf; (tok = strtok_r(init, \",\", &saveptr)); init = nullptr)\n',
                ),
                'forbidden CPU list parse regression',
                'cpu-list-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265.cpp'),
                    'std::fclose(cliopt[0].scenecutAwareQpConfig);\n',
                ),
                'missing scenecut QP cleanup guardrail',
                'scenecut-qp-cleanup-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265.cpp'),
                    'if (isAbrLadder && !abrConfig)\n        std::exit(1);\n',
                ),
                'forbidden x265 main cleanup regression',
                'x265-main-cleanup-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/output/raw.cpp'),
                    '\n'.join((
                        'ofs = x265_fopen(fname, "wb");',
                        'if (!ofs || std::ferror(ofs))',
                        '    b_fail = true;',
                    )) + '\n',
                ),
                'missing raw open cleanup-state guardrail',
                'raw-open-cleanup-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/output/raw.cpp'),
                    'if (ofs != stdout && std::fclose(ofs))\n    b_fail = true;\n',
                ),
                'missing raw close guardrail',
                'raw-close-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/abrEncApp.cpp'),
                    '\n'.join((
                        'if (!m_encoder)',
                        '{',
                        '    m_ret = 2;',
                        '    return -1;',
                        '}',
                    )) + '\n',
                ),
                'missing abr init reader rollback guardrail: m_reader = new (std::nothrow) Reader(m_id, this);',
                'abr-init-reader-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)',
                        'parsedValue = x265_atobool(value, bLocalError);',
                        'int namedValue = parseName(value, names, bLocalError);',
                        'parsedValue = namedValue;',
                        'OPT("interlace")',
                        '{',
                        '    bool bInterlaceBoolError = false;',
                        '    int interlaceBoolValue = x265_atobool(value, bInterlaceBoolError);',
                        '    bError |= !parseBoolOrNamedValue(value, x265_interlace_names, p->interlaceMode)',
                        '           || p->interlaceMode < 0 || p->interlaceMode > 2;',
                        '}',
                        'CHECK(param->interlaceMode < 0 || param->interlaceMode > 2,',
                    )) + '\n',
                ),
                'forbidden interlace parse regression',
                'interlace-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)',
                        'int boolValue = x265_atobool(value, bLocalError);',
                        'parsedValue = x265_atoi(value, bLocalError);',
                        'bool bRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
                        'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                        '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                        'bool bRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
                        'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                        '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                        'CHECK(param->rdoqLevel < 0 || param->rdoqLevel > 2,',
                    )) + '\n',
                ),
                'forbidden rdoq parse regression',
                'rdoq-level-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/ratecontrol.cpp'),
                    "if (end == cursor || parsedFirst > UINT_MAX || *end != separator)\n",
                ),
                'forbidden ratecontrol numeric helper regression',
                'ratecontrol-numeric-helper-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/ratecontrol.cpp'),
                    'sscanf(p, " input-res=%dx%d%n", &i, &j, &consumed) != 2\n',
                ),
                'forbidden ratecontrol stats parse regression',
                'ratecontrol-stats-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/ratecontrol.cpp'),
                    'if (e < 10)\n',
                ),
                'forbidden ratecontrol stats-line parse regression',
                'ratecontrol-stats-line-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/ratecontrol.cpp'),
                    'e = sscanf(p, " in:%d out:%d%n", &frameNumber, &encodeOrder, &consumedPrefix);\n',
                ),
                'forbidden ratecontrol stats-prefix parse regression',
                'ratecontrol-stats-prefix-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)',
                        'int boolValue = x265_atobool(value, bLocalError);',
                        'if (!bLocalError && boolValue)',
                        'parsedValue = 1;',
                        'parsedValue = x265_atoi(value, bLocalError);',
                        'return !bLocalError;',
                        'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                        '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                        'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                        '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                        'CHECK(param->rdoqLevel < 0 || param->rdoqLevel > 2,',
                    )) + '\n',
                ),
                'forbidden bool-or-numeric-int regression',
                'param-bool-numeric-int-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        '    p->rc.bitrate = x265_atoi(value, bError);',
                        '        p->rc.rateControlMode = X265_RC_ABR;',
                    )) + '\n',
                ),
                'forbidden bitrate mode regression',
                'bitrate-mode-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        '    p->rc.qp = x265_atoi(value, bError);',
                        '        p->rc.rateControlMode = X265_RC_CQP;',
                    )) + '\n',
                ),
                'forbidden qp mode regression',
                'qp-mode-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("strict-cbr")',
                        '{',
                        '    p->rc.bStrictCbr = atobool(value);',
                        '    p->rc.pbFactor = 1.0;',
                        '}',
                    )) + '\n',
                ),
                'forbidden strict-cbr regression',
                'strict-cbr-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/sao.cpp'),
                    'fail:\n    return false;\n',
                ),
                'forbidden SAO create rollback regression',
                'sao-create-rollback',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("bitrate")',
                        '{',
                        '    svtHevcParam->rateControlMode = 1;',
                        '    svtHevcParam->targetBitRate = x265_atoi(value, bError);',
                        '}',
                    )) + '\n',
                ),
                'forbidden SVT bitrate mode regression',
                'svt-bitrate-mode-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'if (zoneAllocCount)',
                        '{',
                        '    param->rc.zoneCount = zoneAllocIsZoneFile ? 0 : p->rc.zoneCount;',
                        '}',
                        'x265_copy_params(param, p);',
                        'if (!param->bResetZoneConfig && param->rc.zonefileCount)',
                        '{',
                        '    param->rc.zones = x265_zone_alloc(param->rc.zonefileCount, 1);',
                        '}',
                    )) + '\n',
                ),
                'missing zone open staging guardrail',
                'api-zone-open-staging',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'dst->rc.zoneCount = src->rc.zoneCount;',
                        'dst->rc.zonefileCount = src->rc.zonefileCount;',
                        'dst->reconfigWindowSize = src->reconfigWindowSize;',
                    )) + '\n',
                ),
                'missing copy_params zone replacement guardrail',
                'copy-params-zone-replace-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    '\n'.join((
                        'x265_log_file(param, X265_LOG_ERROR, "failed to open output file <%s> for writing\\n", outputfn);',
                        'return true;',
                    )) + '\n',
                ),
                'missing CLI output failure cleanup guardrail: closeVmafInputFile(param, vmafData->reference_file, "reference", "after output open failure");',
                'cli-output-failure-full-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/input/lavf.cpp'),
                    'FAIL_IF_ERROR(avformat_open_input(&h->lavf, info.filename, nullptr, nullptr), "could not open input file\\n")\n',
                ),
                'forbidden Lavf openfile cleanup regression',
                'lavf-openfile-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("qp")',
                        '{',
                        '    svtHevcParam->rateControlMode = 0;',
                        '    svtHevcParam->qp = x265_atoi(value, bError);',
                        '}',
                    )) + '\n',
                ),
                'forbidden SVT qp mode regression',
                'svt-qp-mode-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/abrEncApp.cpp'),
                    '\n'.join((
                        'x265_picture* src = x265_picture_alloc();',
                        'x265_picture_init(m_parentEnc->m_param, src);',
                        'dest->planes[0] = X265_MALLOC(char, dest->framesize);',
                        'std::memcpy(dest->planes[0], src->planes[0], src->framesize * sizeof(char));',
                    )) + '\n',
                ),
                'missing reader thread alloc guardrail: if (!src)',
                'reader-thread-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/abrEncApp.cpp'),
                    '\n'.join((
                        'm_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx] = x265_picture_alloc();',
                        'x265_picture_init(m_parentEnc->m_param, m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx]);',
                        'm_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWritten % QDepth]->planes[j] = X265_MALLOC(char, planesize[j]);',
                    )) + '\n',
                ),
                'missing scaler thread alloc guardrail: if (!m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx])',
                'scaler-thread-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/dynamicHDR10/metadataFromJson.cpp'),
                    '\n'.join((
                        'delete(metadata);',
                        'metadata = new uint8_t[mSEIBytesToRead];',
                        'metadata = new uint8_t*[numFrames];',
                    )) + '\n',
                ),
                'forbidden HDR10 metadata ownership regression',
                'hdr10-json-metadata-ownership',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/temporalfilter.cpp'),
                    '\n'.join((
                        'refFrame->compensatedPic = new PicYuv;',
                        'refFrame->compensatedPic->create(param, true);',
                        '',
                        'return 1;',
                        'fail:',
                        '    return 0;',
                    )) + '\n',
                ),
                'forbidden temporalfilter refpic rollback regression',
                'temporalfilter-refpic-rollback',
            ),
            case(
                lambda repo: (
                    write_repo_file(repo, Path('source/common/frame.cpp'), 'Frame::Frame()\n{\n    // mcstf\n}\n'),
                    write_repo_file(
                        repo,
                        Path('source/common/temporalfilter.cpp'),
                        '\n'.join((
                            'void resetRefPicInfoState(TemporalFilterRefPicInfo* refFrame)',
                            '{',
                            '    refFrame->picBuffer = nullptr;',
                            '    refFrame->picBufferSubSampled2 = nullptr;',
                            '    refFrame->picBufferSubSampled4 = nullptr;',
                            '    refFrame->poc = 0;',
                            '    refFrame->lowres = nullptr;',
                            '    refFrame->lowerRes = nullptr;',
                            '    refFrame->origOffset = 0;',
                            '    refFrame->isFilteredFrame = false;',
                            '    refFrame->isSubsampled = nullptr;',
                            '    refFrame->slicetype = X265_TYPE_AUTO;',
                            '}',
                        )) + '\n',
                    ),
                ),
                'missing temporalfilter refpic state-init guardrail: std::fill_n(m_mcstfRefList, MAX_MCSTF_TEMPORAL_WINDOW_LENGTH, TemporalFilterRefPicInfo());',
                'temporalfilter-refpic-state-init',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/temporalfilter.cpp'),
                    '\n'.join((
                        'bool TemporalFilter::init(const x265_param* param)',
                        '{',
                        '    m_metld = new (std::nothrow) MotionEstimatorTLD;',
                        '    return m_metld != nullptr;',
                        '}',
                    )) + '\n',
                ),
                'missing temporalfilter metld YUV guardrail: inline bool hasMotionEstimatorTLDBuffers(const MotionEstimatorTLD* metld)',
                'temporalfilter-metld-yuv-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'if (dst->logfn)',
                        '{',
                        '    free(dst->logfn);',
                        '    dst->logfn = nullptr;',
                        '}',
                        'if (src->logfn)',
                        '{',
                        '    dst->logfn = strdup(src->logfn);',
                        '}',
                    )) + '\n',
                ),
                'missing param string replacement guardrail',
                'param-string-replace-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("zones")',
                        '{',
                        '    p->rc.zoneCount = 1;',
                        '    p->rc.zones = X265_MALLOC(x265_zone, p->rc.zoneCount);',
                        '    p->rc.zones[i].startFrame = x265_atoi(c, bZoneValueError);',
                        '    p->rc.zones[i].endFrame = x265_atoi(firstComma + 1, bZoneValueError);',
                        '    p->rc.zones[i].qp = x265_atoi(modeValue, bZoneValueError);',
                        '    p->rc.zones[i].bitrateFactor = x265_atof(modeValue, bZoneValueError);',
                        '}',
                    )) + '\n',
                ),
                'forbidden zones regression',
                'zones-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/output/raw.cpp'),
                    'std::fclose(ofs);\n',
                ),
                'missing RAW output fail-state guardrail',
                'raw-output-fail-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'vmafData->reference_file = x265_fopen(inputfn[0], "rb");\n            vmafData->distorted_file = x265_fopen(reconfn[0], "rb");\n',
                ),
                'missing VMAF/recon guardrail',
                'vmaf-recon-state-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/output/reconplay.cpp'),
                    'std::fprintf(outputPipe, "FRAME\\n");\n',
                ),
                'missing ReconPlay pipe fail-state guardrail',
                'reconplay-pipe-fail-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'if (tok)',
                        '{',
                        '    bool bValueError = false;',
                        '    value = x265_atof(tok, bValueError);',
                        '    if (!bValueError)',
                        '        break;',
                        '}',
                        'while (1);',
                    )) + '\n',
                ),
                'missing lambda fail-fast guardrail: x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
                'lambda-file-failfast',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/input/lavf.cpp'),
                    'X265_FREE(frame_buffer);\n        frame_buffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));\n',
                ),
                'forbidden LAVF buffer replace regression',
                'lavf-buffer-replace-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'temp1 = strtok(pools, ",");\n',
                ),
                'forbidden SVT pools parse regression',
                'svt-pools-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/threadpool.cpp'),
                    'double mhz = std::strtod(line.c_str() + colon + 1, nullptr);\n',
                ),
                'forbidden threadpool CPU frequency parse regression',
                'threadpool-cpu-frequency-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/threadpool.cpp'),
                    'if (errno != ERANGE && end != value && std::isfinite(mhz) && mhz > maxMhz)\n',
                ),
                'forbidden threadpool CPU frequency tail regression',
                'threadpool-cpu-frequency-tail-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/input/lavf.cpp'),
                    'if (bError)\n',
                ),
                'forbidden lavf framecount parse regression',
                'lavf-framecount-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/output/gop.cpp'),
                    'std::fclose(data_file);\n',
                ),
                'missing GOP close fail-state guardrail',
                'gop-close-fail-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    'fclose(csvfp);\nreturn x265_fopen(param->csvfn, "ab");\n',
                ),
                'missing CSV log reopen guardrail',
                'csvlog-reopen-state',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)',
                        '{',
                        '    parsedValue = x265_atof(value, bLocalError);',
                        '    return !bLocalError;',
                        '}',
                        'OPT("psy-rd")',
                        '{',
                        '    bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd);',
                        '}',
                        'static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])',
                    )) + '\n',
                ),
                'forbidden param bool-or-numeric-double regression',
                'param-bool-numeric-double-safety',
            ),
            case(lambda repo: replace_text(build_workflow(repo), '--forbidden-flag-substring=-std=gnu++17', '# --forbidden-flag-substring=-std=gnu++17'), 'GNU++20 downgrade guard must reject GNU++17 flags', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'configure_cxx20_scan x265/source build/cxx20-downgrade-guard', 'configure_cxx20_scan x265/source build/cxx20-warning-scan'), 'GNU++20 downgrade guard must actively configure downgrade build', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), '          cpu_targets=(haswell)', '          cpu_targets=(znver4)'), 'CPU warning scan push mode must keep haswell as the representative CPU target', 'warning-scan-full-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '          cpu_targets+=(arrowlake znver5)', '          # cpu_targets+=(arrowlake znver5)'), 'CPU warning scan full mode must add arrowlake/znver5 targets behind is_full_warning_scan', 'warning-scan-full-gate'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_clang build/cxx20-warning-scan-asm', 'check_cxx20_commands_clang build/cxx20-warning-scan'), 'ASM warning scan must actively check asm compile commands target', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), '--required-file-substring=source/test/', '--required-file-substring=source/common/'), 'ASM warning scan must actively require test sources', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', '--required-file-substring=source/input/lavf.cpp', count=2), 'C++20 warning scan must actively require LAVF macro', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands-12bit', 'echo skip-linux-gcc-12bit-shape'), 'Linux GCC diagnostics must actively check 12-bit compile commands', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands ', 'echo skip-windows-gcc-base '), 'Windows GCC diagnostics must actively check base compile commands', 'gnu20-diagnostic-steps'),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively require mkv.cpp coverage',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively require MKV macro',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively reject LAVF macro on common.cpp',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively reject L-SMASH macro on common.cpp',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively reject LAVF macro on encoder.cpp',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LSMASH \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_MKV \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively reject L-SMASH macro on encoder.cpp',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively reject MKV macro on common.cpp',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_MKV \\\n",
                    "          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \\\n            --min-cpp-commands=60 \\\n            --required-depth-define=-DX265_DEPTH=8 \\\n            --forbidden-flag=-DX265_DEPTH=10 \\\n            --forbidden-flag=-DX265_DEPTH=12 \\\n            --required-file-substring=source/encoder/ \\\n            --required-file-substring=source/common/ \\\n            --required-file-substring=source/input/ \\\n            --required-file-substring=source/output/ \\\n            --required-file-substring=source/output/mkv.cpp \\\n            --required-file-substring=source/output/reconplay.cpp \\\n            --required-file-substring=source/dynamicHDR10/ \\\n            --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV \\\n            --forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH \\\n            --forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF \\\n",
                    count=1,
                ),
                'Windows GCC diagnostics must actively reject MKV macro on encoder.cpp',
                'gnu20-diagnostic-steps',
            ),
            case(lambda repo: replace_text(build_workflow(repo), '--required-file-substring=source/common/winxp.cpp \\', '--required-file-substring=source/common/version.cpp \\', count=1), 'Windows GCC diagnostics must actively require winxp.cpp coverage', 'gnu20-diagnostic-steps'),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          use-mimalloc: 'false'\n          use-obuparse: ${{ env.CI_FULL_EVENT }}\n          use-lsmash: ${{ env.CI_FULL_EVENT }}\n          extra-msys2-packages: ''",
                    "          use-mimalloc: 'false'\n          use-obuparse: ${{ env.CI_FULL_EVENT }}\n          use-lsmash: ${{ env.CI_FULL_EVENT }}\n          extra-msys2-packages: mingw-w64-clang-x86_64-zimg",
                ),
                'C++20 warning scan dependency setup must keep extra-msys2-packages empty for shared CLANG64 cache reuse',
                'warning-scan-dependencies',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          ffmpeg-cache-suffix: lavf-v3-clang',
                    '          ffmpeg-cache-suffix: lavf-v4-clang',
                    count=2,
                ),
                'C++20 warning scan dependency setup must pin ffmpeg-cache-suffix=lavf-v3-clang',
                'warning-scan-dependencies',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          use-ffmpeg: ${{ env.CI_FULL_EVENT }}",
                    "          use-ffmpeg: 'true'",
                ),
                'C++20 warning scan dependency setup must enable FFmpeg only for manual/tag full scans',
                'warning-scan-dependencies',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '              --enable-avformat --enable-avcodec --enable-avutil --enable-swscale \\\n',
                    '              --enable-avformat --enable-avcodec --enable-avutil --enable-swscale \\\n              --enable-ffmpeg --enable-ffprobe \\\n',
                    count=1,
                ),
                'C++20 warning scan FFmpeg config must stay lightweight and omit: --enable-ffmpeg',
                'warning-scan-dependencies',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          use-obuparse: ${{ env.CI_FULL_EVENT }}",
                    "          use-obuparse: 'true'",
                ),
                'C++20 warning scan dependency setup must enable obuparse only for manual/tag full scans',
                'warning-scan-dependencies',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          use-lsmash: ${{ env.CI_FULL_EVENT }}",
                    "          use-lsmash: 'true'",
                ),
                'C++20 warning scan dependency setup must enable L-SMASH only for manual/tag full scans',
                'warning-scan-dependencies',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '        run: pacman -S --needed --noconfirm mingw-w64-clang-x86_64-zimg',
                    '        run: echo skip-zimg-install',
                ),
                'C++20 warning scan must install mingw-w64-clang-x86_64-zimg in a dedicated warning-scan step',
                'warning-scan-dependencies',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '            git',
                    '',
                ),
                'Windows GCC diagnostics setup must install git',
                'windows-gcc-diagnostics-setup',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "            mingw-w64-x86_64-cmake",
                    "            make\n            mingw-w64-x86_64-cmake",
                ),
                'Windows GCC diagnostics setup must not install unused MSYS2 package make',
                'windows-gcc-diagnostics-setup',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '            mingw-w64-x86_64-python',
                    '            mingw-w64-x86_64-clang',
                ),
                'Windows GCC diagnostics setup must install mingw-w64-x86_64-python',
                'windows-gcc-diagnostics-setup',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "env:\n  CI_FULL_EVENT: ${{ (github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')) && 'true' || 'false' }}\n\nconcurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: ${{ github.event_name == 'push' && !startsWith(github.ref, 'refs/tags/') }}\n\n",
                    '',
                    count=1,
                ),
                'Build workflow must declare concurrency',
                'build-workflow-concurrency',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          source x265/.github/scripts/ensure_cmake4.sh\n          ensure_cmake4\n          cmake --version',
                    '          cmake --version',
                    count=1,
                ),
                'cxx20-linux-gcc-compile-commands must source ensure_cmake4 helper',
                'linux-cmake-setup',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          source x265/.github/scripts/ensure_cmake4.sh\n          ensure_cmake4\n          cmake --version',
                    '          source x265/.github/scripts/ensure_cmake4.sh\n          python -m venv "$RUNNER_TEMP/cmake-venv"\n          "$RUNNER_TEMP/cmake-venv/bin/python" -m pip install \'cmake>=4.0,<5\'\n          export PATH="$RUNNER_TEMP/cmake-venv/bin:$PATH"\n          cmake --version',
                    count=1,
                ),
                'cxx20-linux-gcc-compile-commands must not inline duplicate CMake venv bootstrap logic',
                'linux-cmake-setup',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          source x265/.github/scripts/ensure_linux_sanitizer_toolchain.sh\n          ensure_linux_sanitizer_toolchain\n          source x265/.github/scripts/ensure_cmake4.sh\n          ensure_cmake4\n          cmake --version',
                    '          source x265/.github/scripts/ensure_linux_sanitizer_toolchain.sh\n          ensure_linux_sanitizer_toolchain\n          cmake --version',
                    count=1,
                ),
                'linux-clang-sanitizers must source ensure_cmake4 helper',
                'linux-cmake-setup',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          source x265/.github/scripts/ensure_linux_sanitizer_toolchain.sh\n          ensure_linux_sanitizer_toolchain\n          source x265/.github/scripts/ensure_cmake4.sh',
                    '          source x265/.github/scripts/ensure_cmake4.sh',
                    count=1,
                ),
                'linux-clang-sanitizers must source Linux sanitizer toolchain helper',
                'linux-sanitizer-toolchain-setup',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          source x265/.github/scripts/ensure_linux_sanitizer_toolchain.sh\n          ensure_linux_sanitizer_toolchain\n          source x265/.github/scripts/ensure_cmake4.sh',
                    '          source x265/.github/scripts/ensure_linux_sanitizer_toolchain.sh\n          ensure_linux_sanitizer_toolchain\n          sudo apt-get update\n          sudo apt-get install -y clang lld ninja-build\n          source x265/.github/scripts/ensure_cmake4.sh',
                    count=1,
                ),
                'linux-clang-sanitizers must not inline duplicate sanitizer toolchain apt bootstrap: sudo apt-get update',
                'linux-sanitizer-toolchain-setup',
            ),
            case(lambda repo: replace_text(build_workflow(repo), 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 64x64', 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 128x128'), 'Linux GCC smoke --input-res must be 64x64, got 128x128', 'linux-gcc-smoke'),
            case(lambda repo: replace_text(build_workflow(repo), '  pull_request:', '  pull_request_disabled:'), 'Build workflow must define pull_request trigger for pre-merge CI', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "      - '.github/workflows/**'", "      - '.github/workflows/build.yml'"), 'Build workflow pull_request paths missing: .github/workflows/**', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "      - '.github/patches/**'", "      - '.github/scripts/**'"), 'Build workflow pull_request paths missing: .github/patches/**', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "      - '.github/deps-cache.json'\n", '', count=1), 'Build workflow pull_request paths missing: .github/deps-cache.json', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "    if: github.event_name != 'pull_request'\n    runs-on: windows-latest", "    runs-on: windows-latest", count=1), 'Build workflow job cxx20-warning-scan must be skipped for pull_request fast gate', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "  cxx20-gcc-compile-commands:\n    needs: validate-deps-cache-suffix\n    runs-on: windows-latest", "  cxx20-gcc-compile-commands-disabled:\n    needs: validate-deps-cache-suffix\n    runs-on: windows-latest", count=1), 'missing workflow job: cxx20-gcc-compile-commands', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "  cxx20-gcc-compile-commands:\n    needs: validate-deps-cache-suffix\n    runs-on: windows-latest", "  cxx20-gcc-compile-commands:\n    needs: validate-deps-cache-suffix\n    if: github.event_name != 'pull_request'\n    runs-on: windows-latest", count=1), 'Build workflow job cxx20-gcc-compile-commands must run for pull_request fast gate', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "  cxx20-linux-gcc-compile-commands:\n    needs: validate-deps-cache-suffix\n    runs-on: ubuntu-latest", "  cxx20-linux-gcc-compile-commands-disabled:\n    needs: validate-deps-cache-suffix\n    runs-on: ubuntu-latest", count=1), 'missing workflow job: cxx20-linux-gcc-compile-commands', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "  cxx20-linux-gcc-compile-commands:\n    needs: validate-deps-cache-suffix\n    runs-on: ubuntu-latest", "  cxx20-linux-gcc-compile-commands:\n    needs: validate-deps-cache-suffix\n    if: github.event_name != 'pull_request'\n    runs-on: ubuntu-latest", count=1), 'Build workflow job cxx20-linux-gcc-compile-commands must run for pull_request fast gate', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '  linux-clang-sanitizers:', '  linux-clang-sanitizers-disabled:'), 'Build workflow must include linux-clang-sanitizers PR fast gate job', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '  build-metadata:', '  build-metadata-disabled:'), 'Build workflow must include build-metadata job', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '            enable_hdr10_plus=OFF', '            enable_hdr10_plus=ON', count=1), 'sanitizer PR fast gate must disable HDR10+ for speed', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "      - validate-deps-cache-suffix\n      - build-metadata", "      - validate-deps-cache-suffix", count=1), 'Build workflow job build must need validate-deps-cache-suffix and build-metadata', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "      - build\n    if: startsWith(github.ref, 'refs/tags/')", "      - build\n      - linux-clang-sanitizers\n    if: startsWith(github.ref, 'refs/tags/')"), 'publish-release must not depend on PR fast-gate sanitizer job', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '      - validate-ci-guardrails\n', '', count=1), 'publish-release must depend on full-gate job: validate-ci-guardrails', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '      - build-metadata\n      - build', '      - build', count=1), 'publish-release must depend on full-gate job: build-metadata', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "    if: startsWith(github.ref, 'refs/tags/')", "    if: github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')", count=1), 'publish-release must only run for tag refs', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '    - name: Validate Release Tag', '    - name: Validate Release Tag Disabled', count=1), 'missing job publish-release step: Validate Release Tag', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '          *) echo "Release artifacts require a numeric version tag, got ${GITHUB_REF_NAME:-}" >&2; exit 1 ;;', '          *) version="${{ needs.build-metadata.outputs.latest_tag }}" ;;', count=1), 'publish-release Validate Release Tag must include: Release artifacts require a numeric version tag', 'build-pr-fast-gate'),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "      - name: Run C++20 shared and all-bit-depth warning scans\n        if: env.CI_FULL_EVENT == 'true'",
                    "      - name: Run C++20 shared and all-bit-depth warning scans",
                ),
                'C++20 shared/all-bit-depth warning scan step must run only for workflow_dispatch or tags',
                'warning-scan-full-gate',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          if is_full_warning_scan; then',
                    '          if true; then',
                    count=1,
                ),
                'C++20 warning scan full-only dependency scans must be gated behind is_full_warning_scan',
                'warning-scan-full-gate',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          if is_full_warning_scan; then\n            cpu_targets+=(arrowlake znver5)\n          fi',
                    '          cpu_targets+=(arrowlake znver5)',
                ),
                'CPU warning scan full-only CPU targets must be gated behind is_full_warning_scan',
                'warning-scan-full-gate',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '              ninja -C build/cxx20-warning-scan-shared-deps-asm cli',
                    '              echo skip-shared-deps-asm-build',
                ),
                'C++20 warning scan full-only dependency asm build must stay inside is_full_warning_scan gate',
                'warning-scan-full-gate',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '                --required-file-flag=source/output/mkv.cpp=-DENABLE_MKV \\\n',
                    '',
                    count=2,
                ),
                'C++20 warning scan must actively require MKV macro',
                'gnu20-diagnostic-steps',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '              --required-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1 \\\n',
                    '',
                    count=1,
                ),
                'C++20 warning scan must actively require exported API macro for shared-library builds',
                'gnu20-diagnostic-steps',
            ),
            case(lambda repo: replace_text(update_deps_workflow(repo), 'python .github/scripts/run_python_ci_guard_bundle.py --suite update-deps', 'python .github/scripts/check_dependency_patch_suffixes.py --allow-missing-cache', count=1), 'missing required update-deps guard snippet: python .github/scripts/run_python_ci_guard_bundle.py --suite update-deps', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "('python', '.github/scripts/check_dependency_patch_suffixes.py', '--allow-missing-cache'),", "('python', '.github/scripts/check_dependency_patch_suffixes.py'),", count=1), "Python CI guard bundle runner missing detail: ('python', '.github/scripts/check_dependency_patch_suffixes.py', '--allow-missing-cache'),", 'required-snippets'),
            case(lambda repo: replace_text(update_deps_workflow(repo), '          python .github/scripts/run_python_ci_guard_bundle.py --suite update-deps', '          python .github/scripts/run_python_ci_guard_bundle.py --suite update-deps || true', count=1), 'update-deps guard bundle must run the exact Python CI guard bundle runner with --suite update-deps without softening wrappers or extra flags', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "parser.add_argument('--suite', choices=tuple(SUITE_COMMANDS), default='default')", "parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])", count=1), "Python CI guard bundle runner missing detail: parser.add_argument('--suite', choices=tuple(SUITE_COMMANDS), default='default')", 'required-snippets'),
            case(lambda repo: replace_text(update_deps_workflow(repo), "      - name: Check CI guardrails\n        run: |", "      - name: Check CI guardrails\n        if: github.event_name == 'workflow_dispatch'\n        run: |", count=1), 'update-deps Check CI guardrails must not be step-gated', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), 'gop-muxer-cache-suffix:', 'gop-muxer-cache-label:'), 'missing dependency update anchor: gop-muxer-cache-suffix:', 'dependency-update-anchors'),
            case(lambda repo: replace_text(profiling_workflow(repo), 'needs: validate-guardrails', '# needs removed'), 'Build Profiling build job must need validate-guardrails', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), "    if: startsWith(github.ref, 'refs/tags/')", "    if: github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')", count=1), 'Build Profiling publish-release must only run for tag refs', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), 'python .github/scripts/run_python_ci_guard_bundle.py --suite profdata', 'python .github/scripts/run_python_ci_guard_bundle.py', count=1), 'missing required Build Profiling workflow guard snippet: python .github/scripts/run_python_ci_guard_bundle.py --suite profdata', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "('python', '.github/scripts/check_profdata_metadata.py', '--self-test'),", "('python', '.github/scripts/check_profdata_metadata.py'),", count=1), "Python CI guard bundle runner missing detail: ('python', '.github/scripts/check_profdata_metadata.py', '--self-test'),", 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        path: x265', '        path: x264', count=1), 'Build Profiling build Checkout X265 must set path=x265', 'required-snippets'),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    "  publish-release:\n    needs: [build, validate-guardrails]\n    if: startsWith(github.ref, 'refs/tags/')\n    runs-on: windows-latest\n    timeout-minutes: 20\n    steps:\n    - name: Checkout X265\n      uses: actions/checkout@v6\n      with:\n        path: x265\n        fetch-depth: 0\n        fetch-tags: true",
                    "  publish-release:\n    needs: [build, validate-guardrails]\n    if: startsWith(github.ref, 'refs/tags/')\n    runs-on: windows-latest\n    timeout-minutes: 20\n    steps:\n    - name: Checkout X265\n      uses: actions/checkout@v6\n      with:\n        path: x265\n        fetch-depth: 0\n        fetch-tags: false",
                    count=1,
                ),
                'Build Profiling publish-release Checkout X265 must set fetch-tags=True',
                'required-snippets',
            ),
            case(lambda repo: replace_text(profiling_workflow(repo), '      fail-fast: false', '      fail-fast: true', count=1), 'Build Profiling build job must set strategy.fail-fast to false so one profiling CPU failure cannot cancel remaining legs', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          - x86-64\n          - haswell\n          - skylake\n          - alderlake\n          - raptorlake\n          - arrowlake\n          - znver2\n          - znver3\n          - znver4\n          - znver5', '          - x86-64\n          - haswell'), 'Build Profiling build job must use the full profiling CPU matrix', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '      uses: ./x265/.github/actions/setup-windows-deps', '      uses: ./x265/.github/actions/setup-windows-deps-disabled', count=1), 'Build Profiling Setup Shared Dependencies must use the setup-windows-deps action', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        ffmpeg-cache-suffix: profiling-v1-clang', '        ffmpeg-cache-suffix: full-v5-clang'), 'Build Profiling Setup Shared Dependencies must pin ffmpeg-cache-suffix=profiling-v1-clang', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        use-mimalloc: \'true\'', '        use-mimalloc: \'false\'', count=1), 'Build Profiling Setup Shared Dependencies must keep mimalloc enabled', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          PGO_OPT="--enable-avdevice --enable-avfilter --enable-ffmpeg --enable-indev=lavfi"', '          PGO_OPT="--enable-avdevice --enable-avfilter --enable-indev=lavfi"', count=1), 'Build Profiling FFmpeg config must enable dependency: --enable-ffmpeg', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          for f in testsrc testsrc2 smptebars smptehdbars nullsrc geq gradients format scale noise; do', '          for f in testsrc smptebars smptehdbars nullsrc geq gradients format scale noise; do', count=1), 'Build Profiling FFmpeg config must enable dependency: for f in testsrc testsrc2 smptebars smptehdbars nullsrc geq gradients format scale noise; do', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '            --enable-muxer=yuv4mpegpipe \\\n', ''), 'Build Profiling FFmpeg config must enable dependency: --enable-muxer=yuv4mpegpipe', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py')", "CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py', '--only', 'required-snippets')", count=1), "Python CI guard bundle runner missing detail: CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py')", 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py'}", "NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py', 'test_check_ci_guards.py'}", count=1), "Python CI guard bundle runner missing detail: NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py'}", 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "script_dir.glob('test_check_*.py')", "script_dir.glob('test_check_ci_guards*.py')", count=1), "Python CI guard bundle runner missing detail: script_dir.glob('test_check_*.py')", 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), 'from concurrent.futures import ThreadPoolExecutor, as_completed', 'from pathlib import Path', count=1), 'Python CI guard bundle runner missing detail: from concurrent.futures import ThreadPoolExecutor, as_completed', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), 'def run_commands_parallel(repo_root, commands, jobs):', 'def run_commands_serial(repo_root, commands, jobs):', count=1), 'Python CI guard bundle runner missing detail: def run_commands_parallel(repo_root, commands, jobs):', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), '    run_commands_parallel(repo_root, commands, jobs)', '    run_command(repo_root, commands[0])', count=2), 'Python CI guard bundle runner missing detail:     run_commands_parallel(repo_root, commands, jobs)', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "parser.add_argument('--jobs', type=int, default=default_jobs())", "parser.add_argument('--verbose', action='store_true')", count=1), "Python CI guard bundle runner missing detail: parser.add_argument('--jobs', type=int, default=default_jobs())", 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        python .github/scripts/run_python_ci_guard_bundle.py --suite profdata', '        python .github/scripts/run_python_ci_guard_bundle.py --suite profdata || true', count=1), 'Build Profiling workflow guard bundle must run the exact Python CI guard bundle runner with --suite profdata without softening wrappers or extra flags', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), 'PROFDATA_GUARD_SUITE = WORKFLOW_GUARD_SUITE + (', 'PROFDATA_GUARD_SUITE = (', count=1), 'Python CI guard bundle runner missing detail: PROFDATA_GUARD_SUITE = WORKFLOW_GUARD_SUITE + (', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), "    - name: Check CI guardrails\n      shell: bash", "    - name: Check CI guardrails\n      if: startsWith(github.ref, 'refs/tags/')\n      shell: bash", count=1), 'Build Profiling Check CI guardrails must not be step-gated', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), "    - name: Compress LLVM Profdata\n      if: matrix.target_cpu == 'x86-64'", '    - name: Compress LLVM Profdata'), 'Build Profiling step Compress LLVM Profdata must run only for the x86-64 representative build', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), "    - name: Verify LLVM Profdata Artifact\n      if: matrix.target_cpu == 'x86-64'", '    - name: Verify LLVM Profdata Artifact'), 'Build Profiling step Verify LLVM Profdata Artifact must run only for the x86-64 representative build', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), "    - name: Upload LLVM Profdata Artifact\n      if: matrix.target_cpu == 'x86-64'", '    - name: Upload LLVM Profdata Artifact'), 'Build Profiling step Upload LLVM Profdata Artifact must run only for the x86-64 representative build', 'required-snippets'),
            case(lambda repo: replace_text(ci_version_helper(repo), '  elif [[ "${GITHUB_REF:-}" == refs/tags/* ]]; then', '  elif [[ "${GITHUB_REF:-}" == refs/releases/* ]]; then', count=1), 'CI version helper missing detail: elif [[ "${GITHUB_REF:-}" == refs/tags/* ]]; then', 'required-snippets'),
            case(lambda repo: replace_text(ci_version_helper(repo), '    echo "::warning::No numeric version tag found; using $version as CI fallback"', '    echo "::warning::No numeric version tag found; fallback disabled"', count=1), 'CI version helper missing detail: echo "::warning::No numeric version tag found; using $version as CI fallback"', 'required-snippets'),
            case(lambda repo: replace_text(ci_version_helper(repo), '    version="${orig_tag#M}+${distance}-g${head_hash}"', '    version="${orig_tag#M}-${distance}-g${head_hash}"', count=1), 'CI version helper missing detail: version="${orig_tag#M}+${distance}-g${head_hash}"', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        version=$(x265_package_version_for_event "${{ steps.tag.outputs.version }}" "${{ steps.ci_version.outputs.version }}")', '        version=$(x265_package_version_for_event "${{ steps.tag.outputs.version }}" "${{ github.sha }}")', count=1), 'missing required Build Profiling workflow guard snippet: version=$(x265_package_version_for_event "${{ steps.tag.outputs.version }}" "${{ steps.ci_version.outputs.version }}")', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        tag_name: ${{ github.ref_name }}', '        tag_name: ${{ steps.tag.outputs.version }}', count=1), 'Build Profiling Release Profiling Artifacts step must set tag_name=${{ github.ref_name }}', 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '    - name: Validate Profiling Release Assets', '    - name: Profiling Asset Validation Disabled', count=1), 'missing job publish-release step: Validate Profiling Release Assets', 'required-snippets'),
            case(lambda repo: replace_text(release_asset_validator(repo), '    expected_count=11', '    expected_count=0', count=1), 'release asset validator missing detail: expected_count=11', 'required-snippets'),
            case(lambda repo: replace_text(release_asset_validator(repo), '    profdata_count=0', '    profdata_count=1', count=1), 'release asset validator missing detail: profdata_count=0', 'package-scope'),
            case(lambda repo: replace_text(release_asset_validator(repo), "    prefix='x265-profiling'", "    prefix='x265'", count=1), "release asset validator missing detail: prefix='x265-profiling'", 'required-snippets'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        bash x265/.github/scripts/validate_release_assets.sh profiling release-assets "${GITHUB_REF_NAME}"', '        bash x265/.github/scripts/validate_release_assets.sh release release-assets "${GITHUB_REF_NAME}"', count=1), 'Build Profiling Validate Profiling Release Assets must run the shared profiling release asset validator without softening wrappers or extra flags', 'required-snippets'),
            case(lambda repo: replace_text(release_asset_validator(repo), '      profdata_count=$((profdata_count + 1))', '      echo skip-profdata-count', count=1), 'release asset validator missing detail: profdata_count=$((profdata_count + 1))', 'package-scope'),
            case(lambda repo: replace_text(release_asset_validator(repo), 'if [ "$mode" = \'profiling\' ] && [ "$profdata_count" -ne 1 ]; then', 'if false; then', count=1), 'release asset validator missing detail: if [ "$mode" = \'profiling\' ] && [ "$profdata_count" -ne 1 ]; then', 'required-snippets'),
            case(lambda repo: replace_text(release_asset_validator(repo), '  echo "Expected exactly one llvm-profdata archive, found $profdata_count" >&2', '  echo "llvm-profdata count mismatch" >&2', count=1), 'release asset validator missing detail: echo "Expected exactly one llvm-profdata archive, found $profdata_count" >&2', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        fail_on_unmatched_files: true', '        fail_on_unmatched_files: false'), 'Build Profiling Release Profiling Artifacts step must set fail_on_unmatched_files=True', 'required-snippets'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'build_x265_profiling.sh', '    -DENABLE_CXX20_WARNING_SCAN=ON\n', '', count=1), 'build profiling helper missing detail: -DENABLE_CXX20_WARNING_SCAN=ON', 'required-snippets'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'build_x265_profiling.sh', '    -DWARNINGS_AS_ERRORS=ON\n', '', count=1), 'build profiling helper missing detail: -DWARNINGS_AS_ERRORS=ON', 'required-snippets'),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    "    - name: Build 8b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: 8b-lib\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    "    - name: Build 8b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling-disabled\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: 8b-lib\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    count=1,
                ),
                'Build Profiling step Build 8b-lib Profiling Binaries must use the build-x265-profiling action',
                'required-snippets',
            ),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    "    - name: Build 8b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: 8b-lib\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    "    - name: Build 8b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: haswell\n        profile-class: 8b-lib\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    count=1,
                ),
                'Build Profiling step Build 8b-lib Profiling Binaries must set target-cpu=${{ matrix.target_cpu }}',
                'required-snippets',
            ),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    "    - name: Build 12b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: 12b-lib\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    "    - name: Build 12b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: 8b-lib\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    count=1,
                ),
                'Build Profiling step Build 12b-lib Profiling Binaries must set profile-class=12b-lib',
                'required-snippets',
            ),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    "    - name: Build 8b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: 8b-lib\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    "    - name: Build 8b-lib Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: 8b-lib\n        use-mimalloc: 'OFF'\n        enable-lsmash: 'ON'",
                    count=1,
                ),
                'Build Profiling step Build 8b-lib Profiling Binaries must set use-mimalloc=ON',
                'required-snippets',
            ),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    "    - name: Build All Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: all\n        use-mimalloc: 'ON'\n        enable-lsmash: 'ON'",
                    "    - name: Build All Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling\n      with:\n        target-cpu: ${{ matrix.target_cpu }}\n        profile-class: all\n        use-mimalloc: 'ON'\n        enable-lsmash: 'OFF'",
                    count=1,
                ),
                'Build Profiling step Build All Profiling Binaries must set enable-lsmash=ON',
                'required-snippets',
            ),
            case(lambda repo: replace_text(build_pgo_workflow(repo), 'python .github/scripts/run_python_ci_guard_bundle.py --suite pgo', 'python .github/scripts/check_pgo_consume_chain.py', count=1), 'missing required Build PGO workflow guard snippet: python .github/scripts/run_python_ci_guard_bundle.py --suite pgo', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), "('python', '.github/scripts/test_check_pgo_consume_chain.py'),", "('python', '.github/scripts/test_check_profdata_metadata.py'),", count=1), "Python CI guard bundle runner missing detail: ('python', '.github/scripts/test_check_pgo_consume_chain.py'),", 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        python .github/scripts/run_python_ci_guard_bundle.py --suite pgo', '        python .github/scripts/run_python_ci_guard_bundle.py --suite pgo || true', count=1), 'Build PGO workflow guard bundle must run the exact Python CI guard bundle runner with --suite pgo without softening wrappers or extra flags', 'required-snippets'),
            case(lambda repo: replace_text(python_ci_guard_bundle_runner(repo), 'for command in SUITE_COMMANDS[suite]:', 'for command in guard_test_scripts(repo_root):', count=1), 'Python CI guard bundle runner missing detail: for command in SUITE_COMMANDS[suite]:', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), "    - name: Check CI guardrails\n      shell: bash", "    - name: Check CI guardrails\n      if: startsWith(github.ref, 'refs/tags/')\n      shell: bash", count=1), 'Build PGO Check CI guardrails must not be step-gated', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), 'needs: validate-guardrails', '# needs removed'), 'Build PGO generate job must need validate-guardrails', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        default: all', '        default: 8b-lib'), 'Build PGO profile_target input must default to all', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          - all', '          - all\n          - 10b-lib'), 'Build PGO profile_target input must offer 8b-lib, 12b-lib, and all in order', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), "  group: ${{ github.workflow }}-${{ github.ref }}-x86-64-${{ inputs.profile_target || 'all' }}", '  group: ${{ github.workflow }}-${{ github.ref }}'), 'Build PGO concurrency group must serialize by ref and profile_target', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '    - name: Checkout X265\n      uses: actions/checkout@v6\n      with:\n        fetch-depth: 0\n        fetch-tags: true', '    - name: Checkout X265\n      uses: actions/checkout@v5\n      with:\n        fetch-depth: 0\n        fetch-tags: true', count=1), 'Build PGO validate-guardrails Checkout X265 must use actions/checkout@v6', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '    - name: Checkout X265\n      uses: actions/checkout@v6\n      with:\n        path: x265\n        fetch-depth: 0\n        fetch-tags: true', '    - name: Checkout X265\n      uses: actions/checkout@v6\n      with:\n        path: x264\n        fetch-depth: 0\n        fetch-tags: true', count=1), 'Build PGO generate Checkout X265 must set path=x265', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '      uses: ./x265/.github/actions/setup-windows-deps', '      uses: ./x265/.github/actions/setup-windows-deps-disabled', count=1), 'Build PGO Setup Shared Dependencies must use the setup-windows-deps action', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        ffmpeg-cache-suffix: pgo-v1-clang', '        ffmpeg-cache-suffix: full-v5-clang'), 'Build PGO Setup Shared Dependencies must pin ffmpeg-cache-suffix=pgo-v1-clang', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        use-mimalloc: \'true\'', '        use-mimalloc: \'false\'', count=1), 'Build PGO Setup Shared Dependencies must keep mimalloc enabled', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          PGO_OPT="--enable-avdevice --enable-avfilter --enable-ffmpeg --enable-indev=lavfi"', '          PGO_OPT="--enable-avdevice --enable-avfilter --enable-indev=lavfi"', count=1), 'Build PGO FFmpeg config must enable dependency: --enable-ffmpeg', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          for f in testsrc testsrc2 smptebars smptehdbars nullsrc mandelbrot life cellauto haldclutsrc; do', '          for f in testsrc smptebars smptehdbars nullsrc mandelbrot life cellauto haldclutsrc; do', count=1), 'Build PGO FFmpeg config must enable dependency: for f in testsrc testsrc2 smptebars smptehdbars nullsrc mandelbrot life cellauto haldclutsrc; do', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '            --enable-protocol=file,pipe \\\n', ''), 'Build PGO FFmpeg config must enable dependency: --enable-protocol=file,pipe', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '    - name: Build Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling', '    - name: Build Profiling Binaries\n      uses: ./x265/.github/actions/build-x265-profiling-disabled', count=1), 'Build PGO Build Profiling Binaries must use the build-x265-profiling action', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        target-cpu: x86-64', '        target-cpu: haswell'), 'Build PGO profiling action must set target-cpu=x86-64', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        llvm_profdata_version=$(llvm-profdata --version | sed -nE \'s/.*LLVM version ([0-9]+\\.[0-9]+).*/\\1/p\' | head -1)', '        llvm_profdata_version=19.1', count=1), 'Build PGO profdata publish must derive llvm_profdata_version from llvm-profdata --version', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        test -n "$llvm_profdata_version"', '        : # skip llvm_profdata version check', count=1), 'Build PGO profdata publish must require a parsed llvm-profdata version before deriving the toolchain id', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), 'profdata_branch="profdata-x86-64-${profile_target}-${profdata_toolchain}"', 'profdata_branch="profdata-x86-64-${profile_target}"'), 'Build PGO profdata publish must isolate branches by target and LLVM toolchain', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        profdata_push_dir=$(mktemp -d)', '        profdata_push_dir="$RUNNER_TEMP/profdata"', count=1), 'Build PGO profdata publish must allocate an isolated temporary publish directory', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        trap \'rm -rf "$profdata_push_dir"\' EXIT', '        : # skip profdata tempdir cleanup', count=1), 'Build PGO profdata publish must clean up the isolated temporary publish directory on exit', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        remote_url="https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}.git"', '        remote_url="https://example.invalid/not-x265.git"', count=1), 'Build PGO profdata publish must target the current repository with the GITHUB_TOKEN remote', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        git -C "$profdata_push_dir" config user.name "github-actions[bot]"', '        git -C "$profdata_push_dir" config user.name "codex"', count=1), 'Build PGO profdata publish must set the isolated publish repository user.name to github-actions[bot]', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        git -C "$profdata_push_dir" config user.email "github-actions[bot]@users.noreply.github.com"', '        git -C "$profdata_push_dir" config user.email "codex@example.invalid"', count=1), 'Build PGO profdata publish must set the isolated publish repository user.email to github-actions[bot]@users.noreply.github.com', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        scratch_dir="$profdata_push_dir/.window"', '        scratch_dir="$RUNNER_TEMP/profdata-window"', count=1), 'Build PGO profdata publish must stage bounded-window scratch state under the isolated publish directory', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        profiles_dir="$scratch_dir/profiles"', '        profiles_dir="$profdata_push_dir/profiles"', count=1), 'Build PGO profdata publish must derive the bounded-window profiles directory from scratch_dir', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        mkdir -p "$profiles_dir"', '        : # skip scratch profiles dir creation', count=1), 'Build PGO profdata publish must create the bounded-window scratch profiles directory before rotation', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          local source_path="$1"', '          local source_path="$2"', count=1), 'Build PGO profdata publish copy_if_exists helper must bind the source path argument', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '            mkdir -p "$(dirname "$destination_path")"', '            : # skip destination mkdir', count=1), 'Build PGO profdata publish copy_if_exists helper must create parent directories for rotated profiles', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '            cp "$profdata_push_dir/$source_path" "$destination_path"', '            cp "$source_path" "$destination_path"', count=1), 'Build PGO profdata publish copy_if_exists helper must copy rotated profiles from the isolated publish directory', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), 'merge_args+=("--weighted-input=$((4 - slot)),profiles/${slot}.profdata")', 'merge_args+=("profiles/${slot}.profdata")'), 'Build PGO profdata publish must weight newer profile slots more heavily', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          merge_args=()', '          merge_args=(profiles/0.profdata)', count=1), 'Build PGO profdata publish must build the bounded-window merge input list from scratch', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          cd "$scratch_dir"', '          cd "$profdata_push_dir"', count=1), 'Build PGO profdata publish must merge profdata from the bounded-window scratch directory', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          test "${#merge_args[@]}" -gt 0', '          : # skip merge_args emptiness check', count=1), 'Build PGO profdata publish must require at least one profdata input before merging', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          llvm-profdata merge -o x265.profdata "${merge_args[@]}"', '          llvm-profdata merge -o merged.profdata "${merge_args[@]}"', count=1), 'Build PGO profdata publish must merge the bounded-window profdata inputs into x265.profdata', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          llvm-profdata show x265.profdata >/dev/null', '          : # skip merged profdata validation', count=1), 'Build PGO profdata publish must validate the merged profdata artifact before publication', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        mkdir -p "$profdata_push_dir/profiles"', '        : # skip published profiles dir creation', count=1), 'Build PGO profdata publish must create the published profiles directory before copying profile slots', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          if [ -f "$profiles_dir/${slot}.profdata" ]; then', '          if true; then', count=1), 'Build PGO profdata publish must only republish bounded-window slots that exist after rotation', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '            cp "$profiles_dir/${slot}.profdata" "$profdata_push_dir/profiles/${slot}.profdata"', '            cp "$fresh_profdata" "$profdata_push_dir/profiles/${slot}.profdata"', count=1), 'Build PGO profdata publish must republish rotated profile slots from the bounded-window scratch directory', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        fresh_profdata="$GITHUB_WORKSPACE/build/x265.profdata"', '        fresh_profdata="$GITHUB_WORKSPACE/build/old.profdata"', count=1), 'Build PGO profdata publish must source the fresh profdata from the workload output at $GITHUB_WORKSPACE/build/x265.profdata', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        test -f "$fresh_profdata"', '        test -f "$scratch_dir/x265.profdata"', count=1), 'Build PGO profdata publish must require the fresh profdata artifact before rotating slots', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), 'ffmpeg_cache_suffix="pgo-v1-clang"', 'ffmpeg_cache_suffix=$(action_default "$setup_deps_action" ffmpeg-cache-suffix)'), 'Build PGO profdata metadata must record the workflow-specific FFmpeg cache suffix', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        setup_deps_action="$GITHUB_WORKSPACE/x265/.github/actions/setup-windows-deps/action.yml"', '        setup_deps_action="$GITHUB_WORKSPACE/x265/.github/actions/other/action.yml"', count=1), 'Build PGO profdata publish must load dependency defaults from the checked-out setup-windows-deps action', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          local action_file="$1"', '          local action_file="$2"', count=1), 'Build PGO profdata publish action_default helper must bind the action file argument', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          awk -v input="  ${input_name}:" \'', '          awk -v input="$input_name" \'', count=1), 'Build PGO profdata publish action_default helper must anchor parsing on the requested input name', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '            in_input && /^[[:space:]]+default:/ { print $2; exit }', '            in_input && /^[[:space:]]+default:/ { print $1; exit }', count=1), 'Build PGO profdata publish action_default helper must emit the default value token for the requested input', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        ffmpeg_ref=$(action_default "$setup_deps_action" ffmpeg-ref)', '        ffmpeg_ref=manual', count=1), 'Build PGO profdata publish must source ffmpeg_ref from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        mimalloc_ref=$(action_default "$setup_deps_action" mimalloc-ref)', '        mimalloc_ref=manual', count=1), 'Build PGO profdata publish must source mimalloc_ref from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        obuparse_ref=$(action_default "$setup_deps_action" obuparse-ref)', '        obuparse_ref=manual', count=1), 'Build PGO profdata publish must source obuparse_ref from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        obuparse_cache_suffix=$(action_default "$setup_deps_action" obuparse-cache-suffix)', '        obuparse_cache_suffix=manual', count=1), 'Build PGO profdata publish must source obuparse_cache_suffix from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        lsmash_repository=$(action_default "$setup_deps_action" lsmash-repository)', '        lsmash_repository=manual', count=1), 'Build PGO profdata publish must source lsmash_repository from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        lsmash_ref=$(action_default "$setup_deps_action" lsmash-ref)', '        lsmash_ref=manual', count=1), 'Build PGO profdata publish must source lsmash_ref from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        lsmash_cache_suffix=$(action_default "$setup_deps_action" lsmash-cache-suffix)', '        lsmash_cache_suffix=manual', count=1), 'Build PGO profdata publish must source lsmash_cache_suffix from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        gop_muxer_repository=$(action_default "$setup_deps_action" gop-muxer-repository)', '        gop_muxer_repository=manual', count=1), 'Build PGO profdata publish must source gop_muxer_repository from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        gop_muxer_ref=$(action_default "$setup_deps_action" gop-muxer-ref)', '        gop_muxer_ref=manual', count=1), 'Build PGO profdata publish must source gop_muxer_ref from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        gop_muxer_cache_suffix=$(action_default "$setup_deps_action" gop-muxer-cache-suffix)', '        gop_muxer_cache_suffix=manual', count=1), 'Build PGO profdata publish must source gop_muxer_cache_suffix from the setup-windows-deps action defaults', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        source_commit=$(git -C "$GITHUB_WORKSPACE/x265" rev-parse HEAD)', '        source_commit=$(git rev-parse HEAD)', count=1), 'Build PGO profdata publish must derive metadata source_commit from the checked-out x265 workspace', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        source_ref=$(git -C "$GITHUB_WORKSPACE/x265" rev-parse --abbrev-ref HEAD || true)', '        source_ref=$(git rev-parse --abbrev-ref HEAD || true)', count=1), 'Build PGO profdata publish must derive metadata source_ref from the checked-out x265 workspace', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          source_ref="${GITHUB_REF_NAME}"', '          source_ref="HEAD"', count=1), 'Build PGO profdata publish must fall back to GITHUB_REF_NAME for detached HEAD source_ref values', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)', '        generated_at=$(date +%s)', count=1), 'Build PGO profdata publish must timestamp metadata in UTC ISO-8601 form', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          "schema_version": 1,', '          "schema_version": 2,', count=1), 'Build PGO profdata metadata must declare schema_version 1', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          "repository": "${GITHUB_REPOSITORY}",', '          "repository": "${GITHUB_ACTOR}",', count=1), 'Build PGO profdata metadata must record the source repository', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          "workflow": "${GITHUB_WORKFLOW}",', '          "workflow": "manual",', count=1), 'Build PGO profdata metadata must record the publishing workflow name', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          "source_ref": "${source_ref}",', '          "source_ref": "HEAD",', count=1), 'Build PGO profdata metadata must record the normalized source_ref', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          "source_commit": "${source_commit}",', '          "source_commit": "unknown",', count=1), 'Build PGO profdata metadata must record the publishing source_commit', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        python x265/.github/scripts/check_profdata_metadata.py "$profdata_push_dir/metadata.json" \\', '        cat "$profdata_push_dir/metadata.json" \\'), 'missing required Build PGO workflow guard snippet: python x265/.github/scripts/check_profdata_metadata.py "$profdata_push_dir/metadata.json"', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --expected-target="$profile_target" \\\n', ''), 'missing required Build PGO workflow guard snippet: --expected-target="$profile_target"', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --current-commit="$source_commit" \\\n', ''), 'Build PGO profdata publish must run the exact metadata validation command without softening wrappers or extra flags', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --expected-toolchain="$profdata_toolchain" \\\n', ''), 'missing required Build PGO workflow guard snippet: --expected-toolchain="$profdata_toolchain"', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '--required-ffmpeg-cache-suffix=pgo-v1-clang', '--required-ffmpeg-cache-suffix=full-v5-clang'), 'missing required Build PGO workflow guard snippet: --required-ffmpeg-cache-suffix=pgo-v1-clang', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --required-obuparse-cache-suffix="$obuparse_cache_suffix" \\\n', ''), 'missing required Build PGO workflow guard snippet: --required-obuparse-cache-suffix="$obuparse_cache_suffix"', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --required-lsmash-cache-suffix="$lsmash_cache_suffix" \\\n', ''), 'missing required Build PGO workflow guard snippet: --required-lsmash-cache-suffix="$lsmash_cache_suffix"', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --required-gop-muxer-cache-suffix="$gop_muxer_cache_suffix" \\\n', ''), 'missing required Build PGO workflow guard snippet: --required-gop-muxer-cache-suffix="$gop_muxer_cache_suffix"', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '--expected-branch="$profdata_branch"', '--expected-branch=profdata-x86-64-all'), 'missing required Build PGO workflow guard snippet: --expected-branch="$profdata_branch"', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --require-dependency-fields \\\n', ''), 'missing required Build PGO workflow guard snippet: --require-dependency-fields', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --require-fresh-slot\n', ''), 'missing required Build PGO workflow guard snippet: --require-fresh-slot', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          --require-fresh-slot\n', '          --require-fresh-slot || true\n', count=1), 'Build PGO profdata publish must run the exact metadata validation command without softening wrappers or extra flags', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        cp "$scratch_dir/x265.profdata" "$profdata_push_dir/x265.profdata"', '        cp "$fresh_profdata" "$profdata_push_dir/x265.profdata"', count=1), 'Build PGO profdata publish must publish the merged bounded-window profdata artifact', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        add_paths=(x265.profdata profiles metadata.json)', '        add_paths=(x265.profdata metadata.json)', count=1), 'Build PGO profdata publish must stage exactly x265.profdata, profiles, and metadata.json', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        git -C "$profdata_push_dir" add "${add_paths[@]}"', '        git -C "$profdata_push_dir" add .', count=1), 'Build PGO profdata publish must add only the explicit profdata publish set', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        if git -C "$profdata_push_dir" diff --cached --quiet; then', '        if false; then', count=1), 'Build PGO profdata publish must skip branch updates when staged profdata is unchanged', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        git -C "$profdata_push_dir" commit -m "Update PGO profdata ($profile_target) - $(date +%Y%m%d-%H%M)"', '        echo skip-profdata-commit', count=1), 'Build PGO profdata publish must create a profdata publication commit', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        git init "$profdata_push_dir"', '        mkdir -p "$profdata_push_dir"', count=1), 'Build PGO profdata publish must initialize an isolated publish repository', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        git -C "$profdata_push_dir" remote add origin "$remote_url"', '        git -C "$profdata_push_dir" remote add upstream "$remote_url"', count=1), 'Build PGO profdata publish must bind the isolated publish repository to the computed remote', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          remote_tip=$(git -C "$profdata_push_dir" rev-parse FETCH_HEAD)', '          remote_tip=deadbeef', count=1), 'Build PGO profdata publish must snapshot the pre-publication remote tip', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          latest_remote_tip=$(git -C "$profdata_push_dir" rev-parse FETCH_HEAD)', '          latest_remote_tip="$remote_tip"', count=1), 'Build PGO profdata publish must re-read the remote tip immediately before pushing', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        if git -C "$profdata_push_dir" fetch origin "$profdata_branch" --depth=1; then', '        if git -C "$profdata_push_dir" fetch origin main --depth=1; then', count=1), 'Build PGO profdata publish must fetch the computed profdata branch before deciding whether it exists', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          git -C "$profdata_push_dir" fetch origin "$profdata_branch" --depth=1', '          git -C "$profdata_push_dir" fetch origin main --depth=1', count=1), 'Build PGO profdata publish must refetch the computed profdata branch immediately before the remote advancement check', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          git -C "$profdata_push_dir" checkout -B "$profdata_branch" FETCH_HEAD', '          git -C "$profdata_push_dir" checkout FETCH_HEAD', count=1), 'Build PGO profdata publish must reuse the fetched profdata branch tip when it exists', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          git -C "$profdata_push_dir" checkout --orphan "$profdata_branch"', '          git -C "$profdata_push_dir" checkout -b "$profdata_branch"', count=1), 'Build PGO profdata publish must create a clean orphan profdata branch when none exists', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          git -C "$profdata_push_dir" rm -rf . >/dev/null 2>&1 || true', '          echo skip-profdata-rm', count=1), 'Build PGO profdata publish must remove tracked files from an existing profdata branch before repopulating it', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          find "$profdata_push_dir" -mindepth 1 -maxdepth 1 ! -name .git ! -name .window -exec rm -rf {} +', '          echo skip-profdata-clear', count=1), 'Build PGO profdata publish must clear non-git branch contents on both existing and new branch paths', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '          if [ "$latest_remote_tip" != "$remote_tip" ]; then', '          if false; then', count=1), 'Build PGO profdata publish must detect remote branch advancement before pushing', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        elif git -C "$profdata_push_dir" ls-remote --exit-code --heads origin "$profdata_branch" >/dev/null 2>&1; then', '        elif false; then', count=1), 'Build PGO profdata publish must detect a remote profdata branch that appears mid-publication', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        git -C "$profdata_push_dir" push origin HEAD:"$profdata_branch"', '        git -C "$profdata_push_dir" push origin HEAD:"$profdata_branch" --force', count=1), 'Build PGO profdata publish must run the exact push command to the computed profdata branch without force or extra flags', 'required-snippets'),
            case(lambda repo: replace_text(profiling_action(repo), '-fprofile-instr-generate ', ''), 'Build Profiling action profiling-cxx-flags default must include -fprofile-instr-generate', 'required-snippets'),
            case(lambda repo: replace_text(profiling_action(repo), '-fprofile-update=atomic ', ''), 'Build Profiling action profiling-cxx-flags default must include -fprofile-update=atomic', 'required-snippets'),
            case(lambda repo: replace_text(profiling_action(repo), '-fprofile-update=atomic ', '-fprofile-update=atomic -fprofile-instr-use=/tmp/x265.profdata '), 'Build Profiling action profiling-cxx-flags default must not include PGO consume flags', 'required-snippets'),
            case(lambda repo: replace_text(profiling_action(repo), '    default: -O3 -flto=thin -fmerge-all-constants -I/usr/local/include', '    default: -O3 -flto=thin -fmerge-all-constants -fprofile-instr-generate -I/usr/local/include'), 'Build Profiling action common-cxx-flags default must not include profiling instrumentation or consume flags', 'required-snippets'),
            case(lambda repo: replace_text(build_workflow(repo), '    timeout-minutes: 15\n', '', count=1), 'build.yml job validate-ci-guardrails must declare a positive timeout-minutes', 'job-timeouts'),
            case(lambda repo: replace_text(update_deps_workflow(repo), "concurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: false\n\n", ''), 'Update-deps workflow must declare concurrency', 'update-deps-concurrency'),
            case(lambda repo: replace_text(build_workflow(repo), "cancel-in-progress: ${{ github.event_name == 'push' && !startsWith(github.ref, 'refs/tags/') }}", 'cancel-in-progress: true', count=1), 'Build workflow concurrency must cancel in-progress runs only for non-tag push events', 'build-workflow-concurrency'),
            case(lambda repo: replace_text(build_workflow(repo), "  CI_FULL_EVENT: ${{ (github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')) && 'true' || 'false' }}", "  CI_FULL_EVENT: 'true'", count=1), 'Build workflow env must define CI_FULL_EVENT for workflow_dispatch/tag full builds', 'build-workflow-concurrency'),
            case(lambda repo: replace_text(build_workflow(repo), '      fail-fast: false', '      fail-fast: true', count=1), 'Build workflow job build must set strategy.fail-fast to false so one CPU failure cannot cancel remaining dependency-coverage legs', 'build-matrix-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'target_cpu: ${{ fromJSON((github.event_name == \'workflow_dispatch\' || startsWith(github.ref, \'refs/tags/\')) && \'[\"x86-64\",\"haswell\",\"skylake\",\"alderlake\",\"raptorlake\",\"arrowlake\",\"znver2\",\"znver3\",\"znver4\",\"znver5\"]\' || \'[\"x86-64\",\"haswell\",\"alderlake\",\"znver4\"]\') }}', "target_cpu:\n          - x86-64\n          - haswell\n          - skylake\n          - alderlake\n          - raptorlake\n          - arrowlake\n          - znver2\n          - znver3\n          - znver4\n          - znver5"), 'Build workflow job build must use representative push CPU matrix and full tag/workflow_dispatch matrix', 'build-matrix-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "      - name: Run Python CI guard bundle\n        shell: bash", "      - name: Run Python CI guard bundle\n        if: github.event_name == 'push'\n        shell: bash", count=1), 'Build workflow Run Python CI guard bundle must not be step-gated', 'required-snippets'),
            case(lambda repo: replace_text(build_workflow(repo), "      - name: Check dependency patch cache suffixes\n        shell: bash", "      - name: Check dependency patch cache suffixes\n        if: github.event_name == 'push'\n        shell: bash", count=1), 'Build workflow Check dependency patch cache suffixes must not be step-gated', 'required-snippets'),
            case(lambda repo: replace_text(build_workflow(repo), "          sparse-checkout: |\n            .\n            .github\n            source", '          sparse-checkout: .', count=1), "validate-ci-guardrails Checkout X265 must use sparse-checkout '.\\n.github\\nsource\\n'", 'checkout-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          if [ "${{ github.event_name }}" != "push" ] || [[ "$before" =~ ^0+$ ]]; then', '          if true; then'), 'validate-deps-cache-suffix diff fallback must include: if [ "${{ github.event_name }}" != "push" ] || [[ "$before" =~ ^0+$ ]]; then', 'metadata-history-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '            echo "Before commit unavailable locally; fetching before commit"', '            echo "Before commit unavailable locally; skip fetch"'), 'validate-deps-cache-suffix diff fallback must include: echo "Before commit unavailable locally; fetching before commit"', 'metadata-history-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '              echo "Before commit fetch failed; skipping patch suffix diff validation"', '              echo "Before commit fetch failed"'), 'validate-deps-cache-suffix diff fallback must include: echo "Before commit fetch failed; skipping patch suffix diff validation"', 'metadata-history-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after"', '          echo "skip patch suffix diff validation"'), 'validate-deps-cache-suffix diff fallback must include: python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after"', 'metadata-history-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after"', '          python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after" --allow-missing-cache', count=1), 'validate-deps-cache-suffix diff fallback must run the exact before/after dependency suffix command without permissive extra flags', 'metadata-history-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          if ! git cat-file -e "$before^{commit}" 2>/dev/null; then', '          if ! git cat-file -e "$after^{commit}" 2>/dev/null; then', count=1), 'validate-deps-cache-suffix diff fallback must check before commit availability before and after fetch', 'metadata-history-scope'),
            case(lambda repo: replace_text(ci_version_helper(repo), '      git fetch --tags --deepen="$deepen" origin "${GITHUB_REF}"', '      git fetch --tags origin "${GITHUB_REF}"', count=1), 'CI version helper missing detail: git fetch --tags --deepen="$deepen" origin "${GITHUB_REF}"', 'metadata-history-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          if [ "${CI_FULL_EVENT}" = \'true\' ]; then', '          if true; then', count=1), 'Build workflow Fetch PGO Profdata must include: if [ "${CI_FULL_EVENT}" = \'true\' ]; then', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'fetch_output=$(git fetch --quiet origin "$branch" --depth=1 2>&1)', 'fetch_output=$(git ls-remote --exit-code --heads origin "$branch" 2>&1)'), 'Build workflow Fetch PGO Profdata must include: fetch_output=$(git fetch --quiet origin "$branch" --depth=1 2>&1)', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'fetch_output=$(git fetch --quiet origin "$branch" --depth=1 2>&1)', 'git ls-remote --exit-code --heads origin "$branch" >/dev/null\n              fetch_output=$(git fetch --quiet origin "$branch" --depth=1 2>&1)'), 'Build workflow Fetch PGO Profdata must not preflight branches with git ls-remote before git fetch', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '--required-ffmpeg-cache-suffix=pgo-v1-clang', '--required-ffmpeg-cache-suffix=full-v5-clang'), 'Build workflow Fetch PGO Profdata must include: --required-ffmpeg-cache-suffix=pgo-v1-clang', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                  --required-obuparse-cache-suffix="$obuparse_cache_suffix"\n', ''), 'Build workflow Fetch PGO Profdata must include: --required-obuparse-cache-suffix="$obuparse_cache_suffix"', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                  --required-lsmash-cache-suffix="$lsmash_cache_suffix"\n', ''), 'Build workflow Fetch PGO Profdata must include: --required-lsmash-cache-suffix="$lsmash_cache_suffix"', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                  --required-gop-muxer-cache-suffix="$gop_muxer_cache_suffix"\n', ''), 'Build workflow Fetch PGO Profdata must include: --required-gop-muxer-cache-suffix="$gop_muxer_cache_suffix"', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                if ! metadata_check_output=$(python .github/scripts/check_profdata_metadata.py "$metadata_path" "${metadata_check_args[@]}" 2>&1); then', '                if ! metadata_check_output=$(cat "$metadata_path" 2>&1); then'), 'Build workflow Fetch PGO Profdata must include: if ! metadata_check_output=$(python .github/scripts/check_profdata_metadata.py "$metadata_path" "${metadata_check_args[@]}" 2>&1); then', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                  --expected-branch="$branch"\n', ''), 'Build workflow Fetch PGO Profdata must include: --expected-branch="$branch"', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                  metadata_check_args+=(--expected-toolchain="$expected_toolchain")\n', ''), 'Build workflow Fetch PGO Profdata must include: metadata_check_args+=(--expected-toolchain="$expected_toolchain")', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                  --require-fresh-slot\n', ''), 'Build workflow Fetch PGO Profdata must include: --require-fresh-slot', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '                continue\n              fi\n\n              if ! git show "FETCH_HEAD:${source_path}" > "$destination" 2>/dev/null; then', '              fi\n\n              if ! git show "FETCH_HEAD:${source_path}" > "$destination" 2>/dev/null; then', count=1), 'Build workflow Fetch PGO Profdata must skip branches with missing metadata before copying profdata', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '            append_pgo_status 8b-lib skipped push "push path only consumes all-target profdata"', '            fetch_profdata 8b-lib profdata-${{ matrix.target_cpu }}-8b-lib profdata-x86-64-8b-lib x265.profdata', count=1), 'Build workflow Fetch PGO Profdata must include: append_pgo_status 8b-lib skipped push "push path only consumes all-target profdata"', 'pgo-fetch-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '      - name: Setup Shared Dependencies (Runtime Smokes)', '      - name: Setup Shared Dependencies'), 'missing job build step: Setup Shared Dependencies (Runtime Smokes)', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '      - name: Setup Shared Dependencies (Build Only)', '      - name: Setup Shared Dependencies'), 'missing job build step: Setup Shared Dependencies (Build Only)', 'windows-dependency-smoke-scope'),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "      - name: Setup Shared Dependencies (Runtime Smokes)\n        if: matrix.target_cpu == 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-cli-v3-clang",
                    "      - name: Setup Shared Dependencies (Runtime Smokes)\n        if: matrix.target_cpu == 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-cli-v4-clang",
                ),
                'Build workflow Setup Shared Dependencies (Runtime Smokes) must pin ffmpeg-cache-suffix=lavf-cli-v3-clang',
                'windows-dependency-smoke-scope',
            ),
            case(lambda repo: replace_text(build_workflow(repo), '          ffmpeg-cache-suffix: lavf-cli-v3-clang', '          ffmpeg-cache-suffix: lavf-v3-clang', count=1), 'Build workflow runtime-smoke FFmpeg cache suffix must differ from warning-scan library-only cache suffix', 'windows-dependency-smoke-scope'),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    '          ffmpeg-cache-suffix: lavf-v3-clang',
                    '          ffmpeg-cache-suffix: lavf-v4-clang',
                    count=2,
                ),
                'Build workflow Setup Shared Dependencies (Build Only) must pin ffmpeg-cache-suffix=lavf-v3-clang',
                'windows-dependency-smoke-scope',
            ),
            case(lambda repo: replace_text(build_workflow(repo), '              --enable-ffmpeg --enable-ffprobe --enable-avdevice --enable-avfilter', '              --enable-avdevice --enable-avfilter', count=1), 'Build workflow runtime-smoke FFmpeg config must enable dependency: --enable-ffmpeg', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '              --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe,hevc', '              --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe', count=1), 'Build workflow runtime-smoke FFmpeg config must enable dependency: --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe,hevc', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '              --enable-parser=h264,hevc', '              --enable-parser=h264', count=1), 'Build workflow runtime-smoke FFmpeg config must enable dependency: --enable-parser=h264,hevc', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '              --enable-encoder=wrapped_avframe,ffv1,rawvideo --enable-muxer=matroska,yuv4mpegpipe', '              --enable-encoder=rawvideo --enable-muxer=yuv4mpegpipe', count=1), 'Build workflow runtime-smoke FFmpeg config must enable dependency: --enable-encoder=wrapped_avframe,ffv1,rawvideo', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          use-gop-muxer: 'true'", "          use-gop-muxer: 'false'", count=1), 'Build workflow Setup Shared Dependencies (Runtime Smokes) must enable GOP muxer', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          use-mimalloc: 'true'", "          use-mimalloc: 'false'", count=1), 'Build workflow Setup Shared Dependencies (Runtime Smokes) must keep mimalloc enabled', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          use-obuparse: 'true'", "          use-obuparse: 'false'", count=1), 'Build workflow Setup Shared Dependencies (Runtime Smokes) must keep obuparse enabled', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          use-lsmash: 'true'", "          use-lsmash: 'false'", count=1), 'Build workflow Setup Shared Dependencies (Runtime Smokes) must keep L-SMASH enabled', 'windows-dependency-smoke-scope'),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "      - name: Setup Shared Dependencies (Build Only)\n        if: matrix.target_cpu != 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-v3-clang",
                    "      - name: Setup Shared Dependencies (Build Only)\n        if: matrix.target_cpu != 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-cli-v3-clang",
                ),
                'Build workflow build-only FFmpeg cache suffix must reuse warning-scan library-only cache suffix',
                'windows-dependency-smoke-scope',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "      - name: Setup Shared Dependencies (Build Only)\n        if: matrix.target_cpu != 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-v3-clang\n          ffmpeg-configure: |\n            ./configure --prefix=/usr/local --enable-gpl \\\n              --disable-runtime-cpudetect --disable-all --disable-autodetect \\\n              --disable-everything --disable-network \\\n              --enable-avformat --enable-avcodec --enable-avutil --enable-swscale \\\n              --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf",
                    "      - name: Setup Shared Dependencies (Build Only)\n        if: matrix.target_cpu != 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-v3-clang\n          ffmpeg-configure: |\n            ./configure --prefix=/usr/local --enable-gpl \\\n              --disable-runtime-cpudetect --disable-all --disable-autodetect \\\n              --disable-everything --disable-network \\\n              --enable-avformat --enable-avcodec --enable-avutil --enable-swscale \\\n              --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg",
                ),
                'Build workflow build-only FFmpeg config must enable compile dependency: --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf',
                'windows-dependency-smoke-scope',
            ),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "      - name: Setup Shared Dependencies (Build Only)\n        if: matrix.target_cpu != 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-v3-clang\n          ffmpeg-configure: |\n            ./configure --prefix=/usr/local --enable-gpl \\\n              --disable-runtime-cpudetect --disable-all --disable-autodetect \\\n              --disable-everything --disable-network \\\n              --enable-avformat --enable-avcodec --enable-avutil --enable-swscale \\\n              --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf",
                    "      - name: Setup Shared Dependencies (Build Only)\n        if: matrix.target_cpu != 'x86-64'\n        uses: ./x265/.github/actions/setup-windows-deps\n        with:\n          ffmpeg-cache-suffix: lavf-v3-clang\n          ffmpeg-configure: |\n            ./configure --prefix=/usr/local --enable-gpl \\\n              --disable-runtime-cpudetect --disable-all --disable-autodetect \\\n              --disable-everything --disable-network \\\n              --enable-avformat --enable-avcodec --enable-avutil --enable-swscale \\\n              --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe,hevc",
                ),
                'Build workflow build-only FFmpeg config must stay lightweight and omit: --enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe,hevc',
                'windows-dependency-smoke-scope',
            ),
            case(lambda repo: replace_text(build_workflow(repo), "          use-obuparse: ${{ env.CI_FULL_EVENT }}\n          use-lsmash: ${{ env.CI_FULL_EVENT }}\n          use-gop-muxer: 'false'", "          use-obuparse: ${{ env.CI_FULL_EVENT }}\n          use-lsmash: ${{ env.CI_FULL_EVENT }}\n          use-gop-muxer: 'true'", count=1), 'Build workflow Setup Shared Dependencies (Build Only) must disable GOP muxer', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          use-mimalloc: ${{ env.CI_FULL_EVENT }}", "          use-mimalloc: 'true'", count=1), 'Build workflow Setup Shared Dependencies (Build Only) must enable mimalloc only for workflow_dispatch/tag full builds', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          use-mimalloc: ${{ env.CI_FULL_EVENT }}\n          use-obuparse: ${{ env.CI_FULL_EVENT }}\n          use-lsmash: ${{ env.CI_FULL_EVENT }}", "          use-mimalloc: ${{ env.CI_FULL_EVENT }}\n          use-obuparse: 'false'\n          use-lsmash: ${{ env.CI_FULL_EVENT }}", count=1), 'Build workflow Setup Shared Dependencies (Build Only) must enable obuparse only for workflow_dispatch/tag full builds', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          use-obuparse: ${{ env.CI_FULL_EVENT }}\n          use-lsmash: ${{ env.CI_FULL_EVENT }}\n          use-gop-muxer: 'false'", "          use-obuparse: ${{ env.CI_FULL_EVENT }}\n          use-lsmash: 'false'\n          use-gop-muxer: 'false'", count=1), 'Build workflow Setup Shared Dependencies (Build Only) must enable L-SMASH only for workflow_dispatch/tag full builds', 'windows-dependency-smoke-scope'),
            case(
                lambda repo: replace_text(
                    build_workflow(repo),
                    "          use-gop-muxer: 'false'\n          extra-msys2-packages: ''",
                    "          use-gop-muxer: 'false'\n          extra-msys2-packages: mingw-w64-clang-x86_64-lldb",
                ),
                'Build workflow Setup Shared Dependencies (Build Only) must not preinstall extra MSYS2 packages',
                'windows-dependency-smoke-scope',
            ),
            case(lambda repo: replace_text(build_workflow(repo), "      - name: Smoke Test L-SMASH\n        if: matrix.target_cpu == 'x86-64'", '      - name: Smoke Test L-SMASH'), 'Build workflow Smoke Test L-SMASH must run only for the x86-64 representative build', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '            pacman -S --needed --noconfirm mingw-w64-clang-x86_64-lldb', '            echo skip-lldb-install'), 'Build workflow Smoke Test L-SMASH must include: pacman -S --needed --noconfirm mingw-w64-clang-x86_64-lldb', 'windows-dependency-smoke-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "          sparse-checkout: |\n            .\n            .github\n\n      - name: Get Latest Tag", "          sparse-checkout: .\n\n      - name: Get Latest Tag", count=1), "build-metadata Checkout X265 must use sparse-checkout '.\\n.github\\n'", 'checkout-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'run_ninja_retry_verbose() {', 'run_ninja_logged() {'), 'Build workflow Compile X265 must include: run_ninja_retry_verbose() {', 'build-log-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'echo "=== Ninja failed, rerunning verbose diagnostics: $dir -> $log ==="', 'echo "=== Verbose ninja: $dir -> $log ==="'), 'Build workflow Compile X265 must include: echo "=== Ninja failed, rerunning verbose diagnostics: $dir -> $log ==="', 'build-log-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '-DENABLE_LSMASH="${ENABLE_LSMASH}"', '-DENABLE_LSMASH=ON', count=1), 'Build workflow Compile X265 must include: -DENABLE_LSMASH="${ENABLE_LSMASH}"', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '-DUSE_MIMALLOC="${USE_MIMALLOC}"', '-DUSE_MIMALLOC=ON', count=1), 'Build workflow Compile X265 must include: -DUSE_MIMALLOC="${USE_MIMALLOC}"', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '"${ALL_BUILD_EXTRA_ARGS[@]}" \\', '', count=1), 'Build workflow Compile X265 must include: "${ALL_BUILD_EXTRA_ARGS[@]}"', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '              -DCMAKE_CXX_FLAGS="$CXX_FLAGS_ALL" \\\n', '              -DCMAKE_CXX_FLAGS="$CXX_FLAGS" \\\n', count=1), 'Build workflow Compile X265 representative smoke must include: -DCMAKE_CXX_FLAGS="$CXX_FLAGS_ALL"', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '            check_pgo_consume_commands build/10b "$PGO_ALL_FLAG" 60\n', '', count=1), 'Build workflow Compile X265 representative smoke must include: check_pgo_consume_commands build/10b "$PGO_ALL_FLAG" 60', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          cp build/10b/x265.exe build/all/x265.exe', '          # cp build/10b/x265.exe build/all/x265.exe'), 'Build workflow Compile X265 must include: cp build/10b/x265.exe build/all/x265.exe', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          if [ "$FULL_COMPILE" = true ]; then\n            require_pgo_flag 8b-lib "$PGO_8B_LIB_FLAG"\n            require_pgo_flag 12b-lib "$PGO_12B_LIB_FLAG"\n            require_pgo_flag all "$PGO_ALL_FLAG"\n            build_full_compile_matrix\n          fi', '          build_full_compile_matrix'), 'Build workflow Compile X265 must include: if [ "$FULL_COMPILE" = true ]; then', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          build_representative_compile_smoke\n          if [ "$FULL_COMPILE" = true ]; then', '          if [ "$FULL_COMPILE" = true ]; then'), 'Build workflow Compile X265 must always run representative compile smoke', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          if [ "$FULL_COMPILE" = true ]; then\n            require_pgo_flag 8b-lib "$PGO_8B_LIB_FLAG"\n            require_pgo_flag 12b-lib "$PGO_12B_LIB_FLAG"\n            require_pgo_flag all "$PGO_ALL_FLAG"\n            build_full_compile_matrix\n          fi', '          if [ "$FULL_COMPILE" = true ]; then\n            build_full_compile_matrix\n          fi', count=1), 'Build workflow Compile X265 must include: require_pgo_flag 8b-lib "$PGO_8B_LIB_FLAG"', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          require_pgo_flag() {\n            local label="$1"\n            local pgo_flag="$2"\n            if [ -z "$pgo_flag" ]; then\n              echo "::error::Missing required PGO profdata for $label" >&2\n              exit 1\n            fi\n          }\n', '', count=1), 'Build workflow Compile X265 must include: require_pgo_flag() {', 'build-compile-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "      - name: Package\n        if: env.CI_FULL_EVENT == 'true' || matrix.target_cpu == 'x86-64'", '      - name: Package'), 'Build workflow step Package must package push artifacts only for the x86-64 representative build', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), "      - name: Upload Artifact\n        if: env.CI_FULL_EVENT == 'true' || matrix.target_cpu == 'x86-64'", '      - name: Upload Artifact'), 'Build workflow step Upload Artifact must package push artifacts only for the x86-64 representative build', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          version=$(x265_latest_numeric_tag)', '          version="$GITHUB_REF_NAME"', count=1), 'build-metadata Get Latest Tag must include: version=$(x265_latest_numeric_tag)', 'metadata-history-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          source x265/.github/scripts/ci_version_helpers.sh', '          : # skip version helper', count=1), 'Build workflow Set Package Version must source the CI version helper', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '          version=$(x265_package_version_for_event "${{ needs.build-metadata.outputs.latest_tag }}" "${{ needs.build-metadata.outputs.ci_version }}")', '          version="${{ github.sha }}"', count=1), 'Build workflow Set Package Version must use x265_package_version_for_event with the build-metadata outputs', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe', '7z a -t7z -mx=9 ../x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe'), 'Build workflow Compress Package must use the runner-provided 7z executable', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe', 'pacman -S --needed --noconfirm p7zip\n          bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe'), 'Build workflow must use runner-provided 7z instead of installing p7zip', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '      - name: Verify Package Artifact\n        if: env.CI_FULL_EVENT == \'true\' || matrix.target_cpu == \'x86-64\'\n        run: |\n          expected_count=1\n          if [ "${CI_FULL_EVENT}" = \'true\' ]; then\n            expected_count=4\n          fi\n          bash x265/.github/scripts/verify_ci_archive.sh x265-release "x265-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z" artifact-check "${{ matrix.target_cpu }}" "$expected_count"\n', '      - name: Verify Package Artifact\n        if: env.CI_FULL_EVENT == \'true\' || matrix.target_cpu == \'x86-64\'\n        run: |\n          echo skip-package-verify\n', count=1), 'Build workflow Verify Package Artifact must validate the packaged release archive', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '      - name: Upload Artifact\n        if: env.CI_FULL_EVENT == \'true\' || matrix.target_cpu == \'x86-64\'\n        uses: actions/upload-artifact@v7', '      - name: Upload Artifact\n        if: env.CI_FULL_EVENT == \'true\' || matrix.target_cpu == \'x86-64\'\n        uses: actions/upload-artifact@v6', count=1), 'Build workflow Upload Artifact step must use actions/upload-artifact@v7', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '      - name: Upload Artifact\n        if: env.CI_FULL_EVENT == \'true\' || matrix.target_cpu == \'x86-64\'\n        uses: actions/upload-artifact@v7\n        with:\n          name: x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}\n          path: x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z\n          compression-level: 0', '      - name: Upload Artifact\n        if: env.CI_FULL_EVENT == \'true\' || matrix.target_cpu == \'x86-64\'\n        uses: actions/upload-artifact@v7\n        with:\n          name: x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}\n          path: x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z\n          compression-level: 9', count=1), 'Build workflow Upload Artifact step must set compression-level=0', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '    - name: Download Release Artifacts\n      uses: actions/download-artifact@v7', '    - name: Download Release Artifacts\n      uses: actions/download-artifact@v6', count=1), 'Build workflow Download Release Artifacts step must use actions/download-artifact@v7', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '    - name: Release Artifacts\n      uses: softprops/action-gh-release@v3', '    - name: Release Artifacts\n      uses: softprops/action-gh-release@v2', count=1), 'Build workflow Release Artifacts step must use softprops/action-gh-release@v3', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '        fail_on_unmatched_files: true', '        fail_on_unmatched_files: false', count=1), 'Build workflow Release Artifacts step must set fail_on_unmatched_files=True', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        llvm_profdata=$(command -v llvm-profdata.exe || command -v llvm-profdata)', '        llvm_profdata=/tmp/llvm-profdata.exe', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must resolve llvm-profdata from PATH', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        [ -f "$llvm_profdata" ] || llvm_profdata="${llvm_profdata}.exe"', '        : # skip llvm-profdata .exe normalization', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must normalize bare llvm-profdata paths to the .exe sibling when needed', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          /clang64/bin/*) ;;', '          /usr/bin/*) ;;', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must allow only the clang64 llvm-profdata path prefix', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        queue=("$llvm_profdata")', '        queue=()', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must seed DLL dependency traversal with llvm-profdata', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        version=$("$llvm_profdata" --version | sed -nE \'s/.*LLVM version ([0-9]+(\\.[0-9]+)+).*/\\1/p\' | head -1)', '        version="manual"', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must derive the package version from llvm-profdata --version', 'package-scope'),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    '        version=$("$llvm_profdata" --version | sed -nE \'s/.*LLVM version ([0-9]+(\\.[0-9]+)+).*/\\1/p\' | head -1)\n        test -n "$version"\n        echo "version=$version" >> "$GITHUB_OUTPUT"',
                    '        version=$("$llvm_profdata" --version | sed -nE \'s/.*LLVM version ([0-9]+(\\.[0-9]+)+).*/\\1/p\' | head -1)\n        : # skip llvm-profdata version non-empty check\n        echo "version=$version" >> "$GITHUB_OUTPUT"',
                    count=1,
                ),
                'Build Profiling workflow Package LLVM Profdata Tool must require a parsed llvm-profdata version before packaging',
                'package-scope',
            ),
            case(
                lambda repo: replace_text(
                    profiling_workflow(repo),
                    "    - name: Package LLVM Profdata Tool\n      id: llvm_profdata\n      run: |\n        llvm_profdata=$(command -v llvm-profdata.exe || command -v llvm-profdata)\n        test -n \"$llvm_profdata\"\n        [ -f \"$llvm_profdata\" ] || llvm_profdata=\"${llvm_profdata}.exe\"\n        test -f \"$llvm_profdata\"\n        case \"$llvm_profdata\" in\n          /clang64/bin/*) ;;\n          *) echo \"Unexpected llvm-profdata path: $llvm_profdata\" >&2; exit 1 ;;\n        esac\n        version=$(\"$llvm_profdata\" --version | sed -nE 's/.*LLVM version ([0-9]+(\\.[0-9]+)+).*/\\1/p' | head -1)\n        test -n \"$version\"\n        echo \"version=$version\" >> \"$GITHUB_OUTPUT\"",
                    "    - name: Package LLVM Profdata Tool\n      id: llvm_profdata\n      run: |\n        llvm_profdata=$(command -v llvm-profdata.exe || command -v llvm-profdata)\n        test -n \"$llvm_profdata\"\n        [ -f \"$llvm_profdata\" ] || llvm_profdata=\"${llvm_profdata}.exe\"\n        test -f \"$llvm_profdata\"\n        case \"$llvm_profdata\" in\n          /clang64/bin/*) ;;\n          *) echo \"Unexpected llvm-profdata path: $llvm_profdata\" >&2; exit 1 ;;\n        esac\n        version=$(\"$llvm_profdata\" --version | sed -nE 's/.*LLVM version ([0-9]+(\\.[0-9]+)+).*/\\1/p' | head -1)\n        test -n \"$version\"\n        echo \"tool=$version\" >> \"$GITHUB_OUTPUT\"",
                    count=1,
                ),
                'Build Profiling workflow Package LLVM Profdata Tool must publish the parsed llvm-profdata version',
                'package-scope',
            ),
            case(lambda repo: replace_text(profiling_workflow(repo), '        cp "$llvm_profdata" profdata-dist/', '        : # skip llvm-profdata staging copy', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must copy llvm-profdata.exe into profdata-dist before dependency staging', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), "            dll_key=$(printf '%s' \"$dll_name\" | tr '[:upper:]' '[:lower:]')", '            dll_key="$dll_name"', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must normalize DLL dependency names before deduping and whitelisting', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '            [ -z "${seen[$dll_key]:-}" ] || continue', '            : # skip seen-dll short-circuit', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must skip DLL dependencies already seen in the traversal', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        declare -a missing_dlls', '        # missing_dlls disabled', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must collect unresolved DLL dependencies', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          for base in /clang64/bin /usr/bin; do', '          for base in /usr/bin; do', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must search DLL dependencies in clang64 and system bin directories', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '                advapi32.dll|bcrypt.dll|kernel32.dll|msvcrt.dll|ntdll.dll|ole32.dll|shell32.dll|user32.dll|ws2_32.dll) ;;', '                kernel32.dll) ;;', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must tolerate the expected Windows system DLL set without packaging them', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '                seen[$dll_key]=missing', '                seen[$dll_key]=ignored', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must mark unresolved non-system DLL dependencies as missing', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '                missing_dlls+=("$dll_name")', '                echo "missing $dll_name" >&2', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must record unresolved non-system DLL dependency names', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '            seen[$dll_key]="$dll_path"', '            seen[$dll_key]=resolved', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must record resolved DLL dependency paths to avoid duplicate staging', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          cp "$dll_path" profdata-dist/', '          : # skip dll copy', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must copy resolved DLL dependencies into profdata-dist', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '            queue+=("$dll_path")', '            # queue+=("$dll_path")', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must recursively collect DLL dependencies', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          done < <(objdump -p "$current" | awk -F\': \' \'/DLL Name:/ { sub(/\\r$/, "", $2); print $2 }\')', '          done < <(objdump -p "$current")', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must extract DLL dependency names from objdump output', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          printf \'Missing DLL dependency for llvm-profdata package: %s\\n\' "${missing_dlls[@]}" >&2', '          echo "Missing DLL dependency for llvm-profdata package" >&2', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must fail on missing DLL dependencies', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        strip -s profdata-dist/llvm-profdata.exe', '        # strip -s profdata-dist/llvm-profdata.exe', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must strip llvm-profdata.exe', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        shopt -s nullglob', '        : # skip nullglob', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must enable nullglob before iterating packaged DLLs', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        for dll in profdata-dist/*.dll; do', '        for dll in *.dll; do', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must iterate packaged DLLs from profdata-dist', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          strip -s "$dll"', '          : # skip dll strip', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must strip packaged DLL dependencies', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '          packaged_dll_count=$((packaged_dll_count + 1))', '          packaged_dll_count=0', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must count packaged DLLs', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '        if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then', '        if false; then', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must write a package summary only when GITHUB_STEP_SUMMARY is available', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '            echo "### LLVM profdata package"', '            echo "### package"', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must title the step summary for llvm-profdata packaging', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '            echo "| tool | version | packaged_dlls |"', '            echo "| version | packaged_dlls |"', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must write the package summary table header', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '            echo "| $llvm_profdata | $version | $packaged_dll_count |"', '            echo "| $version | $packaged_dll_count |"', count=1), 'Build Profiling workflow Package LLVM Profdata Tool must record tool path, version, and packaged DLL count in the step summary', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), 'bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe', '7z a -t7z -mx=9 ../x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe'), 'Build Profiling workflow Compress Profiling Build must use the runner-provided 7z executable', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), 'bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z ./*', '7z a -t7z -mx=9 ../llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z ./*'), 'Build Profiling workflow Compress LLVM Profdata must use the runner-provided 7z executable', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '    - name: Verify Profiling Artifact\n      run: |\n        bash x265/.github/scripts/verify_ci_archive.sh x265-profiling "x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z" artifact-check-profiling "${{ matrix.target_cpu }}"\n', '    - name: Verify Profiling Artifact\n      run: |\n        echo skip-profiling-verify\n', count=1), 'Build Profiling workflow Verify Profiling Artifact must validate the packaged profiling archive', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '    - name: Verify LLVM Profdata Artifact\n      if: matrix.target_cpu == \'x86-64\'\n      run: |\n        bash x265/.github/scripts/verify_ci_archive.sh llvm-profdata "llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z" artifact-check-profdata\n', '    - name: Verify LLVM Profdata Artifact\n      if: matrix.target_cpu == \'x86-64\'\n      run: |\n        echo skip-profdata-verify\n', count=1), 'Build Profiling workflow Verify LLVM Profdata Artifact must validate the packaged profdata archive', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '    - name: Upload Combined Profiling Artifact\n      uses: actions/upload-artifact@v7', '    - name: Upload Combined Profiling Artifact\n      uses: actions/upload-artifact@v6', count=1), 'Build Profiling Upload Combined Profiling Artifact step must use actions/upload-artifact@v7', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '    - name: Upload Combined Profiling Artifact\n      uses: actions/upload-artifact@v7\n      with:\n        name: x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}\n        path: x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z\n        compression-level: 0\n        retention-days: 7', '    - name: Upload Combined Profiling Artifact\n      uses: actions/upload-artifact@v7\n      with:\n        name: x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}\n        path: x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z\n        compression-level: 0\n        retention-days: 1', count=1), 'Build Profiling Upload Combined Profiling Artifact step must set retention-days=7', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), "    - name: Upload LLVM Profdata Artifact\n      if: matrix.target_cpu == 'x86-64'\n      uses: actions/upload-artifact@v7", "    - name: Upload LLVM Profdata Artifact\n      if: matrix.target_cpu == 'x86-64'\n      uses: actions/upload-artifact@v6", count=1), 'Build Profiling Upload LLVM Profdata Artifact step must use actions/upload-artifact@v7', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '    - name: Download Profiling Artifacts\n      uses: actions/download-artifact@v7', '    - name: Download Profiling Artifacts\n      uses: actions/download-artifact@v6', count=1), 'Build Profiling Download Profiling Artifacts step must use actions/download-artifact@v7', 'package-scope'),
            case(lambda repo: replace_text(profiling_workflow(repo), '    - name: Release Profiling Artifacts\n      uses: softprops/action-gh-release@v3', '    - name: Release Profiling Artifacts\n      uses: softprops/action-gh-release@v2', count=1), 'Build Profiling Release Profiling Artifacts step must use softprops/action-gh-release@v3', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '    - name: Validate Release Assets', '    - name: Release Asset Validation Disabled', count=1), 'missing job publish-release step: Validate Release Assets', 'package-scope'),
            case(lambda repo: replace_text(release_asset_validator(repo), '    expected_count=10', '    expected_count=0', count=1), 'release asset validator missing detail: expected_count=10', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), '        bash x265/.github/scripts/validate_release_assets.sh release release-assets "${GITHUB_REF_NAME}"', '        bash x265/.github/scripts/validate_release_assets.sh release release-assets "${GITHUB_REF_NAME}" || true', count=1), 'Build workflow Validate Release Assets must run the shared release asset validator without softening wrappers or extra flags', 'package-scope'),
            case(lambda repo: replace_text(release_asset_validator(repo), '  printf \'Expected %d %s archives, found %d:\\n\' "$expected_count" "$count_label" "${#assets[@]}" >&2', '  echo "release archive count mismatch" >&2', count=1), 'release asset validator missing detail: printf \'Expected %d %s archives, found %d:\\n\' "$expected_count" "$count_label" "${#assets[@]}" >&2', 'package-scope'),
            case(lambda repo: replace_text(release_asset_validator(repo), '  printf \'  %s\\n\' "${assets[@]}" >&2', '  : # skip release asset listing', count=1), 'release asset validator missing detail: printf \'  %s\\n\' "${assets[@]}" >&2', 'package-scope'),
            case(lambda repo: replace_text(release_asset_validator(repo), "release_cpus='x86-64 haswell skylake alderlake raptorlake arrowlake znver2 znver3 znver4 znver5'", "release_cpus='x86-64'", count=1), "release asset validator missing detail: release_cpus='x86-64 haswell skylake alderlake raptorlake arrowlake znver2 znver3 znver4 znver5'", 'package-scope'),
            case(lambda repo: replace_text(release_asset_validator(repo), '      echo "Unexpected release archive: $asset" >&2', '      echo "release archive mismatch" >&2', count=1), 'release asset validator missing detail: echo "Unexpected release archive: $asset" >&2', 'package-scope'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_pgo_consume_commands()', 'check_pgo_consume_commands_disabled()'), 'expected exactly one PGO consume helper run block, found 0', 'pgo-consume-helper'),
            case(lambda repo: replace_text(profiling_smoke_helper(repo), './profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null', 'test -s "$profdata"'), 'profiling smoke helper missing detail: ./profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null', 'profiling-smoke-helper'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'build_x265_profiling.sh', 'check_cxx20_commands_profiling build/12b', 'echo skip-12b-guard'), 'build profiling helper missing detail: check_cxx20_commands_profiling build/12b', 'required-snippets'),
            case(lambda repo: replace_text(archive_verify_helper(repo), 'verify_x265_release()', 'verify_x265_release_disabled()'), 'archive verification helper missing function: verify_x265_release()', 'verify-ci-archive-helper'),
            case(
                lambda repo: replace_text(
                    archive_verify_helper(repo),
                    '  if [ "$expected_count" -eq 4 ]; then\n    for depth in 8bit 10bit 12bit; do\n      local exe="$extract_dir/x265-win64-${target_cpu}-${depth}.exe"\n      test -s "$exe"\n      run_with_isolated_path "$exe" --version >/dev/null\n    done\n  fi',
                    '  if [ "$expected_count" -eq 4 ]; then\n    for depth in 8bit 10bit 12bit; do\n      local exe="$extract_dir/x265-win64-${target_cpu}-${depth}.exe"\n      test -s "$exe"\n      "$exe" --version >/dev/null\n    done\n  fi',
                ),
                'archive verification helper missing release isolation: run_with_isolated_path "$exe" --version >/dev/null',
                'verify-ci-archive-helper',
            ),
            case(
                lambda repo: replace_text(
                    archive_verify_helper(repo),
                    '  for profile_class in 8b-lib 12b-lib all; do\n    local exe="$extract_dir/x265-profiling-win64-${target_cpu}-${profile_class}.exe"\n    test -s "$exe"\n    run_with_isolated_path "$exe" --version >/dev/null\n  done',
                    '  for profile_class in 8b-lib 12b-lib all; do\n    local exe="$extract_dir/x265-profiling-win64-${target_cpu}-${profile_class}.exe"\n    test -s "$exe"\n    "$exe" --version >/dev/null\n  done',
                ),
                'archive verification helper missing profiling isolation: run_with_isolated_path "$exe" --version >/dev/null',
                'verify-ci-archive-helper',
            ),
            case(lambda repo: replace_text(archive_verify_helper(repo), '  test -s "$extract_dir/llvm-profdata.exe"\n', '', count=1), 'archive verification helper missing function: test -s "$extract_dir/llvm-profdata.exe"', 'verify-ci-archive-helper'),
            case(lambda repo: replace_text(archive_verify_helper(repo), 'dll_count=$(find "$extract_dir" -maxdepth 1 -type f -iname \'*.dll\' | wc -l)', 'dll_count=0', count=1), 'archive verification helper missing function: dll_count=$(find "$extract_dir" -maxdepth 1 -type f -iname \'*.dll\' | wc -l)', 'verify-ci-archive-helper'),
            case(lambda repo: replace_text(archive_verify_helper(repo), 'run_with_isolated_path "$extract_dir/llvm-profdata.exe" --version >/dev/null', '"$extract_dir/llvm-profdata.exe" --version >/dev/null'), 'archive verification helper missing function: run_with_isolated_path "$extract_dir/llvm-profdata.exe" --version >/dev/null', 'verify-ci-archive-helper'),
            case(lambda repo: replace_text(ci_7z_helper(repo), 'find_ci_7z() {', 'find_ci_7z_disabled() {'), 'CI 7z helper missing detail: find_ci_7z() {', 'ci-7z-helper'),
            case(lambda repo: remove_repo_file(source_test_vector_checker(repo)), 'missing source test vector checker', 'source-test-vector-scripts'),
            case(lambda repo: remove_repo_file(source_test_vector_guard_test(repo)), 'missing source test vector guard test', 'source-test-vector-scripts'),
            case(lambda repo: replace_text(runtime_suite(repo), 'run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile nalu-file output-depth-invalid chunk-negative qpfile-oversized zonefile zonefile-oversized recon analysis-save-load 2pass-stats abr-ladder video-signal-type-preset-oversized gop-output', 'run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile nalu-file output-depth-invalid qpfile-oversized zonefile zonefile-oversized recon analysis-save-load 2pass-stats abr-ladder video-signal-type-preset-oversized gop-output'), 'Runtime smoke suite missing function or dispatch: run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile nalu-file output-depth-invalid chunk-negative qpfile-oversized zonefile zonefile-oversized recon analysis-save-load 2pass-stats abr-ladder video-signal-type-preset-oversized gop-output', 'runtime-smoke-suite'),
            case(lambda repo: replace_text(runtime_suite(repo), 'build/all/x265.exe --input smoke_raw.y4m', 'build/8b/x265.exe --input smoke_raw.y4m'), 'RAW smoke must run build/all/x265.exe, got build/8b/x265.exe', 'raw-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt", "grep -Fq 'threaded-me' smoke_threaded_me_log.txt"), 'Threaded ME smoke must require enabled threaded-me log', 'threaded-me-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'for iteration in $(seq 1 12); do', 'for iteration in $(seq 1 1); do'), 'Threaded ME stress smoke must run a 12-iteration loop', 'threaded-me-stress-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Input filename exceeds supported length' smoke_cli_long_input.log", "grep -Fq 'supported length' smoke_cli_long_input.log"), 'CLI long-input smoke must require oversized --input error log', 'cli-long-input-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '--frames 12 --output smoke_mkv.mkv', '--frames 8 --output smoke_mkv.mkv'), 'MKV smoke --frames must be 12, got 8', 'mkv-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '2>&1 | tee smoke_lavf_log.txt', '2>&1'), 'LAVF smoke must capture x265 log to smoke_lavf_log.txt', 'lavf-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '0 I 60', '0 I 22', count=1), 'QPFile smoke must require frame 0 I 60 entry', 'qpfile-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '# keep qpfile parser moving across ignored lines', '# comment removed', count=1), 'QPFile smoke must exercise ignored qpfile comment lines', 'qpfile-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'test "$(grep -c \'^I$\' smoke_qpfile_types.txt)" -eq 2', 'test "$(grep -c \'^I$\' smoke_qpfile_types.txt)" -eq 1', count=1), 'QPFile smoke must require a second qpfile-forced I frame after ignored lines', 'qpfile-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'test "$(wc -c < smoke_nalu_future.hevc)" -gt "$(wc -c < smoke_nalu_base.hevc)"', 'test "$(wc -c < smoke_nalu_future.hevc)" -ge "$(wc -c < smoke_nalu_base.hevc)"', count=1), 'Nalu-file smoke must require the future-POC SEI payload to survive until its frame is encoded', 'nalu-file-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'User SEI file contains a line exceeding supported length; skipping' smoke_nalu_long.log", "grep -Fq 'supported length' smoke_nalu_long.log"), 'Nalu-file smoke must require the oversized-line warning log', 'nalu-file-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'test "$(wc -c < smoke_nalu_long.hevc)" -eq "$(wc -c < smoke_nalu_base.hevc)"', 'test "$(wc -c < smoke_nalu_long.hevc)" -gt "$(wc -c < smoke_nalu_base.hevc)"', count=1), 'Nalu-file smoke must require oversized user SEI lines to be skipped without injecting truncated payload bytes', 'nalu-file-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'if build/all/x265.exe --output-depth 9 --help > smoke_output_depth_invalid.log 2>&1; then', 'build/all/x265.exe --output-depth 9 --help > smoke_output_depth_invalid.log 2>&1', count=1), 'Output-depth invalid smoke must actively require failure', 'output-depth-invalid-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'invalid argument: output-depth = 9' smoke_output_depth_invalid.log", "grep -Fq 'output-depth = 9' smoke_output_depth_invalid.log", count=1), 'Output-depth invalid smoke must require the invalid-argument log', 'output-depth-invalid-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "! grep -Fq 'falling back to default bit-depth' smoke_output_depth_invalid.log", "# ! grep -Fq 'falling back to default bit-depth' smoke_output_depth_invalid.log", count=1), 'Output-depth invalid smoke must reject fallback-to-default warnings', 'output-depth-invalid-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'if build/all/x265.exe --chunk-start -1 --help > smoke_chunk_start_negative.log 2>&1; then', 'build/all/x265.exe --chunk-start -1 --help > smoke_chunk_start_negative.log 2>&1', count=1), 'Chunk-negative smoke must actively require chunk-start failure', 'chunk-negative-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'invalid argument: chunk-start = -1' smoke_chunk_start_negative.log", "grep -Fq 'chunk-start = -1' smoke_chunk_start_negative.log", count=1), 'Chunk-negative smoke must require the chunk-start invalid-argument log', 'chunk-negative-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'if build/all/x265.exe --chunk-end -1 --help > smoke_chunk_end_negative.log 2>&1; then', 'build/all/x265.exe --chunk-end -1 --help > smoke_chunk_end_negative.log 2>&1', count=1), 'Chunk-negative smoke must actively require chunk-end failure', 'chunk-negative-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'invalid argument: chunk-end = -1' smoke_chunk_end_negative.log", "grep -Fq 'chunk-end = -1' smoke_chunk_end_negative.log", count=1), 'Chunk-negative smoke must require the chunk-end invalid-argument log', 'chunk-negative-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'QP file contains a line exceeding supported length' smoke_qpfile_longline.log", "grep -Fq 'supported length' smoke_qpfile_longline.log"), 'QPFile oversized smoke must require oversized-line parse error log', 'qpfile-oversized-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq \"can't parse qpfile for frame 1 in x265\" smoke_qpfile_longline.log", "grep -Fq \"can't parse qpfile\" smoke_qpfile_longline.log"), 'QPFile oversized smoke must require qpfile parse failure propagation log', 'qpfile-oversized-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '--bitrate 400 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc', '--bitrate 350 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc'), 'Zonefile smoke --bitrate must be 400, got 350', 'zonefile-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Zone file entry exceeds supported argument count' smoke_zonefile_oversized.log", "grep -Fq 'supported argument count' smoke_zonefile_oversized.log"), 'Zonefile oversized smoke must require argument-count error log', 'zonefile-oversized-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Zone file line 1 exceeds supported length' smoke_zonefile_longline.log", "grep -Fq 'supported length' smoke_zonefile_longline.log"), 'Zonefile oversized smoke must require long-line error log', 'zonefile-oversized-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '--recon smoke_recon_out.y4m --output smoke_recon.hevc', '--output smoke_recon.hevc'), 'missing Recon smoke value for --recon', 'recon-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'encoded 4 frames' smoke_analysis_load.log", "grep -Fq 'encoded frames' smoke_analysis_load.log"), 'Analysis save/load smoke must require load encoded-frame log', 'analysis-save-load-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq ' conformance-window-offsets right=0 bottom=0' smoke_2pass_stats.stats", "grep -Fq 'conformance-window-offsets right=0 bottom=0' smoke_2pass_stats.stats"), '2pass stats smoke must require spaced conformance-window offsets in stats header', '2pass-stats-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -q 'width=128' smoke_abr_scaled_probe.txt", "grep -q 'width=96' smoke_abr_scaled_probe.txt"), 'ABR ladder smoke must require 128-pixel scaled width', 'abr-ladder-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Incorrect system-id, aborting' smoke_vst_oversized.log", "grep -Fq 'system-id' smoke_vst_oversized.log"), 'Video-signal-type-preset oversized smoke must require invalid system-id log', 'video-signal-type-preset-oversized-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'test "$(wc -l < smoke_gop_data_files.txt)" -eq 2', '# test "$(wc -l < smoke_gop_data_files.txt)" -eq 2'), 'GOP smoke must require exactly two gop-data sidecars', 'gop-output-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt", "# awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt"), 'GOP smoke must require positive extradata_size in muxed MP4 stream', 'gop-output-smoke'),
            case(lambda repo: replace_text(mp4_suite(repo), 'run_mp4_smoke_targets smoke open-gop cra single-frame frames-zero single-frame-24000-1001 vui strict-cbr-fails frac-24000-1001 b-pyramid aud eos-eob idr-recovery', 'run_mp4_smoke_targets smoke open-gop cra single-frame frames-zero single-frame-24000-1001 vui strict-cbr-fails frac-24000-1001 b-pyramid aud eos-eob'), 'MP4 smoke suite missing function or dispatch: run_mp4_smoke_targets smoke open-gop cra single-frame frames-zero single-frame-24000-1001 vui strict-cbr-fails frac-24000-1001 b-pyramid aud eos-eob idr-recovery', 'mp4-smoke-suite'),
            case(lambda repo: replace_text(mp4_suite(repo), '--no-open-gop --output smoke.mp4', '--open-gop --output smoke.mp4'), 'missing MP4 smoke argument: --no-open-gop', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), "assert_mp4_markers smoke_open.mp4 iso6 sgpd sbgp 'rap '", 'assert_mp4_markers smoke_open.mp4 iso6 hvc1 hvcC'), 'MP4 open-GOP smoke must require sample-group markers', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--cra-nal --output smoke_cra.mp4', '--output smoke_cra.mp4'), 'missing MP4 CRA smoke argument: --cra-nal', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), 'make_y4m smoke_single.y4m 24 1 yuv420p', 'make_y4m smoke_single.y4m 24 2 yuv420p'), 'MP4 single-frame smoke must generate 1-frame yuv420p input', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), 'assert_single_frame_mp4 smoke_single_frac 0.06 0.03 0.06', 'assert_single_frame_mp4 smoke_single_frac 0.04 0.01 0.04'), 'MP4 single-frame 24000/1001 smoke must require single-frame timing window', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--frames 0 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4', '--frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4'), 'MP4 frames=0 smoke --frames must be 0, got 1', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--sar 4:3 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4', '--sar 1:1 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4'), 'MP4 VUI smoke --sar must be 4:3, got 1:1', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--strict-cbr --hrd --output smoke_strict_cbr.mp4', '--strict-cbr --output smoke_strict_cbr.mp4'), 'missing MP4 strict-CBR smoke argument: --hrd', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 13) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv", "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv"), 'MP4 24000/1001 smoke must require second key packet at packet 13', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--bframes 4 --b-pyramid --keyint 8', '--bframes 4 --keyint 8'), 'missing MP4 B-pyramid smoke argument: --b-pyramid', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--aud --output smoke_aud.mp4', '--output smoke_aud.mp4'), 'missing MP4 AUD smoke argument: --aud', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--eos --eob --output smoke_eos.mp4', '--eos --output smoke_eos.mp4'), 'missing MP4 EOS/EOB smoke argument: --eob', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--no-open-gop --idr-recovery-sei --output smoke_recovery.mp4', '--no-open-gop --output smoke_recovery.mp4'), 'missing MP4 IDR recovery smoke argument: --idr-recovery-sei', 'mp4-smokes'),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/x265.cpp'), 'void* ptr = NULL;\n'),
                ),
                'use nullptr instead of NULL in CLI entrypoint C++ sources',
                'cli-nullptr-usage',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/abrEncApp.cpp'), 'static volatile int bad_flag = 0;\n'),
                ),
                'limit volatile usage to reviewed GNU++20 signal-handler and Windows API boundary sites',
                'cli-volatile-usage',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/dynamicHDR10/json11/json11.h'), '#define JSON11_NOEXCEPT throw()\n'),
                    write_repo_file(repo, Path('source/dynamicHDR10/json11/json11.cpp'), 'Json::Json() throw() {}\n'),
                ),
                'avoid old-style throw() exception specifications',
                'json11-noexcept-usage',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/dynamicHDR10/json11/json11.cpp'), "Json parse_number() {\n    if (str[i] == '-')\n        i++;\n}\n"),
                ),
                'forbidden json11 number boundary regression',
                'json11-number-boundary-safety',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/dynamicHDR10/json11/json11.cpp'), "string parse_string() {\n    string esc = str.substr(i, 4);\n    long codepoint = strtol(esc.data(), nullptr, 16);\n    i += 4;\n}\n"),
                ),
                'forbidden json11 unicode escape regression',
                'json11-unicode-escape-parse-safety',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/dynamicHDR10/json11/json11.cpp'), "Json parse_number() {\n    return static_cast<int>(std::strtol(str.c_str() + start_pos, nullptr, 10));\n}\n"),
                ),
                'forbidden json11 short-int regression',
                'json11-short-int-parse-safety',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/dynamicHDR10/json11/json11.cpp'), "Json parse_number() {\n    return std::strtod(str.c_str() + start_pos, nullptr);\n}\n"),
                ),
                'forbidden json11 slow-float regression',
                'json11-slow-float-token-bounds',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/common/common.h'), '#ifndef NULL\n#define NULL 0\n'),
                ),
                'remove legacy internal NULL macro from common header',
                'source-null-exception-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/common.cpp'),
                    '\n'.join((
                        'char* x265_slurp_file(const char *filename)',
                        '{',
                        '    size_t fSize;',
                        '    bError |= (fSize = std::ftell(fh)) <= 0;',
                        '    buf = X265_MALLOC(char, fSize + 2);',
                        '}',
                    )) + '\n',
                ),
                'forbidden common slurp size regression: bError |= (fSize = std::ftell(fh)) <= 0;',
                'common-slurp-size-guard',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/common/ringmem.cpp'),
                        '\n'.join((
                            'std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SHARED_MEM_NAME, name);',
                            'std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SEMAPHORE_RINGMEM_WRITER_NAME, name);',
                            'std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SEMAPHORE_RINGMEM_READER_NAME, name);',
                            'unlink(m_filepath);',
                            'std::free(m_filepath);',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/common/threading.h'),
                        '\n'.join((
                            'm_name = strdup(name);',
                            'ret = true;',
                            'sem_unlink(m_name);',
                            'm_sem = nullptr;',
                        )) + '\n',
                    ),
                ),
                'forbidden cutree shared-memory name regression: std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SHARED_MEM_NAME, name);',
                'cutree-sharedmem-name-guard',
            ),
            case(
                lambda repo: (
                    write_repo_file(
                        repo,
                        Path('source/output/y4m.cpp'),
                        '\n'.join((
                            'Y4MOutput::Y4MOutput(const char* filename, int w, int h, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int inputdepth)',
                            '{',
                            '    buf = new char[width];',
                            '}',
                        )) + '\n',
                    ),
                    write_repo_file(
                        repo,
                        Path('source/output/yuv.cpp'),
                        '\n'.join((
                            '#include <new>',
                            'YUVOutput::YUVOutput(const char *filename, int w, int h, uint32_t d, int csp, int inputdepth)',
                            '{',
                            '    buf = new (std::nothrow) char[width];',
                            '    if (!buf)',
                            '    {',
                            '        failed = true;',
                            '        return;',
                            '    }',
                            '}',
                        )) + '\n',
                    ),
                ),
                'forbidden row-buffer allocation regression: buf = new char[width];',
                'y4m-yuv-row-buffer-alloc-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/output/output.cpp'),
                    '\n'.join((
                        '#include <new>',
                        'ReconFile* ReconFile::open(const char *fname, int width, int height, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int sourceBitDepth)',
                        '{',
                        '    ReconFile* output = new Y4MOutput(fname, width, height, bitdepth, fpsNum, fpsDenom, csp, sourceBitDepth);',
                        '    if (!output)',
                        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate Y4M recon output\\n");',
                        '    output = new (std::nothrow) YUVOutput(fname, width, height, bitdepth, csp, sourceBitDepth);',
                        '    if (!output)',
                        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV recon output\\n");',
                        '}',
                        'OutputFile* OutputFile::open(const char *fname, InputFileInfo& inputInfo)',
                        '{',
                        '    OutputFile* output = new (std::nothrow) MKVOutput(fname, inputInfo);',
                        '    if (!output)',
                        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MKV output\\n");',
                        '    output = new (std::nothrow) MP4Output(fname, inputInfo);',
                        '    if (!output)',
                        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MP4 output\\n");',
                        '    output = new (std::nothrow) GOPOutput(fname, inputInfo);',
                        '    if (!output)',
                        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate GOP output\\n");',
                        '    output = new (std::nothrow) RAWOutput(fname, inputInfo);',
                        '    if (!output)',
                        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate raw output\\n");',
                        '}',
                    )) + '\n',
                ),
                'forbidden output open allocation regression: new Y4MOutput(',
                'output-open-alloc-guards',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/output/mp4.cpp'),
                    '\n'.join((
                        '#include <new>',
                        'bool MP4Muxer::configureParameterSets(const x265_nal* nal, uint32_t nalcount)',
                        '{',
                        '    uint8_t* newSeiBuffer = nullptr;',
                        '    uint32_t newSeiSize = 0;',
                        '    newSeiBuffer = new uint8_t[newSeiSize];',
                        '    if (!newSeiBuffer)',
                        '        return failSeiAssembly("failed to allocate sei transition buffer.\\n");',
                        '    return true;',
                        '}',
                    )) + '\n',
                ),
                'forbidden MP4 header SEI allocation regression: newSeiBuffer = new uint8_t[newSeiSize];',
                'mp4-header-sei-alloc-guard',
            ),
            case(
                lambda repo: (
                    seed_gnu20_foundation_sources(repo),
                    write_repo_file(repo, Path('source/x265.h'), 'void* bad = NULL;\n'),
                ),
                'remove runtime NULL tokens from public header implementations',
                'remaining-null-boundaries',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
                        '{',
                        "    if (parseOptionUintPair(value, '/', numerator, denominator))",
                        '        return true;',
                        '}',
                        'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
                    )) + '\n',
                ),
                'forbidden fps parse regression',
                'fps-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("frame-threads") p->frameNumThreads = x265_atoi(value, bError);\n',
                ),
                'forbidden frame-threads regression',
                'frame-threads-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("total-frames") p->totalFrames = x265_atoi(value, bError);\n',
                ),
                'forbidden total-frames regression',
                'total-frames-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        '#define atoi(str) x265_atoi(str, bError)',
                        '#define atof(str) x265_atof(str, bError)',
                        '#define atobool(str) (x265_atobool(str, bError))',
                        'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)',
                        '{',
                        '    OPT("masking-strength") bError = parseMaskingStrength(p, value);',
                        '}',
                    )) + '\n',
                ),
                'forbidden scenecut-aware QP macro regression',
                'scenecut-qp-macro-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        '/* internal versions of string-to-int with additional error checking */',
                        '#undef atoi',
                        '#undef atof',
                        '#define atoi(str) x265_atoi(str, bError)',
                        '#define atof(str) x265_atof(str, bError)',
                        '#define atobool(str) (x265_atobool(str, bError))',
                        'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
                        '{',
                        '    OPT("fast-intra") p->bEnableFastIntra = atobool(value);',
                        '}',
                    )) + '\n',
                ),
                'forbidden zone param macro regression',
                'zone-param-macro-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        '/* internal versions of string-to-int with additional error checking */',
                        '#undef atoi',
                        '#undef atof',
                        '#define atoi(str) x265_atoi(str, bError)',
                        '#define atof(str) x265_atof(str, bError)',
                        '#define atobool(str) (bNameWasBool = true, x265_atobool(str, bError))',
                        'int x265_param_parse(x265_param* p, const char* name, const char* value)',
                        '{',
                        '    OPT("pmode")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bDistributeModeAnalysis = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("pme")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bDistributeMotionEstimation = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("high-tier")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bHighTier = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("allow-non-conformance")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bAllowNonConformance = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("rect")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableRectInter = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("amp")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableAMP = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("temporal-mvp")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableTemporalMvp = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("early-skip")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableEarlySkip = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("tskip")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableTransformSkip = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("no-tskip-fast")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableTSkipFast = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("tskip-fast")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableTSkipFast = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("strong-intra-smoothing")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableStrongIntraSmoothing = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("lossless")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bLossless = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("cu-lossless")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bCULossless = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("constrained-intra")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableConstrainedIntra = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("fast-intra")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableFastIntra = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("open-gop")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bOpenGOP = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("intra-refresh")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bIntraRefresh = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("annexb")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bAnnexB = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("repeat-headers")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bRepeatHeaders = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("wpp")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableWavefront = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("limit-modes")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->limitModes = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("weightp")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableWeightedPred = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("weightb")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableWeightedBiPred = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("rd-refine")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableRdRefine = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("signhide")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableSignHiding = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("b-intra")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bIntraInBFrames = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("sao")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableSAO = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("sao-non-deblock")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bSaoNonDeblocked = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("ssim")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableSsim = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("psnr")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnablePsnr = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("aud")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEnableAccessUnitDelimiters = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("info")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEmitInfoSEI = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("b-pyramid")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bBPyramid = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("hrd")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->bEmitHRDSEI = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("hevc-aq")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->rc.hevcAq = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("limit-aq1")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->rc.limitAq1 = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("rc-grain")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->rc.bEnableGrain = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("cutree")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->rc.cuTree = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("slow-firstpass")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->rc.bEnableSlowFirstPass = x265_atobool(value, bError);',
                        '    }',
                        '    OPT("uhd-bd")',
                        '    {',
                        '        bNameWasBool = true;',
                        '        p->uhdBluray = x265_atobool(value, bError);',
                        '    }',
                        '        OPT("analyze-src-pics")',
                        '        {',
                        '            bNameWasBool = true;',
                        '            p->bSourceReferenceEstimation = x265_atobool(value, bError);',
                        '        }',
                        '        OPT("vui-timing-info")',
                        '        {',
                        '            bNameWasBool = true;',
                        '            p->bEmitVUITimingInfo = x265_atobool(value, bError);',
                        '        }',
                        '        OPT("vui-hrd-info")',
                        '        {',
                        '            bNameWasBool = true;',
                        '            p->bEmitVUIHRDInfo = x265_atobool(value, bError);',
                        '        }',
                        '}',
                    )) + '\n',
                ),
                'forbidden param parse macro regression',
                'param-parse-macro-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'static bool parseTenthsOrIntegerLevel(const char* value, int& parsedLevel)',
                        '{',
                        '    parsedLevel = (int)(10 * decimalLevel + .5);',
                        '    return true;',
                        '}',
                        'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
                    )) + '\n',
                ),
                'forbidden level-idc parse regression',
                'level-idc-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
                        '{',
                        '    bool bLocalError = false;',
                        '    parsedValue = x265_atoi(value, bLocalError);',
                        '    if (!bLocalError)',
                        '        return true;',
                        '}',
                        'static bool parseBoolOrIntValue(const char* value, int& parsedValue)',
                    )) + '\n',
                ),
                'forbidden log level parse regression',
                'log-level-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("qpstep") p->rc.qpStep = x265_atoi(value, bError);\n',
                ),
                'forbidden qpstep regression',
                'qpstep-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("qscale-mode") p->rc.qScaleMode = x265_atoi(value, bError);\n',
                ),
                'forbidden qscale-mode regression',
                'qscale-mode-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("subme") p->subpelRefine = x265_atoi(value, bError);\n',
                ),
                'forbidden subme regression',
                'subme-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'if (!this->input[i] || this->input[i]->isFail())\nreturn true;\n',
                ),
                'missing CLI input open cleanup guardrail',
                'cli-input-open-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'if (info[i].depth < 8 || info[i].depth > 16)\nreturn true;\n',
                ),
                'missing CLI input validation cleanup guardrail',
                'cli-input-validation-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'if (!this->output || this->output->isFail())\nreturn true;\n',
                ),
                'missing CLI output open cleanup guardrail',
                'cli-output-open-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'if (api->param_apply_profile(param, profile))\nreturn true;\n',
                ),
                'missing CLI profile apply cleanup guardrail',
                'cli-profile-apply-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'x265_log(param, X265_LOG_ERROR, "recon file name must include a non-empty base name for alpha or multiview output\\n");\nreturn true;\n',
                ),
                'missing CLI recon basename cleanup guardrail',
                'cli-recon-basename-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'x265_log(param, X265_LOG_ERROR, "unable to open VMAF input files\\n");\nreturn true;\n',
                ),
                'missing CLI VMAF input-open cleanup guardrail',
                'cli-vmaf-input-open-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'x265_log(param, X265_LOG_ERROR, "recon file must be specified to get VMAF score, try --help for help\\n");\nreturn true;\n',
                ),
                'missing CLI VMAF recon precondition cleanup guardrail',
                'cli-vmaf-recon-preconditions-cleanup',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/x265cli.cpp'),
                    'this->recon[i] = ReconFile::open(filename, info);\n',
                ),
                'missing CLI recon open guardrail',
                'cli-recon-open-guard',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'encoder->m_svtAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
                        'encoder->m_svtAppData->inputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
                        'svt_release_app_context(encoder);',
                        '        return false;',
                    )) + '\n',
                ),
                'forbidden SVT app-context staging regression',
                'svt-app-context-staging',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'dst->svtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                        'if (!dst->svtHevcParam)',
                        'memcpy(dst->svtHevcParam, src->svtHevcParam, sizeof(EB_H265_ENC_CONFIGURATION));',
                    )) + '\n',
                ),
                'forbidden SVT param storage regression',
                'svt-param-storage-replace-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'uint8_t* buffer = X265_MALLOC(uint8_t, outputPtr->nFilledLen);',
                        'if (!buffer)',
                        'nalList.m_buffer = buffer;',
                    )) + '\n',
                ),
                'forbidden SVT NAL buffer replace regression',
                'svt-nal-buffer-replace-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/nal.cpp'),
                    '\n'.join((
                        'void NALList::takeContents(NALList& other)',
                        '{',
                        '    other.m_buffer = X265_MALLOC(uint8_t, m_allocSize);',
                        '}',
                    )) + '\n',
                ),
                'forbidden NAL takeContents realloc regression',
                'nal-takecontents-realloc-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/api.cpp'),
                    '\n'.join((
                        'if (inputData->dolbyVisionRpu.payload && encoder->m_svtAppData->dolbyVisionRpuCapacity < payloadSize)',
                        'inputData->dolbyVisionRpu.payload = X265_MALLOC(uint8_t, payloadSize);',
                    )) + '\n',
                ),
                'forbidden SVT RPU payload replace regression',
                'svt-rpu-payload-replace-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/encoder/encoder.cpp'),
                    '\n'.join((
                        'std::memcpy(zone, p, sizeof(x265_param));',
                        'zone->svtHevcParam = zoneSvtHevcParam;',
                        'if (p->svtHevcParam)',
                        '{',
                        '    zoneSvtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                        '}',
                    )) + '\n',
                ),
                'missing configureZone SVT staging guardrail',
                'configure-zone-svt-staging',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        '                            svtHevcParam->targetSocket = 1;',
                        '                            svtHevcParam->logicalProcessors = x265_atoi(temp2, bLogicalProcessorsError);',
                    )) + '\n',
                ),
                'forbidden SVT pools regression',
                'svt-pools-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'if (strtol(value, nullptr, 0))\n',
                ),
                'forbidden SVT deblock parse regression',
                'svt-deblock-parse-usage',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'svtHevcParam->threadCount = (uint32_t)x265_atoi(value, bError);\n',
                ),
                'forbidden SVT frame-threads regression',
                'svt-frame-threads-parse-safety',
            ),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_dependency_patch_suffixes.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'dependency-suffixes'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_release_needs.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'release-needs'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_compile_commands.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'compile-commands'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_profdata_metadata.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'profdata-metadata'),
            case(
                lambda repo: replace_text(
                    python_ci_guard_bundle_runner(repo),
                    "script_dir.glob('test_check_*.py')",
                    "script_dir.glob('test_check_gnu20_legacy_guard_bundle_disabled.py')",
                ),
                "Python CI guard bundle runner missing detail: script_dir.glob('test_check_*.py')",
                'required-snippets',
            ),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_pgo_consume_chain.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'pgo-consume-chain'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_source_test_vectors.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'source-test-vectors'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_source_legacy_patterns.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'source-legacy-patterns'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_all_source_legacy_patterns.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'all-source-legacy-patterns'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_csvlog_reopen_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'csvlog-reopen-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_cli_config_file_parse_usage.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'cli-config-file-parse-usage'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_csv_log_level_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'csv-log-level-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_common_logfile_open_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'common-logfile-open-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_common_logfile_close_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'common-logfile-close-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_intra_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-intra-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_inter_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-inter-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_inter_motion_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-inter-motion-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_inter_temp_luma_alloc_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-inter-temp-luma-alloc-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_inter_depth_run_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-inter-depth-run-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_cache_cost_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-cache-cost-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_scaled_analysis_load_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'scaled-analysis-load-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_2pass_load_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-2pass-load-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_nal_takecontents_realloc_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'nal-takecontents-realloc-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_picyuv_offset_rollback.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'picyuv-offset-rollback'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_motion_reference_init_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'motion-reference-init-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_motionestimate_init_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'motionestimate-init-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_motion_sea_scratch_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'motion-sea-scratch-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_scaler_slice_linebuf_init.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'scaler-slice-linebuf-init'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_load_staging_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-load-staging-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_atc_sei_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'atc-sei-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_chunk_start_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'chunk-start-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_chunk_end_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'chunk-end-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_deblock_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'deblock-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_hash_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'hash-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_hme_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'hme-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_lookahead_slices_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'lookahead-slices-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_merange_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'merange-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_misc_control_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'misc-control-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_vbv_fullness_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'vbv-fullness-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_zonefile_startframe_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'zonefile-startframe-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_reconfig_window_size_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'reconfig-window-size-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_no_reset_zone_prefill_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'no-reset-zone-prefill-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_view_layer_limit_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'view-layer-limit-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_pic_struct_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'pic-struct-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_psy_scale_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'psy-scale-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_rskip_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'rskip-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_rskip_edge_threshold_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'rskip-edge-threshold-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_sar_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'sar-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_selective_sao_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'selective-sao-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_ssim_rd_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'ssim-rd-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_temporal_layers_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'temporal-layers-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_uint32_token_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'uint32-token-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_json11_number_boundary_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'json11-number-boundary-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_json11_unicode_escape_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'json11-unicode-escape-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_json11_short_int_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'json11-short-int-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_json11_slow_float_token_bounds.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'json11-slow-float-token-bounds'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_scenecut_qp_macro_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'scenecut-qp-macro-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_zone_param_macro_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'zone-param-macro-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_param_parse_macro_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'param-parse-macro-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_cli_inputfn_alloc_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'cli-inputfn-alloc-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_cli_vmaf_format_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'cli-vmaf-format-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_input_filename_copy_usage.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'input-filename-copy-usage'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_print_status_progress_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'print-status-progress-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_recon_basename_parse_usage.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'recon-basename-parse-usage'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_zonefile_parse_no_exit.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'zonefile-parse-no-exit'),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("aud") svtHevcParam->accessUnitDelimiter = x265_atobool(value, bError);\n',
                ),
                'forbidden SVT aud regression',
                'svt-aud-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-base-layer-switch-mode") svtHevcParam->baseLayerSwitchMode = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT base-layer-switch-mode regression',
                'svt-base-layer-switch-mode-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-compressed-ten-bit-format") svtHevcParam->compressedTenBitFormat = x265_atobool(value, bError);\n',
                ),
                'forbidden SVT compressed-ten-bit-format regression',
                'svt-compressed-ten-bit-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("constrained-intra") svtHevcParam->constrainedIntra = (uint8_t)x265_atobool(value, bError);\n',
                ),
                'forbidden SVT constrained-intra regression',
                'svt-constrained-intra-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-fps-in-vps") svtHevcParam->fpsInVps = (uint8_t)x265_atobool(value, bError);\n',
                ),
                'forbidden SVT fps-in-vps regression',
                'svt-fps-in-vps-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("total-frames") svtHevcParam->framesToBeEncoded = x265_atoi(value, bError);',
                        'OPT("frames") svtHevcParam->framesToBeEncoded = x265_atoi(value, bError);',
                    )) + '\n',
                ),
                'forbidden SVT total-frames regression',
                'svt-frames-to-be-encoded-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("hdr") svtHevcParam->highDynamicRangeInput = x265_atobool(value, bError);\n',
                ),
                'forbidden SVT hdr regression',
                'svt-hdr-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-hierarchical-level") svtHevcParam->hierarchicalLevels = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT hierarchical-level regression',
                'svt-hierarchical-level-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("high-tier") svtHevcParam->tier = x265_atobool(value, bError);\n',
                ),
                'forbidden SVT high-tier regression',
                'svt-high-tier-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'svtHevcParam->hrdFlag = (uint32_t)x265_atobool(value, bError);\n',
                ),
                'forbidden SVT hrd regression',
                'svt-hrd-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("input-depth") svtHevcParam->encoderBitDepth = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT input-depth regression',
                'svt-input-depth-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("keyint") svtHevcParam->intraPeriodLength = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT keyint regression',
                'svt-keyint-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("master-display") svtHevcParam->useMasteringDisplayColorVolume = parseOptionUint8Token(value, std::strlen(value), bError);\n',
                ),
                'forbidden SVT master-display regression',
                'svt-master-display-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("nalu-file") svtHevcParam->useNaluFile = parseOptionUint8Token(value, std::strlen(value), bError);\n',
                ),
                'forbidden SVT nalu-file regression',
                'svt-nalu-file-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-pred-struct") svtHevcParam->predStructure = parseOptionUint8Token(value, std::strlen(value), bError);\n',
                ),
                'forbidden SVT pred-struct regression',
                'svt-pred-struct-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("qpmax") svtHevcParam->maxQpAllowed = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT qpmax regression',
                'svt-qpmax-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("qpmin") svtHevcParam->minQpAllowed = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT qpmin regression',
                'svt-qpmin-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("rc-lookahead") svtHevcParam->lookAheadDistance = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT rc-lookahead regression',
                'svt-rc-lookahead-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("sao") svtHevcParam->enableSaoFlag = (uint8_t)x265_atobool(value, bError);\n',
                ),
                'forbidden SVT SAO regression',
                'svt-sao-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'svtHevcParam->sceneChangeDetection = x265_atobool(value, bError);\n',
                ),
                'forbidden SVT scenecut regression',
                'svt-scenecut-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-search-height") svtHevcParam->searchAreaHeight = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT search-height regression',
                'svt-search-height-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-search-width") svtHevcParam->searchAreaWidth = x265_atoi(value, bError);\n',
                ),
                'forbidden SVT search-width regression',
                'svt-search-width-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("svt-speed-control") svtHevcParam->speedControlFlag = x265_atobool(value, bError);\n',
                ),
                'forbidden SVT speed-control regression',
                'svt-speed-control-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'svtHevcParam->vbvBufsize = (uint32_t)x265_atoi(value, bError);\n',
                ),
                'forbidden SVT vbv-bufsize regression',
                'svt-vbv-bufsize-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'svtHevcParam->vbvBufInit = (uint64_t)x265_atof(value, bError);\n',
                ),
                'forbidden SVT vbv-init regression',
                'svt-vbv-init-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'svtHevcParam->vbvMaxrate = (uint32_t)x265_atoi(value, bError);\n',
                ),
                'forbidden SVT vbv-maxrate regression',
                'svt-vbv-maxrate-parse-safety',
            ),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_abr_analysis_slot_wait_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'abr-analysis-slot-wait'),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'OPT("vui-timing-info") svtHevcParam->videoUsabilityInfo = x265_atobool(value, bError);\n',
                ),
                'forbidden SVT vui-timing-info regression',
                'svt-vui-timing-info-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("svt-hme")',
                        '{',
                        '    svtHevcParam->enableHmeFlag = (uint8_t)x265_atobool(value, bError);',
                        '    if (svtHevcParam->enableHmeFlag) svtHevcParam->useDefaultMeHme = 1;',
                        '}',
                    )) + '\n',
                ),
                'forbidden SVT HME regression',
                'svt-hme-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'svtHevcParam->interlacedVideo = (uint8_t)x265_atobool(value, bError);\n',
                ),
                'forbidden SVT interlace regression',
                'svt-interlace-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    '\n'.join((
                        'OPT("open-gop")',
                        '{',
                        '    if (x265_atobool(value, bError))',
                        '        svtHevcParam->intraRefreshType = 1;',
                        '    else',
                        '        svtHevcParam->intraRefreshType = 2;',
                        '}',
                    )) + '\n',
                ),
                'forbidden SVT open-gop regression',
                'svt-open-gop-parse-safety',
            ),
            case(
                lambda repo: write_repo_file(
                    repo,
                    Path('source/common/param.cpp'),
                    'else if (!strcmp(temp2, "-")) x265_log(param, X265_LOG_ERROR, "Shouldn\'t exclude both sockets for pools option %s \\n", pools);\n',
                ),
                'forbidden SVT pools exclude-both-sockets regression',
                'svt-pools-exclude-both-sockets-guard',
            ),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_encoder_rpu_replace_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'encoder-rpu-replace-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_copy_user_sei_staging.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'copy-user-sei-staging'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_dup_side_data_staging.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'dup-side-data-staging'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_read_user_sei_staging.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'read-user-sei-staging'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_copy_picture_staging.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'copy-picture-staging'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_dup_create_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'dup-create-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_encode_quant_offsets_staging.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'encode-quant-offsets-staging'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_read_user_sei_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'read-user-sei-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_log_progress_file_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'log-progress-file-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_negated_bool_alias_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'negated-bool-alias-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_rd_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'rd-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_limit_refs_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'limit-refs-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_dup_threshold_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'dup-threshold-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_vmaf_flush_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'vmaf-flush-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_avs_buffer_replace_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'avs-buffer-replace-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_vpy_buffer_replace_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'vpy-buffer-replace-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_zimg_token_parse_usage.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'zimg-token-parse-usage'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_zimg_init_rollback.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'zimg-init-rollback'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_dynamic_hdr10_legacy_patterns.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'dynamic-hdr10-legacy-patterns'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_sei_unsigned_token_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'sei-unsigned-token-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_lavf_framecount_parse_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'lavf-framecount-parse-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_video_signal_type_preset_parse.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'video-signal-type-preset-parse'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_sei_mastering_display_parse.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'sei-mastering-display-parse'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_sao_param_staging.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'sao-param-staging'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_zone_parse_replace_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'zone-parse-replace-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_cpu_name_strdup_safety.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'cpu-name-strdup-safety'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_x265_fclose_macro_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'x265-fclose-macro-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_hme_param_sscanf_usage.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'hme-param-sscanf-usage'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_masking_strength_scan_usage.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'masking-strength-scan-usage'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_reviewed_string_copy_usage.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'reviewed-string-copy-usage'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_cli_progress_file_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'cli-progress-file-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_raw_output_write_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'raw-output-write-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_raw_stdout_flush_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'raw-stdout-flush-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_mkv_output_fail_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'mkv-output-fail-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_mkv_close_fail_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'mkv-close-fail-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_recon_output_write_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'recon-output-write-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_recon_output_stream_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'recon-output-stream-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_recon_finalize_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'recon-finalize-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_gop_options_fail_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'gop-options-fail-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_gop_output_fail_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'gop-output-fail-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_output_open_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'output-open-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_mp4_header_sei_alloc_guard.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'mp4-header-sei-alloc-guard'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_frame_create_rowstate_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'frame-create-rowstate-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_frame_create_mcstf_refpic_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'frame-create-mcstf-refpic-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_frame_create_mcstffencpic_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'frame-create-mcstf-fenc-pic-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_frame_create_top_alloc_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'frame-create-top-alloc-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_frame_alloc_encode_data_guards.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'frame-alloc-encode-data-guards'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_open_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-open-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_analysis_load_open_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'analysis-load-open-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_cli_config_open_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'cli-config-open-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_cli_help_exit_cleanup.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'cli-help-exit-cleanup'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_vmaf_data_cleanup_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'vmaf-data-cleanup-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_lambda_file_open_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'lambda-file-open-state'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_vmaf_input_open_state.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'vmaf-input-open-state'),
        )

        for item in cases:
            fail_case(item['modifier'], item['expected'], item['check'])

        print('CI guard script guardrails validated')


if __name__ == '__main__':
    main()
