#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
Y4M_BRANCH = 'x265_log(param, X265_LOG_ERROR, "VMAF supports YUV file format only.\\n");'
CSP_BRANCH = 'x265_log(param, X265_LOG_ERROR, "VMAF will support only yuv420p, yu422p, yu444p, yuv420p10le, yuv422p10le, yuv444p10le formats.\\n");'
INPUT_LOOP = 'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)'
RECON_LOOP = 'for (int releaseIdx = 0; releaseIdx < param->numLayers; releaseIdx++)'
REQUIRED_SNIPPETS = (
    Y4M_BRANCH,
    CSP_BRANCH,
    INPUT_LOOP,
    RECON_LOOP,
    'if (this->input[releaseIdx])',
    'this->input[releaseIdx]->release();',
    'this->input[releaseIdx] = nullptr;',
    'if (this->recon[releaseIdx])',
    'this->recon[releaseIdx]->release();',
    'this->recon[releaseIdx] = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI VMAF format cleanup guardrail: {snippet}'))

    y4m_pos = text.find(Y4M_BRANCH)
    y4m_input_loop_pos = text.find(INPUT_LOOP, y4m_pos)
    y4m_input_release_pos = text.find('this->input[releaseIdx]->release();', y4m_input_loop_pos)
    y4m_recon_loop_pos = text.find(RECON_LOOP, y4m_input_release_pos)
    y4m_recon_release_pos = text.find('this->recon[releaseIdx]->release();', y4m_recon_loop_pos)
    y4m_return_pos = text.find('return true;', y4m_recon_release_pos)
    if -1 in (y4m_pos, y4m_input_loop_pos, y4m_input_release_pos, y4m_recon_loop_pos, y4m_recon_release_pos, y4m_return_pos) or not (y4m_pos < y4m_input_loop_pos < y4m_input_release_pos < y4m_recon_loop_pos < y4m_recon_release_pos < y4m_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI VMAF Y4M rejection must release started inputs and recon handles before returning'))

    csp_pos = text.find(CSP_BRANCH)
    csp_input_loop_pos = text.find(INPUT_LOOP, csp_pos)
    csp_input_release_pos = text.find('this->input[releaseIdx]->release();', csp_input_loop_pos)
    csp_recon_loop_pos = text.find(RECON_LOOP, csp_input_release_pos)
    csp_recon_release_pos = text.find('this->recon[releaseIdx]->release();', csp_recon_loop_pos)
    csp_return_pos = text.find('return true;', csp_recon_release_pos)
    if -1 in (csp_pos, csp_input_loop_pos, csp_input_release_pos, csp_recon_loop_pos, csp_recon_release_pos, csp_return_pos) or not (csp_pos < csp_input_loop_pos < csp_input_release_pos < csp_recon_loop_pos < csp_recon_release_pos < csp_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI VMAF colorspace rejection must release started inputs and recon handles before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI VMAF format cleanup')
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

    print('CLI VMAF format cleanup validated')


if __name__ == '__main__':
    main()
