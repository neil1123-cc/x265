#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'void Encoder::fetchStats(x265_stats *stats, size_t statsSizeBytes, int layer)',
    'if (statsSizeBytes >= sizeof(*stats))',
    'stats->globalPsnrY = m_analyzeAll[layer].m_psnrSumY;',
    'if (stats->encodedPictureCount > 0)',
    'stats->statsI.numPics = m_analyzeI[layer].m_numPics;',
    'if (m_param->csvLogLevel >= 2 || m_param->maxCLL || m_param->maxFALL)',
    '/* If new statistics are added to x265_stats, we must check here whether the',
)
FORBIDDEN_SNIPPETS = (
    'if (statsSizeBytes >= sizeof(stats))',
)
REGION_START = 'void Encoder::fetchStats(x265_stats *stats, size_t statsSizeBytes, int layer)'
REGION_END = 'void Encoder::finishFrameStats(Frame* curFrame, FrameEncoder *curEncoder, x265_frame_stats* frameStats, int inPoc, int layer)'
SIZE_GUARD = 'if (statsSizeBytes >= sizeof(*stats))'


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


def find_matching_brace(text, open_pos):
    depth = 0
    for idx in range(open_pos, len(text)):
        if text[idx] == '{':
            depth += 1
        elif text[idx] == '}':
            depth -= 1
            if depth == 0:
                return idx
    return -1


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
            failures.append((TARGET.as_posix(), 0, f'forbidden encoder_get_stats size regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing encoder_get_stats size guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(region, REQUIRED_SNIPPETS):
            failures.append((TARGET.as_posix(), 0, 'fetchStats must guard x265_stats writes with sizeof(*stats) before populating the aggregate and per-slice statistics'))
        guard_pos = region.find(SIZE_GUARD)
        first_stats_use = region.find('stats->')
        if first_stats_use != -1 and first_stats_use < guard_pos:
            failures.append((TARGET.as_posix(), 0, 'fetchStats must not touch stats fields before the sizeof(*stats) guard is checked'))
        brace_open = region.find('{', guard_pos)
        brace_close = find_matching_brace(region, brace_open)
        if brace_open == -1 or brace_close == -1:
            failures.append((TARGET.as_posix(), 0, 'fetchStats size-guard block could not be validated'))
        else:
            outside_guard = region[:guard_pos] + region[brace_close + 1:]
            if 'stats->' in outside_guard:
                failures.append((TARGET.as_posix(), 0, 'fetchStats must keep every stats field access inside the sizeof(*stats) compatibility guard'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_encoder_get_stats size guardrails')
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

    print('Encoder get stats size guard validated')


if __name__ == '__main__':
    main()
