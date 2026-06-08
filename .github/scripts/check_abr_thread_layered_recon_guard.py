#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (numEncoded && m_cliopt.recon[layer])',
    'if (!pic_recon)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing layered recon state for encoder %u layer %d\\n", m_id, layer);',
    'if (!m_cliopt.recon[layer]->writePicture(pic_out[layer]))',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread layered-recon guardrail: {snippet}'))

    loop_pos = text.find('for (int layer = 0; layer < m_param->numLayers; layer++)')
    branch_pos = text.find('if (numEncoded && m_cliopt.recon[layer])', loop_pos)
    guard_pos = text.find('if (!pic_recon)', branch_pos)
    write_pos = text.find('if (!m_cliopt.recon[layer]->writePicture(pic_out[layer]))', guard_pos)
    if -1 in (loop_pos, branch_pos, guard_pos, write_pos) or not (loop_pos < branch_pos < guard_pos < write_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must guard layered recon state before writing recon pictures'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread layered recon guard')
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

    print('ABR thread layered recon guard validated')


if __name__ == '__main__':
    main()
