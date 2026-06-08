#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_motionestimate_init_guard.py')

# Coverage probes used by the scan for MotionEstimate init guardrails.
NORMALIZED_PROBES = (
    'Search::initSearch must fail before quant initialization when MotionEstimate source YUV allocation fails',
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


def motion_text():
    return '\n'.join((
        'bool MotionEstimate::init(int csp)',
        '{',
        '    return fencPUYuv.create(FENC_STRIDE, csp);',
        '}',
    )) + '\n'


def search_text():
    return '\n'.join((
        'bool Search::initSearch(const x265_param& param, ScalingList& scalingList)',
        '{',
        '    if (!m_me.init(param.internalCsp))',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate motion estimate source buffer\\n");',
        '        return false;',
        '    }',
        '    bool ok = m_quant.init(param.psyRdoq, scalingList, m_entropyCoder);',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/motion.cpp': motion_text(),
                'source/encoder/motion.h': 'bool init(int csp);\n',
                'source/encoder/search.cpp': search_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/motion.cpp': motion_text().replace('bool MotionEstimate::init(int csp)', 'void MotionEstimate::init(int csp)', 1),
                'source/encoder/motion.h': 'void init(int csp);\n',
                'source/encoder/search.cpp': search_text(),
            },
        )
        expect_fail(run_checker(root), 'forbidden MotionEstimate init regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/motion.cpp': motion_text(),
                'source/encoder/motion.h': 'bool init(int csp);\n',
                'source/encoder/search.cpp': search_text().replace('if (!m_me.init(param.internalCsp))\n', 'm_me.init(param.internalCsp);\n', 1),
            },
        )
        expect_fail(run_checker(root), 'missing Search motion-estimate init guardrail: if (!m_me.init(param.internalCsp))')

    print('MotionEstimate init guard tests passed')


if __name__ == '__main__':
    main()
