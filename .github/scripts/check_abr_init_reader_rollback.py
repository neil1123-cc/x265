#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (!(m_cliopt.enableScaler && m_id))',
    'm_reader = new (std::nothrow) Reader(m_id, this);',
    'if (!m_encoder)',
    'x265_log(nullptr, X265_LOG_ERROR, "x265_encoder_open() failed for Enc, \\n");',
    'rollbackInputHelper();',
    'm_ret = 2;',
    'if (!result)',
    'result = m_ret;',
    'return -1;',
)
FORBIDDEN_SNIPPETS = (
    'if (!m_encoder)\n        {\n            x265_log(nullptr, X265_LOG_ERROR, "x265_encoder_open() failed for Enc, \\n");\n            m_ret = 2;\n            m_reader = nullptr;\n            return -1;\n        }',
)
REGION_START = 'if (!(m_cliopt.enableScaler && m_id))'
REGION_END = 'return 1;'


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    if -1 not in (region_start, region_end):
        region_end += len(REGION_END)
        region = text[region_start:region_end]
    else:
        region = text
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing abr init reader rollback guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, 'forbidden abr init reader rollback regression: init must not null out m_reader before destroy() can release it'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'if (!(m_cliopt.enableScaler && m_id))',
                'm_reader = new (std::nothrow) Reader(m_id, this);',
                'if (!m_encoder)',
                'x265_log(nullptr, X265_LOG_ERROR, "x265_encoder_open() failed for Enc, \\n");',
                'rollbackInputHelper();',
                'm_ret = 2;',
                'if (!result)',
                'result = m_ret;',
                'return -1;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'PassEncoder::init must roll back reader-owned input state before setting the encoder-open failure result and returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::init reader rollback guardrail')
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

    print('Abr init reader rollback validated')


if __name__ == '__main__':
    main()
