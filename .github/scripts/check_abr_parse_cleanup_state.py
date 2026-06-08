#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(m_cliopt.zoneFile) || std::fclose(m_cliopt.zoneFile)',
    'std::ferror(m_cliopt.qpfile) || std::fclose(m_cliopt.qpfile)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(m_cliopt.zoneFile) != 0;',
    'if (std::fclose(m_cliopt.zoneFile))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(m_param, X265_LOG_WARNING, "Unable to close zonefile after parse failure\\n");',
    'bool closeFailed = std::ferror(m_cliopt.qpfile) != 0;',
    'if (std::fclose(m_cliopt.qpfile))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(m_param, X265_LOG_WARNING, "Unable to close qpfile after parse failure in %s\\n",',
    'm_cliopt.zoneFile = nullptr;',
    'm_parent->m_clioptArray[m_id].zoneFile = nullptr;',
    'm_cliopt.qpfile = nullptr;',
    'm_parent->m_clioptArray[m_id].qpfile = nullptr;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR parse cleanup short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ABR parse cleanup guardrail: {snippet}'))

    qpfile_block_start = text.find('if (!m_cliopt.parseQPFile(pic_orig[view]))')
    qpfile_block_end = text.find('if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)', qpfile_block_start if qpfile_block_start != -1 else 0)
    if qpfile_block_start == -1 or qpfile_block_end == -1:
        failures.append((TARGET.as_posix(), 0, 'missing ABR parse cleanup guardrail: qpfile parse failure block'))
    else:
        qpfile_block = text[qpfile_block_start:qpfile_block_end]
        for snippet in (
            'x265_log(nullptr, X265_LOG_ERROR, "can\'t parse qpfile for frame %d in %s\\n",',
            'm_ret = 1;',
            'goto fail;',
            'm_cliopt.qpfile = nullptr;',
            'm_parent->m_clioptArray[m_id].qpfile = nullptr;',
        ):
            if snippet not in qpfile_block:
                failures.append((TARGET.as_posix(), 0, f'missing ABR parse cleanup guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR parse cleanup state')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('ABR parse cleanup-state guard validated')


if __name__ == '__main__':
    main()
