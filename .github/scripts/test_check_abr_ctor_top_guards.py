#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_ctor_top_guards.py')

# Coverage probe used by the scan for the ABR ctor caller guardrail.
NORMALIZED_PROBES = (
    'missing ABR ctor caller guardrail: ',
    'missing file',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'm_passEnc = X265_MALLOC(PassEncoder*, m_numEncodes);',
                    'if (!m_passEnc)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for ABR pass list\\n");',
                    '    m_numActiveEncodes.set(0);',
                    '}',
                    'std::fill_n(m_passEnc, m_numEncodes, nullptr);',
                    'm_param = X265_MALLOC(x265_param, m_numEncodes);',
                    'if (!m_param)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for ABR parameter list\\n");',
                    '    m_numActiveEncodes.set(0);',
                    '}',
                    'if (!m_passEnc[i])',
                    '{',
                    '    m_numActiveEncodes.decr();',
                    '    continue;',
                    '}',
                    'if (m_inputPicBuffer && m_inputPicBuffer[pass])',
                    'if (m_passEnc && m_passEnc[pass])',
                )) + '\n',
                'source/x265.cpp': '\n'.join((
                    'if (!abrEnc->m_passEnc[idx])',
                    '{',
                    '    ret = 4;',
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
                'source/abrEncApp.cpp': 'm_passEnc = X265_MALLOC(PassEncoder*, m_numEncodes);\n',
                'source/x265.cpp': 'if (abrEnc->m_passEnc[idx]->m_ret)\n{\n}\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR ctor top guardrail: if (!m_passEnc)')

    print('ABR constructor top guard tests passed')


if __name__ == '__main__':
    main()
