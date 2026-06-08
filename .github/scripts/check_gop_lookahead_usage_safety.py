#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/slicetype.cpp')
REQUIRED_SNIPPETS = (
    'if (m_param->gopLookahead > 0 && keyFrameLimit <= m_param->bframes + 1)',
    'keyintLimit = X265_MAX(0, keyintLimit);',
    'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1))',
    'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1) && !m_extendGopBoundary)',
)
FORBIDDEN_SNIPPETS = (
    'if (m_param->gopLookahead && keyFrameLimit <= m_param->bframes + 1)',
    'if (m_param->gopLookahead && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1))',
    'if (m_param->gopLookahead && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1) && !m_extendGopBoundary)',
)
REGION_START = 'int keyFrameLimit = keylimit + m_lastKeyframe - frames[0]->frameNum - 1;'
REGION_END = 'if (!m_param->bIntraRefresh)'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden gop-lookahead usage regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing gop-lookahead usage guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'if (m_param->gopLookahead > 0 && keyFrameLimit <= m_param->bframes + 1)',
                'keyintLimit = X265_MAX(0, keyintLimit);',
                'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1))',
                'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1) && !m_extendGopBoundary)',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'GOP lookahead usage must preserve the reviewed keyFrameLimit gating order around keyintLimit extension and boundary reset'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check gop-lookahead usage safety guardrails')
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

    print('GOP lookahead usage safety validated')


if __name__ == '__main__':
    main()
