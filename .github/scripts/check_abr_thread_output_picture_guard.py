#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (nal)',
    'if (!pic_recon)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing output picture state for encoder %u\\n", m_id);',
    'int frameBytes = m_cliopt.output->writeFrame(p_nal, nal, pic_out[0]);',
    'pts_queue->push(-pic_out[0].pts);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread output-picture guardrail: {snippet}'))

    nal_pos = text.find('if (nal)')
    guard_pos = text.find('if (!pic_recon)', nal_pos)
    write_pos = text.find('int frameBytes = m_cliopt.output->writeFrame(p_nal, nal, pic_out[0]);', guard_pos)
    pts_pos = text.find('pts_queue->push(-pic_out[0].pts);', write_pos)
    if -1 in (nal_pos, guard_pos, write_pos, pts_pos) or not (nal_pos < guard_pos < write_pos < pts_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must guard output picture state before writeFrame/PTS use'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread output-picture guard')
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

    print('ABR thread output-picture guard validated')


if __name__ == '__main__':
    main()
