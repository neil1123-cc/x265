#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_nalu_file_open_state.py')

# Coverage probe used by the scan for nalu-file open-state guardrails.
NORMALIZED_PROBES = (
    'missing nalu file open-state guardrail: ',
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
                    'm_naluFile = x265_fopen(m_param->naluFile, "r");',
                    'else if (std::ferror(m_naluFile))',
                    'bool closeFailed = std::ferror(m_naluFile) != 0;',
                    'if (std::fclose(m_naluFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close user SEI file \\"%s\\" after open failure\\n", m_param->naluFile);',
                    'm_naluFile = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'm_naluFile = x265_fopen(m_param->naluFile, "r");\nif (!m_naluFile)\n    return;\n',
            },
        )
        expect_fail(run_checker(root), 'missing nalu file open-state guardrail')

    print('Nalu file open-state guard tests passed')


if __name__ == '__main__':
    main()
