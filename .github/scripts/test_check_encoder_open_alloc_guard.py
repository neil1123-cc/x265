#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_open_alloc_guard.py')

# Coverage probe used by the scan for the reviewed encoder-open allocation guard.
NORMALIZED_PROBES = (
    'x265_encoder_open must reject encoder allocation failure before touching encoder-owned parameter storage',
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
        'x265_encoder *x265_encoder_open(x265_param *p)',
        '{',
        '    Encoder* encoder = new (std::nothrow) Encoder;',
        '    if (!encoder)',
        '    {',
        '        x265_log(p, X265_LOG_ERROR, "Unable to allocate encoder instance\\n");',
        '        return nullptr;',
        '    }',
        '    encoder->m_paramBase[0] = PARAM_NS::x265_param_alloc();',
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
                    '    Encoder* encoder = new (std::nothrow) Encoder;\n',
                    '    Encoder* encoder = new Encoder;\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_encoder_open allocation guardrail: Encoder* encoder = new (std::nothrow) Encoder;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!encoder)\n'
                    '    {\n'
                    '        x265_log(p, X265_LOG_ERROR, "Unable to allocate encoder instance\\n");\n'
                    '        return nullptr;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_encoder_open allocation guardrail: if (!encoder)')

    print('x265_encoder_open allocation guard tests passed')


if __name__ == '__main__':
    main()
