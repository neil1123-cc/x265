#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (pic_in[view]->bitDepth > m_param->internalBitDepth && m_cliopt.bDither)',
    'if (!m_cliopt.input[view])',
    'x265_log(m_param, X265_LOG_ERROR, "Missing dither input state for view %d in %s\\n",',
    'm_ret = 4;',
    'goto fail;',
    'x265_dither_image(pic_in[view], m_cliopt.input[view]->getWidth(), m_cliopt.input[view]->getHeight(), errorBuf, m_param->internalBitDepth);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread dither input guardrail: {snippet}'))

    dither_pos = text.find('if (pic_in[view]->bitDepth > m_param->internalBitDepth && m_cliopt.bDither)')
    input_guard_pos = text.find('if (!m_cliopt.input[view])', dither_pos)
    goto_pos = text.find('goto fail;', input_guard_pos)
    dither_call_pos = text.find('x265_dither_image(pic_in[view], m_cliopt.input[view]->getWidth(), m_cliopt.input[view]->getHeight(), errorBuf, m_param->internalBitDepth);', goto_pos)
    if -1 in (dither_pos, input_guard_pos, goto_pos, dither_call_pos) or not (dither_pos < input_guard_pos < goto_pos < dither_call_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard null dither input state before x265_dither_image'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain dither input guard')
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

    print('ABR thread dither input guard validated')


if __name__ == '__main__':
    main()
