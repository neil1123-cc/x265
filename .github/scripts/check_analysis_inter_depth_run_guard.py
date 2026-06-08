#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'uint32_t interMaxDepthEntries = analysis->numCUsInFrame * analysis->numPartitions;',
    'if (!validateAnalysisDepthRun(analysis->numPartitions, depthBuf[d], (uint32_t)count, interMaxDepthEntries, bytes))',
    'x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Invalid inter depth run\\n");',
    'x265_free_analysis_data(m_param, analysis);',
    'm_aborted = true;',
    'return;',
    'std::fill_n(&(analysis->interData)->depth[count], bytes, depthBuf[d]);',
    'std::fill_n(&(analysis->interData)->modes[count], bytes, modeBuf[d]);',
)
FORBIDDEN_SNIPPETS = (
    'bytes = analysis->numPartitions >> (depthBuf[d] * 2);',
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
            failures.append((TARGET.as_posix(), 0, f'missing inter depth-run guardrail: {snippet}'))
    loop_anchor = text.find('uint32_t interMaxDepthEntries = analysis->numCUsInFrame * analysis->numPartitions;')
    validate_snippet = 'if (!validateAnalysisDepthRun(analysis->numPartitions, depthBuf[d], (uint32_t)count, interMaxDepthEntries, bytes))'
    depth_write_snippet = 'std::fill_n(&(analysis->interData)->depth[count], bytes, depthBuf[d]);'
    mode_write_snippet = 'std::fill_n(&(analysis->interData)->modes[count], bytes, modeBuf[d]);'
    loop_end_anchor = text.find('count += bytes;', loop_anchor if loop_anchor != -1 else 0)
    loop_scope = text[loop_anchor:loop_end_anchor] if -1 not in (loop_anchor, loop_end_anchor) else text
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in loop_scope:
            failures.append((TARGET.as_posix(), 0, f'forbidden inter depth-run regression: {snippet}'))

    max_pos = loop_anchor
    validate_pos = text.find(validate_snippet, loop_anchor)
    depth_write_pos = text.find(depth_write_snippet, validate_pos)
    mode_write_pos = text.find(mode_write_snippet, depth_write_pos)
    if -1 not in (max_pos, validate_pos, depth_write_pos, mode_write_pos) and not (max_pos < validate_pos < depth_write_pos < mode_write_pos):
        failures.append((TARGET.as_posix(), 0, 'inter depth-run validation must happen before inter depth/mode writes'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check inter depth-run validation guardrail')
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

    print('Inter depth-run validation guard validated')


if __name__ == '__main__':
    main()
