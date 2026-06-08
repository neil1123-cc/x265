#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_dolby_rpu_eof_guard.py')

# Coverage probes used by the scan for ABR Dolby Vision EOF guardrails.
NORMALIZED_PROBES = (
    'threadMain must close the Dolby Vision RPU stream before clearing local and parent pointers after read failure',
    'threadMain must distinguish Dolby Vision EOF from stream errors before success logging',
    'missing ABR Dolby Vision EOF guardrail: ',
    'forbidden ABR Dolby Vision EOF regression: ',
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
                    'if (bDolbyVisionRPU)',
                    '{',
                    '    auto failDolbyVisionRpu = [&]()',
                    '    {',
                    '        bool closeFailed = std::ferror(m_cliopt.dolbyVisionRpu) != 0;',
                    '        if (std::fclose(m_cliopt.dolbyVisionRpu))',
                    '            closeFailed = true;',
                    '        x265_log(m_param, X265_LOG_WARNING, "Unable to close Dolby Vision RPU stream after read failure in %s\\n",',
                    '            profileName);',
                    '        m_cliopt.dolbyVisionRpu = nullptr;',
                    '        m_parent->m_clioptArray[m_id].dolbyVisionRpu = nullptr;',
                    '    };',
                    '    if (m_cliopt.rpuParser(&picField1) > 0)',
                    '    {',
                    '        if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))',
                    '            failDolbyVisionRpu();',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    if (m_cliopt.rpuParser(&picField2) > 0)',
                    '    {',
                    '        if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))',
                    '            failDolbyVisionRpu();',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    if (m_cliopt.rpuParser(pic_in[view]) > 0)',
                    '    {',
                    '        if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))',
                    '            failDolbyVisionRpu();',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    if (!m_cliopt.dolbyVisionRpu)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing Dolby Vision RPU stream state in %s\\n",',
                    '            profileName);',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    int nextRpuByte = fgetc(m_cliopt.dolbyVisionRpu);',
                    '    if (nextRpuByte != EOF)',
                    '        x265_log(nullptr, X265_LOG_WARNING, "Dolby Vision RPU count is greater than frame count in %s\\n",',
                    '            profileName);',
                    '    else if (ferror(m_cliopt.dolbyVisionRpu))',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Unable to finalize Dolby Vision RPU stream state in %s\\n",',
                    '            profileName);',
                    '        failDolbyVisionRpu();',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    else',
                    '        x265_log(nullptr, X265_LOG_INFO, "VES muxing with Dolby Vision RPU file successful in %s\\n",',
                    '            profileName);',
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
                'source/abrEncApp.cpp': 'if (fgetc(m_cliopt.dolbyVisionRpu) != EOF)\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ABR Dolby Vision EOF regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'if (bDolbyVisionRPU)',
                    '{',
                    '    auto failDolbyVisionRpu = [&]()',
                    '    {',
                    '        m_cliopt.dolbyVisionRpu = nullptr;',
                    '    };',
                    '    if (m_cliopt.rpuParser(&picField1) > 0)',
                    '        goto fail;',
                    '    if (m_cliopt.rpuParser(&picField2) > 0)',
                        '        goto fail;',
                    '    if (m_cliopt.rpuParser(pic_in[view]) > 0)',
                    '        goto fail;',
                    '    if (!m_cliopt.dolbyVisionRpu)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing Dolby Vision RPU stream state in %s\\n",',
                    '            profileName);',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    int nextRpuByte = fgetc(m_cliopt.dolbyVisionRpu);',
                    '    if (nextRpuByte != EOF)',
                    '        x265_log(nullptr, X265_LOG_WARNING, "Dolby Vision RPU count is greater than frame count in %s\\n",',
                    '            profileName);',
                    '    else if (ferror(m_cliopt.dolbyVisionRpu))',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Unable to finalize Dolby Vision RPU stream state in %s\\n",',
                    '            profileName);',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    else',
                    '        x265_log(nullptr, X265_LOG_INFO, "VES muxing with Dolby Vision RPU file successful in %s\\n",',
                    '            profileName);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'threadMain must retire the Dolby Vision RPU stream on read failures before propagating parser errors through m_ret')

    print('ABR Dolby Vision EOF guard tests passed')


if __name__ == '__main__':
    main()
