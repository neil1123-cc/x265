#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (reconPlay && numEncoded)',
    'if (!pic_recon)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing recon output state for encoder %u\\n", m_id);',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis save state for encoder %u\\n", m_id);',
    'if (!reconPlay->writePicture(*pic_recon))',
    'copyInfo(analysisInfo);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread recon-state guardrail: {snippet}'))

    recon_guard_pos = text.find('if (reconPlay && numEncoded)')
    recon_null_pos = text.find('if (!pic_recon)', recon_guard_pos)
    recon_write_pos = text.find('if (!reconPlay->writePicture(*pic_recon))', recon_null_pos)
    save_guard_pos = text.find('if (isAbrSave && numEncoded)', recon_write_pos)
    save_null_pos = text.find('if (!pic_recon)', save_guard_pos)
    save_copy_pos = text.find('copyInfo(analysisInfo);', save_null_pos)
    if -1 in (recon_guard_pos, recon_null_pos, recon_write_pos, save_guard_pos, save_null_pos, save_copy_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must guard recon/save state before dereferencing pic_recon'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread recon-state guards')
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

    print('ABR thread recon-state guards validated')


if __name__ == '__main__':
    main()
