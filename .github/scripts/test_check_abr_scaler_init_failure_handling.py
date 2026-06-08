#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_scaler_init_failure_handling.py')

# Coverage probe used by the scan for the reviewed ABR scaler init failure guardrail.
NORMALIZED_PROBES = (
    'missing ABR scaler init failure guardrail: ',
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
                    'if (!src || !dst)',
                    'delete src;',
                    'delete dst;',
                    'x265_log(m_param, X265_LOG_ERROR, "\\n MALLOC failure in Scaler");',
                    'result = 4;',
                    'm_ret = 4;',
                    'return -1;',
                    'm_scaler = new (std::nothrow) Scaler(0, 1, m_id, src, dst, this);',
                    'if (!m_scaler)',
                    'else if (!m_scaler->m_initOk)',
                    'm_scaler->destroy();',
                    'delete m_scaler;',
                    'm_scaler = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'if (!m_scaler)\n'})
        expect_fail(run_checker(root), 'missing ABR scaler init failure guardrail')

    print('ABR scaler init failure handling tests passed')


if __name__ == '__main__':
    main()
