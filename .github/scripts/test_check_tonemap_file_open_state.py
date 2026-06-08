#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_tonemap_file_open_state.py')

# Coverage probes used by the scan for tone-map file open-state guardrails.
NORMALIZED_PROBES = (
    'tone-map validation must close the file before marking the encoder aborted',
    'missing tone-map open-state guardrail: ',
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
                    'FILE* toneMapFile = x265_fopen(p->toneMapFile, "r");',
                    'if (!toneMapFile)',
                    '{',
                    '    x265_log(p, X265_LOG_ERROR, "Unable to open tone-map file.\\n");',
                    '    m_bToneMap = 0;',
                    '    m_param->toneMapFile[0] = 0;',
                    '    m_aborted = true;',
                    '}',
                    'else',
                    '{',
                    '    bool closeFailed = std::ferror(toneMapFile) != 0;',
                    '    if (std::fclose(toneMapFile))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '    {',
                    '        x265_log(p, X265_LOG_ERROR, "Unable to close tone-map file.\\n");',
                    '        m_bToneMap = 0;',
                    '        m_param->toneMapFile[0] = 0;',
                    '        m_aborted = true;',
                    '    }',
                    '    else',
                    '        m_bToneMap = 1;',
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
                'source/encoder/encoder.cpp': 'if (std::strlen(m_param->toneMapFile))\n    m_bToneMap = 1;\n',
            },
        )
        expect_fail(run_checker(root), 'missing tone-map open-state guardrail')

    print('Tone-map file open-state guard tests passed')


if __name__ == '__main__':
    main()
