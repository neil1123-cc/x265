#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_data_cleanup_state.py')

# Normalized checker probes used by the coverage scan for repeated cleanup templates.
NORMALIZED_PROBES = (
    'missing file',
    'missing VMAF data cleanup guardrail: ',
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
        expect_fail(run_checker(root), 'missing file')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (vmafData)',
                    '{',
                    '    closeFailed |= closeVmafInputFile(param, vmafData->reference_file, "reference", "during CLI cleanup");',
                    '    closeFailed |= closeVmafInputFile(param, vmafData->distorted_file, "distorted", "during CLI cleanup");',
                    '    x265_free(vmafData);',
                    '    vmafData = nullptr;',
                    '}',
                )) + '\n',
                'source/abrEncApp.cpp': '\n'.join((
                    'api->vmaf_encoder_log(m_encoder, m_cliopt.argCnt, m_cliopt.argString, m_cliopt.param, vmafdata);',
                    'm_cliopt.vmafData = nullptr;',
                    'm_parent->m_clioptArray[m_id].vmafData = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'x265_free(vmafData);\n',
                'source/abrEncApp.cpp': 'api->vmaf_encoder_log(m_encoder, m_cliopt.argCnt, m_cliopt.argString, m_cliopt.param, vmafdata);\n',
            },
        )
        expect_fail(run_checker(root), 'missing VMAF data cleanup guardrail: if (vmafData)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (vmafData)',
                    '{',
                    '    closeFailed |= closeVmafInputFile(param, vmafData->reference_file, "reference", "during CLI cleanup");',
                    '    closeFailed |= closeVmafInputFile(param, vmafData->distorted_file, "distorted", "during CLI cleanup");',
                    '    x265_free(vmafData);',
                    '    vmafData = nullptr;',
                    '}',
                )) + '\n',
                'source/abrEncApp.cpp': '\n'.join((
                    'm_cliopt.vmafData = nullptr;',
                    'api->vmaf_encoder_log(m_encoder, m_cliopt.argCnt, m_cliopt.argString, m_cliopt.param, vmafdata);',
                    'm_parent->m_clioptArray[m_id].vmafData = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF log path must clear local and parent vmafData pointers after encoder logging')

    print('VMAF data cleanup guard tests passed')


if __name__ == '__main__':
    main()
