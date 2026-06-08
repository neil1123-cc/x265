#!/usr/bin/env python3
import argparse
from pathlib import Path


CLI_TARGET = Path('source/x265cli.cpp')
ABR_TARGET = Path('source/abrEncApp.cpp')

CLI_REQUIRED_SNIPPETS = (
    'if (vmafData)',
    'closeFailed |= closeVmafInputFile(param, vmafData->reference_file, "reference", "during CLI cleanup");',
    'closeFailed |= closeVmafInputFile(param, vmafData->distorted_file, "distorted", "during CLI cleanup");',
    'x265_free(vmafData);',
    'vmafData = nullptr;',
)

ABR_REQUIRED_SNIPPETS = (
    'api->vmaf_encoder_log(m_encoder, m_cliopt.argCnt, m_cliopt.argString, m_cliopt.param, vmafdata);',
    'm_cliopt.vmafData = nullptr;',
    'm_parent->m_clioptArray[m_id].vmafData = nullptr;',
)


def read_text(path):
    return path.read_text(encoding='utf-8', errors='ignore')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    cli_path = repo_root / CLI_TARGET
    if not cli_path.is_file():
        failures.append((CLI_TARGET.as_posix(), 0, 'missing file'))
    else:
        cli_text = read_text(cli_path)
        for snippet in CLI_REQUIRED_SNIPPETS:
            if snippet not in cli_text:
                failures.append((CLI_TARGET.as_posix(), 0, f'missing VMAF data cleanup guardrail: {snippet}'))

    abr_path = repo_root / ABR_TARGET
    if not abr_path.is_file():
        failures.append((ABR_TARGET.as_posix(), 0, 'missing file'))
    else:
        abr_text = read_text(abr_path)
        for snippet in ABR_REQUIRED_SNIPPETS:
            if snippet not in abr_text:
                failures.append((ABR_TARGET.as_posix(), 0, f'missing VMAF data cleanup guardrail: {snippet}'))

        log_pos = abr_text.find(ABR_REQUIRED_SNIPPETS[0])
        local_null_pos = abr_text.find(ABR_REQUIRED_SNIPPETS[1], log_pos if log_pos >= 0 else 0)
        parent_null_pos = abr_text.find(ABR_REQUIRED_SNIPPETS[2], local_null_pos if local_null_pos >= 0 else 0)
        if -1 in (log_pos, local_null_pos, parent_null_pos) or not (log_pos < local_null_pos < parent_null_pos):
            failures.append((ABR_TARGET.as_posix(), 0, 'VMAF log path must clear local and parent vmafData pointers after encoder logging'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF data cleanup state')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('VMAF data cleanup guard validated')


if __name__ == '__main__':
    main()
