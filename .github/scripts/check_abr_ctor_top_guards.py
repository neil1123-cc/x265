#!/usr/bin/env python3
import argparse
from pathlib import Path


ABR_TARGET = Path('source/abrEncApp.cpp')
CLI_TARGET = Path('source/x265.cpp')
ABR_REQUIRED = (
    'm_passEnc = X265_MALLOC(PassEncoder*, m_numEncodes);',
    'if (!m_passEnc)',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for ABR pass list\\n");',
    'std::fill_n(m_passEnc, m_numEncodes, nullptr);',
    'm_param = X265_MALLOC(x265_param, m_numEncodes);',
    'if (!m_param)',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for ABR parameter list\\n");',
    'm_numActiveEncodes.set(0);',
    'if (!m_passEnc[i])',
    'm_numActiveEncodes.decr();',
    'continue;',
    'if (m_inputPicBuffer && m_inputPicBuffer[pass])',
    'if (m_passEnc && m_passEnc[pass])',
)
CLI_REQUIRED = (
    'if (!abrEnc->m_passEnc[idx])',
    'ret = 4;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    abr_path = repo_root / ABR_TARGET
    if not abr_path.is_file():
        failures.append((ABR_TARGET.as_posix(), 0, 'missing file'))
    else:
        abr_text = abr_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in ABR_REQUIRED:
            if snippet not in abr_text:
                failures.append((ABR_TARGET.as_posix(), 0, f'missing ABR ctor top guardrail: {snippet}'))

    cli_path = repo_root / CLI_TARGET
    if not cli_path.is_file():
        failures.append((CLI_TARGET.as_posix(), 0, 'missing file'))
    else:
        cli_text = cli_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in CLI_REQUIRED:
            if snippet not in cli_text:
                failures.append((CLI_TARGET.as_posix(), 0, f'missing ABR ctor caller guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR constructor top-level guards')
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

    print('ABR constructor top-level guards validated')


if __name__ == '__main__':
    main()
