#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_recon_state_safety.py')

# Normalized checker probes used by the coverage scan for snippet-formatted guardrail loops.
NORMALIZED_PROBES = (
    'forbidden VMAF/recon state regression: ',
    'missing VMAF/recon guardrail: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));',
                    'if (!vmafData)',
                    'x265_log(nullptr, X265_LOG_ERROR, "vmaf data alloc failed\\n");',
                    'return true;',
                    '*vmafData = x265_vmaf_data();',
                    'if (api->param_default_preset(param, preset, tune) < 0)',
                    'if (!this->recon[0])',
                    'x265_log(param, X265_LOG_ERROR, "recon file must be writable to get VMAF score\\n");',
                    'return true;',
                    "const char *str = std::strrchr(info[0].filename, '.');",
                    'vmafData->reference_file = x265_fopen(inputfn[0], "rb");',
                    'vmafData->distorted_file = x265_fopen(reconfn[0], "rb");',
                    'if (!vmafData->reference_file || !vmafData->distorted_file)',
                    'x265_log(param, X265_LOG_ERROR, "unable to open VMAF input files\\n");',
                    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
                    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
                    'return true;',
                    'if (!vmafData->reference_file || !vmafData->distorted_file ||',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'vmafData->reference_file = x265_fopen(inputfn[0], "rb");\n            vmafData->distorted_file = x265_fopen(reconfn[0], "rb");\n',
            },
        )
        expect_fail(run_checker(root), 'missing VMAF/recon guardrail: vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));',
                    '*vmafData = x265_vmaf_data();',
                    'if (!vmafData)',
                    'x265_log(nullptr, X265_LOG_ERROR, "vmaf data alloc failed\\n");',
                    'return true;',
                    'if (api->param_default_preset(param, preset, tune) < 0)',
                    'if (!this->recon[0])',
                    'x265_log(param, X265_LOG_ERROR, "recon file must be writable to get VMAF score\\n");',
                    'return true;',
                    "const char *str = std::strrchr(info[0].filename, '.');",
                    'vmafData->reference_file = x265_fopen(inputfn[0], "rb");',
                    'vmafData->distorted_file = x265_fopen(reconfn[0], "rb");',
                    'if (!vmafData->reference_file || !vmafData->distorted_file)',
                    'x265_log(param, X265_LOG_ERROR, "unable to open VMAF input files\\n");',
                    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
                    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
                    'return true;',
                    'if (!vmafData->reference_file || !vmafData->distorted_file ||',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF state initialization must guard the allocation result before zero-initializing vmafData')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));',
                    'if (!vmafData)',
                    'x265_log(nullptr, X265_LOG_ERROR, "vmaf data alloc failed\\n");',
                    'return true;',
                    '*vmafData = x265_vmaf_data();',
                    'if (api->param_default_preset(param, preset, tune) < 0)',
                    'if (!this->recon[0])',
                    'return true;',
                    'x265_log(param, X265_LOG_ERROR, "recon file must be writable to get VMAF score\\n");',
                    "const char *str = std::strrchr(info[0].filename, '.');",
                    'vmafData->reference_file = x265_fopen(inputfn[0], "rb");',
                    'vmafData->distorted_file = x265_fopen(reconfn[0], "rb");',
                    'if (!vmafData->reference_file || !vmafData->distorted_file)',
                    'x265_log(param, X265_LOG_ERROR, "unable to open VMAF input files\\n");',
                    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
                    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
                    'return true;',
                    'if (!vmafData->reference_file || !vmafData->distorted_file ||',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF setup must reject non-writable recon output before attempting to open VMAF input files')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));',
                    'if (!vmafData)',
                    'x265_log(nullptr, X265_LOG_ERROR, "vmaf data alloc failed\\n");',
                    'return true;',
                    '*vmafData = x265_vmaf_data();',
                    'if (api->param_default_preset(param, preset, tune) < 0)',
                    'if (!this->recon[0])',
                    'x265_log(param, X265_LOG_ERROR, "recon file must be writable to get VMAF score\\n");',
                    'return true;',
                    "const char *str = std::strrchr(info[0].filename, '.');",
                    'vmafData->reference_file = x265_fopen(inputfn[0], "rb");',
                    'vmafData->distorted_file = x265_fopen(reconfn[0], "rb");',
                    'if (!vmafData->reference_file || !vmafData->distorted_file)',
                    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
                    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
                    'x265_log(param, X265_LOG_ERROR, "unable to open VMAF input files\\n");',
                    'return true;',
                    'if (!vmafData->reference_file || !vmafData->distorted_file ||',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF input setup must close both staged input files after an open failure before returning')

    print('VMAF/recon state safety tests passed')


if __name__ == '__main__':
    main()
