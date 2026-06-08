#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_encode_frame_alloc_guards.py')

# Coverage probe used by the scan for the reviewed encode-frame allocation guards.
NORMALIZED_PROBES = (
    'Encoder::encode must reject input and temporal-filter Frame allocation failures before use',
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


def valid_text():
    return '\n'.join((
        'inFrame[layer] = new (std::nothrow) Frame;',
        'if (!inFrame[layer])',
        '{',
        '    m_aborted = true;',
        '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate input frame for layer %d, aborting encode\\n", layer);',
        '    return -1;',
        '}',
        'Frame* dupFrame = new (std::nothrow) Frame;',
        'if (!dupFrame)',
        '{',
        '    m_aborted = true;',
        '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate temporal-filter frame %d, aborting encode\\n", i);',
        '    std::fflush(stderr);',
        '    return -1;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('inFrame[layer] = new (std::nothrow) Frame;\n', 'inFrame[layer] = new Frame;\n', 1)})
        expect_fail(run_checker(root), 'forbidden encoder encode frame alloc regression: inFrame[layer] = new Frame;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('Frame* dupFrame = new (std::nothrow) Frame;\n', 'Frame* dupFrame = new Frame;\n', 1)})
        expect_fail(run_checker(root), 'forbidden encoder encode frame alloc regression: Frame* dupFrame = new Frame;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('if (!dupFrame)\n', 'if (dupFrame)\n', 1)})
        expect_fail(run_checker(root), 'missing encoder encode frame alloc guardrail: if (!dupFrame)')

    print('Encoder::encode frame allocation guard tests passed')


if __name__ == '__main__':
    main()
