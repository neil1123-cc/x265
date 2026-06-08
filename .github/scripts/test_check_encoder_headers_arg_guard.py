#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_headers_arg_guard.py')

# Coverage probe used by the scan for the reviewed encoder headers argument guard.
NORMALIZED_PROBES = (
    'x265_encoder_headers must reject null NAL outputs before touching encoder state',
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
        'int x265_encoder_headers(x265_encoder *enc, x265_nal **pp_nal, uint32_t *pi_nal)',
        '{',
        '    if (!enc || !pp_nal)',
        '    {',
        '        if (pi_nal)',
        '            *pi_nal = 0;',
        '        return -1;',
        '    }',
        '    Encoder *encoder = static_cast<Encoder*>(enc);',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!enc || !pp_nal)\n'
                    '    {\n'
                    '        if (pi_nal)\n'
                    '            *pi_nal = 0;\n'
                    '        return -1;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_encoder_headers argument guardrail: if (!enc || !pp_nal)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'int x265_encoder_headers(x265_encoder *enc, x265_nal **pp_nal, uint32_t *pi_nal)',
                    '{',
                    '    if (pp_nal && enc)',
                    '    {',
                    '        Encoder *encoder = static_cast<Encoder*>(enc);',
                    '        return 0;',
                    '    }',
                    '    if (enc)',
                    '    {',
                    '        Encoder *encoder = static_cast<Encoder*>(enc);',
                    '        encoder->m_aborted = true;',
                    '    }',
                    '    return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_encoder_headers must not abort the encoder for caller-owned output pointer errors')

    print('x265_encoder_headers argument guard tests passed')


if __name__ == '__main__':
    main()
