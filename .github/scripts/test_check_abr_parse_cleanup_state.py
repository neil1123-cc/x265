#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_parse_cleanup_state.py')

# Coverage probes used by the scan for ABR parse cleanup guardrails.
NORMALIZED_PROBES = (
    'missing ABR parse cleanup guardrail: qpfile parse failure block',
    'forbidden ABR parse cleanup short-circuit close regression: ',
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
                    'bool closeFailed = std::ferror(m_cliopt.zoneFile) != 0;',
                    'if (std::fclose(m_cliopt.zoneFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(m_param, X265_LOG_WARNING, "Unable to close zonefile after parse failure\\n");',
                    'm_cliopt.zoneFile = nullptr;',
                    'm_parent->m_clioptArray[m_id].zoneFile = nullptr;',
                    'if (!m_cliopt.parseQPFile(pic_orig[view]))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "can\'t parse qpfile for frame %d in %s\\n",',
                    '        pic_orig[view].poc, profileName);',
                    'bool closeFailed = std::ferror(m_cliopt.qpfile) != 0;',
                    'if (std::fclose(m_cliopt.qpfile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(m_param, X265_LOG_WARNING, "Unable to close qpfile after parse failure in %s\\n",',
                    '        profileName);',
                    'm_cliopt.qpfile = nullptr;',
                    'm_parent->m_clioptArray[m_id].qpfile = nullptr;',
                    '    m_ret = 1;',
                    '    goto fail;',
                    '}',
                    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'std::fclose(m_cliopt.zoneFile);\n'})
        expect_fail(run_checker(root), 'missing ABR parse cleanup guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(m_cliopt.zoneFile) != 0;',
                    'if (std::fclose(m_cliopt.zoneFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(m_param, X265_LOG_WARNING, "Unable to close zonefile after parse failure\\n");',
                    'm_cliopt.zoneFile = nullptr;',
                    'm_parent->m_clioptArray[m_id].zoneFile = nullptr;',
                    'if (std::ferror(m_cliopt.zoneFile) || std::fclose(m_cliopt.zoneFile))',
                    '    x265_log(m_param, X265_LOG_WARNING, "Unable to close zonefile after parse failure\\n");',
                    'if (!m_cliopt.parseQPFile(pic_orig[view]))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "can\'t parse qpfile for frame %d in %s\\n",',
                    '        pic_orig[view].poc, profileName);',
                    'bool closeFailed = std::ferror(m_cliopt.qpfile) != 0;',
                    'if (std::fclose(m_cliopt.qpfile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(m_param, X265_LOG_WARNING, "Unable to close qpfile after parse failure in %s\\n",',
                    '        profileName);',
                    'm_cliopt.qpfile = nullptr;',
                    'm_parent->m_clioptArray[m_id].qpfile = nullptr;',
                    '    m_ret = 1;',
                    '    goto fail;',
                    '}',
                    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ABR parse cleanup short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(m_cliopt.zoneFile) != 0;',
                    'if (std::fclose(m_cliopt.zoneFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(m_param, X265_LOG_WARNING, "Unable to close zonefile after parse failure\\n");',
                    'm_cliopt.zoneFile = nullptr;',
                    'm_parent->m_clioptArray[m_id].zoneFile = nullptr;',
                    'if (!m_cliopt.parseQPFile(pic_orig[view]))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "can\'t parse qpfile for frame %d in %s\\n",',
                    '        pic_orig[view].poc, profileName);',
                    'bool closeFailed = std::ferror(m_cliopt.qpfile) != 0;',
                    'if (std::fclose(m_cliopt.qpfile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(m_param, X265_LOG_WARNING, "Unable to close qpfile after parse failure in %s\\n",',
                    '        profileName);',
                    'm_cliopt.qpfile = nullptr;',
                    'm_parent->m_clioptArray[m_id].qpfile = nullptr;',
                    '}',
                    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
                    'm_ret = 1;',
                    'goto fail;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), "missing ABR parse cleanup guardrail: m_ret = 1;")

    print('ABR parse cleanup-state guard tests passed')


if __name__ == '__main__':
    main()
