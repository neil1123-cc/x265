#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_film_grain_open_state.py')

# Coverage probes used by the scan for film grain open-state guardrails.
NORMALIZED_PROBES = (
    'missing film grain open-state guardrail: ',
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
                    'm_filmGrainIn = x265_fopen(m_param->filmGrain, "rb");',
                    'else if (std::ferror(m_filmGrainIn))',
                    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
                    'if (std::fclose(m_filmGrainIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close film grain file \\"%s\\" after open failure\\n", m_param->filmGrain);',
                    'm_filmGrainIn = nullptr;',
                    'm_aomFilmGrainIn = x265_fopen(m_param->aomFilmGrain, "rb");',
                    'else if (std::ferror(m_aomFilmGrainIn))',
                    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
                    'if (std::fclose(m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\" after open failure\\n", m_param->aomFilmGrain);',
                    'm_aomFilmGrainIn = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'm_filmGrainIn = x265_fopen(m_param->filmGrain, "rb");\nif (!m_filmGrainIn)\n    return;\n',
            },
        )
        expect_fail(run_checker(root), 'missing film grain open-state guardrail')

    print('Film grain open-state guard tests passed')


if __name__ == '__main__':
    main()
