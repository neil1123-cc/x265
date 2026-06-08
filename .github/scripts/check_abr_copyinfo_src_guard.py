#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'void PassEncoder::copyInfo(x265_analysis_data * src)',
    'if (!src)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis source data for encoder %u\\n", m_id);',
    'm_ret = 4;',
    'return;',
    'uint32_t written = m_parent->m_analysisWriteCnt[m_id].get();',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ABR copyInfo src guardrail: {snippet}'))

    fn_pos = text.find('void PassEncoder::copyInfo(x265_analysis_data * src)')
    guard_pos = text.find('if (!src)', fn_pos)
    return_pos = text.find('return;', guard_pos)
    written_pos = text.find('uint32_t written = m_parent->m_analysisWriteCnt[m_id].get();', return_pos)
    if -1 in (fn_pos, guard_pos, return_pos, written_pos) or not (fn_pos < guard_pos < return_pos < written_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::copyInfo must guard src before dereferencing it'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::copyInfo src guard')
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

    print('ABR copyInfo src guard validated')


if __name__ == '__main__':
    main()
