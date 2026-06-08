#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (!reconPlay->writePicture(*pic_recon))',
    'x265_log(m_param, X265_LOG_ERROR, "Failed recon playback output for encoder %u\\n", m_id);',
    'if (!m_cliopt.recon[layer]->writePicture(pic_out[layer]))',
    'x265_log(m_param, X265_LOG_ERROR, "Failed layered recon output for encoder %u layer %d\\n", m_id, layer);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR recon-write guardrail: {snippet}'))

    recon_guard_pos = text.find('if (!reconPlay->writePicture(*pic_recon))')
    layered_guard_pos = text.find('if (!m_cliopt.recon[layer]->writePicture(pic_out[layer]))', recon_guard_pos)
    if -1 in (recon_guard_pos, layered_guard_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must check recon output write results before continuing'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread recon write guard')
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

    print('ABR recon write guard validated')


if __name__ == '__main__':
    main()
