#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'else if (picField1.bitDepth != pic_in[view]->bitDepth ||',
    'picField1.colorSpace != pic_in[view]->colorSpace ||',
    'picField1.height != (pic_in[view]->height >> 1) ||',
    'picField1.framesize != (pic_in[view]->framesize >> 1))',
    'x265_log(m_param, X265_LOG_ERROR, "Mismatched field buffer metadata for view %d in %s\\n",',
    'if (picField1.stride[i] != pic_in[view]->stride[i] || picField2.stride[i] != pic_in[view]->stride[i])',
    'x265_log(m_param, X265_LOG_ERROR, "Mismatched field buffer stride for view %d plane %d in %s\\n",',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR field-reuse guardrail: {snippet}'))

    created_pos = text.find('fieldBuffersCreated = true;')
    metadata_pos = text.find('else if (picField1.bitDepth != pic_in[view]->bitDepth ||', created_pos)
    stride_pos = text.find('if (picField1.stride[i] != pic_in[view]->stride[i] || picField2.stride[i] != pic_in[view]->stride[i])', metadata_pos)
    pts_pos = text.find('picField1.pts = picField1.poc = pic_in[view]->poc;', stride_pos)
    if -1 in (created_pos, metadata_pos, stride_pos, pts_pos) or not (created_pos < metadata_pos < stride_pos < pts_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must validate reused field-buffer metadata and stride before copying field data'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread field-reuse guard')
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

    print('ABR field-reuse guard validated')


if __name__ == '__main__':
    main()
