#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_film_grain_close_state.py')

# Coverage probes used by the scan for film grain close-state guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'expected one guarded parse-failure close path for each film grain model in frameencoder',
    'expected one guarded open-failure close path for each film grain file in encoder startup',
    'expected one guarded destroy close path for each film grain file in encoder teardown',
    'missing film grain close guardrail: ',
    'forbidden film grain short-circuit close regression: ',
    'encoder startup must preserve film grain open-failure close ordering and null resets',
    'encoder teardown must preserve film grain close ordering and null resets',
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
                'source/encoder/frameencoder.cpp': '\n'.join((
                    '/* Write Film grain characteristics if present */',
                    'bool closeFailed = ferror(this->m_top->m_filmGrainIn) != 0;',
                    'if (fclose(this->m_top->m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close film grain model file after parse failure\\n");',
                    'this->m_top->m_filmGrainIn = nullptr;',
                    'bool closeFailed = ferror(this->m_top->m_aomFilmGrainIn) != 0;',
                    'if (fclose(this->m_top->m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close AOM film grain model file after parse failure\\n");',
                    'this->m_top->m_aomFilmGrainIn = nullptr;',
                    '/* Write user SEI */',
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (m_param->filmGrain)',
                    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
                    'if (std::fclose(m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close film grain file \\"%s\\" after open failure\\n", m_param->filmGrain);',
                    'm_filmGrainIn = nullptr;',
                    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
                    'if (std::fclose(m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\" after open failure\\n", m_param->aomFilmGrain);',
                    'm_aomFilmGrainIn = nullptr;',
                    'm_bZeroLatency = 0;',
                    'if (m_filmGrainIn)',
                    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
                    'if (std::fclose(m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close film grain file \\"%s\\"\\n", m_param->filmGrain);',
                    'm_filmGrainIn = nullptr;',
                    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
                    'if (std::fclose(m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\"\\n", m_param->aomFilmGrain);',
                    'm_aomFilmGrainIn = nullptr;',
                    '#ifdef SVT_HEVC',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': 'x265_fclose(this->m_top->m_filmGrainIn);\n',
                'source/encoder/encoder.cpp': '\n',
            },
        )
        expect_fail(run_checker(root), 'missing film grain close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': '\n'.join((
                    '/* Write Film grain characteristics if present */',
                    'bool closeFailed = ferror(this->m_top->m_filmGrainIn) != 0;',
                    'if (fclose(this->m_top->m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close film grain model file after parse failure\\n");',
                    'this->m_top->m_filmGrainIn = nullptr;',
                    'if (ferror(this->m_top->m_filmGrainIn) || fclose(this->m_top->m_filmGrainIn))',
                    '    x265_log(this->m_param, X265_LOG_WARNING, "Unable to close film grain model file after parse failure\\n");',
                    'bool closeFailed = ferror(this->m_top->m_aomFilmGrainIn) != 0;',
                    'if (fclose(this->m_top->m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close AOM film grain model file after parse failure\\n");',
                    'this->m_top->m_aomFilmGrainIn = nullptr;',
                    '/* Write user SEI */',
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (m_param->filmGrain)',
                    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
                    'if (std::fclose(m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close film grain file \\"%s\\" after open failure\\n", m_param->filmGrain);',
                    'm_filmGrainIn = nullptr;',
                    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
                    'if (std::fclose(m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\" after open failure\\n", m_param->aomFilmGrain);',
                    'm_aomFilmGrainIn = nullptr;',
                    'm_bZeroLatency = 0;',
                    'if (m_filmGrainIn)',
                    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
                    'if (std::fclose(m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close film grain file \\"%s\\"\\n", m_param->filmGrain);',
                    'm_filmGrainIn = nullptr;',
                    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
                    'if (std::fclose(m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\"\\n", m_param->aomFilmGrain);',
                    'm_aomFilmGrainIn = nullptr;',
                    '#ifdef SVT_HEVC',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden film grain short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': '\n'.join((
                    '/* Write Film grain characteristics if present */',
                    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close film grain model file after parse failure\\n");',
                    'bool closeFailed = ferror(this->m_top->m_filmGrainIn) != 0;',
                    'if (fclose(this->m_top->m_filmGrainIn))',
                    '    closeFailed = true;',
                    'this->m_top->m_filmGrainIn = nullptr;',
                    'bool closeFailed = ferror(this->m_top->m_aomFilmGrainIn) != 0;',
                    'if (fclose(this->m_top->m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close AOM film grain model file after parse failure\\n");',
                    'this->m_top->m_aomFilmGrainIn = nullptr;',
                    '/* Write user SEI */',
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (m_param->filmGrain)',
                    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
                    'if (std::fclose(m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close film grain file \\"%s\\" after open failure\\n", m_param->filmGrain);',
                    'm_filmGrainIn = nullptr;',
                    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
                    'if (std::fclose(m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\" after open failure\\n", m_param->aomFilmGrain);',
                    'm_aomFilmGrainIn = nullptr;',
                    'm_bZeroLatency = 0;',
                    'if (m_filmGrainIn)',
                    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
                    'if (std::fclose(m_filmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close film grain file \\"%s\\"\\n", m_param->filmGrain);',
                    'm_filmGrainIn = nullptr;',
                    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
                    'if (std::fclose(m_aomFilmGrainIn))',
                    '    closeFailed = true;',
                    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\"\\n", m_param->aomFilmGrain);',
                    'm_aomFilmGrainIn = nullptr;',
                    '#ifdef SVT_HEVC',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'frameencoder film grain close guards must preserve parse-failure warning and null-reset ordering')

    print('Film grain close guard tests passed')


if __name__ == '__main__':
    main()
