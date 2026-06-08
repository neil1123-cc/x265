#!/usr/bin/env python3
import argparse
from pathlib import Path


MOTION_TARGET = Path('source/encoder/motion.cpp')
MOTION_HEADER_TARGET = Path('source/encoder/motion.h')
SEARCH_TARGET = Path('source/encoder/search.cpp')

MOTION_REQUIRED = (
    'bool MotionEstimate::init(int csp)',
    'return fencPUYuv.create(FENC_STRIDE, csp);',
)
MOTION_FORBIDDEN = (
    'void MotionEstimate::init(int csp)',
)
HEADER_REQUIRED = (
    'bool init(int csp);',
)
SEARCH_REQUIRED = (
    'if (!m_me.init(param.internalCsp))',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate motion estimate source buffer\\n");',
    'return false;',
)


def check_file(path, required, forbidden, label):
    if not path.is_file():
        return [(path.as_posix(), 0, f'missing {label} file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in forbidden:
        if snippet in text:
            failures.append((path.as_posix(), 0, f'forbidden {label} regression: {snippet}'))
    for snippet in required:
        if snippet not in text:
            failures.append((path.as_posix(), 0, f'missing {label} guardrail: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    failures.extend(check_file(repo_root / MOTION_TARGET, MOTION_REQUIRED, MOTION_FORBIDDEN, 'MotionEstimate init'))
    failures.extend(check_file(repo_root / MOTION_HEADER_TARGET, HEADER_REQUIRED, (), 'MotionEstimate init header'))
    failures.extend(check_file(repo_root / SEARCH_TARGET, SEARCH_REQUIRED, (), 'Search motion-estimate init'))

    search_path = repo_root / SEARCH_TARGET
    if search_path.is_file():
        text = search_path.read_text(encoding='utf-8', errors='ignore')
        init_search_pos = text.find('bool Search::initSearch(const x265_param& param, ScalingList& scalingList)')
        me_guard_pos = text.find('if (!m_me.init(param.internalCsp))', init_search_pos if init_search_pos != -1 else 0)
        log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate motion estimate source buffer\\n");', me_guard_pos if me_guard_pos != -1 else 0)
        return_pos = text.find('return false;', log_pos if log_pos != -1 else 0)
        quant_init_pos = text.find('bool ok = m_quant.init(param.psyRdoq, scalingList, m_entropyCoder);', return_pos if return_pos != -1 else 0)
        if -1 in (init_search_pos, me_guard_pos, log_pos, return_pos, quant_init_pos) or not (
            init_search_pos < me_guard_pos < log_pos < return_pos < quant_init_pos
        ):
            failures.append((SEARCH_TARGET.as_posix(), 0, 'Search::initSearch must fail before quant initialization when MotionEstimate source YUV allocation fails'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MotionEstimate init guardrails')
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

    print('MotionEstimate init guards validated')


if __name__ == '__main__':
    main()
