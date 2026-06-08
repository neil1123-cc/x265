#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_rpu_replace_safety.py')

# Coverage probes used by the scan for encoder RPU replacement guardrails.
NORMALIZED_PROBES = (
    'encoder RPU replacement must allocate before dropping the old payload',
    'forbidden encoder RPU replacement regression: ',
    'missing encoder RPU replacement guardrail: ',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (inputPic[0]->rpu.payloadSize)',
                    '{',
                    '    uint8_t* newRpuPayload = new (std::nothrow) uint8_t[inputPic[0]->rpu.payloadSize];',
                    '    if (!newRpuPayload)',
                    '        return -1;',
                    '    delete[] inFrame[0]->m_rpu.payload;',
                    '    inFrame[0]->m_rpu.payload = newRpuPayload;',
                    '    inFrame[0]->m_rpu.payloadSize = inputPic[0]->rpu.payloadSize;',
                    '}',
                    'else if (inFrame[0]->m_rpu.payload)',
                    '{',
                    '    delete[] inFrame[0]->m_rpu.payload;',
                    '    inFrame[0]->m_rpu.payload = nullptr;',
                    '    inFrame[0]->m_rpu.payloadSize = 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (inFrame[0]->m_rpu.payload)',
                    '{',
                    '    delete[] inFrame[0]->m_rpu.payload;',
                    '    inFrame[0]->m_rpu.payload = nullptr;',
                    '    inFrame[0]->m_rpu.payloadSize = 0;',
                    '}',
                    'if (inputPic[0]->rpu.payloadSize)',
                    '{',
                    '    inFrame[0]->m_rpu.payload = new (std::nothrow) uint8_t[inputPic[0]->rpu.payloadSize];',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden encoder RPU replacement regression')

    print('Encoder RPU replacement safety tests passed')


if __name__ == '__main__':
    main()
