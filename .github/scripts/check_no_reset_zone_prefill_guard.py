#!/usr/bin/env python3
import argparse
from pathlib import Path


SLICETYPE_H_TARGET = Path('source/encoder/slicetype.h')
SLICETYPE_CPP_TARGET = Path('source/encoder/slicetype.cpp')
ENCODER_TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SLICETYPE_H_SNIPPETS = (
    'Frame*  peekDecidedPicture();',
)
REQUIRED_SLICETYPE_CPP_SNIPPETS = (
    'Frame* Lookahead::peekDecidedPicture()',
    'Frame* out = m_outputQueue.first();',
    'out = m_outputQueue.first();',
    'findJob(-1); /* run slicetypeDecide() if necessary */',
    'm_outputSignal.wait();',
)
REQUIRED_ENCODER_SNIPPETS = (
    'if (!m_param->bResetZoneConfig && m_param->reconfigWindowSize && m_param->rc.zonefileCount &&',
    '(m_encodedFrameNum % m_param->reconfigWindowSize == 0))',
    'Frame* nextFrame = m_lookahead->peekDecidedPicture();',
    'int zoneIndex = (m_encodedFrameNum / m_param->reconfigWindowSize) % m_param->rc.zonefileCount;',
    'if (!zoneReadCount || !zoneWriteCount || !zone || !zone->zoneParam ||',
    '"Zone reconfiguration state is incomplete before encode order %d (POC %d)\\n",',
    'if (zoneWrite <= zoneRead)',
    '"Zone reconfiguration window at encode order %d (POC %d) was not prefilled before encoding reached it\\n",',
    'if (zone->startFrame != m_encodedFrameNum)',
    '"Zone reconfiguration window at encode order %d (POC %d) is staged for startFrame %d instead of the current reconfig window\\n",',
    'frameEnc[0] = m_lookahead->getDecidedPicture();',
)


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return text
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    slicetype_h_path = repo_root / SLICETYPE_H_TARGET
    slicetype_cpp_path = repo_root / SLICETYPE_CPP_TARGET
    encoder_path = repo_root / ENCODER_TARGET
    for path in (slicetype_h_path, slicetype_cpp_path, encoder_path):
        if not path.is_file():
            return [(path.relative_to(repo_root).as_posix(), 0, 'missing file')]

    slicetype_h_text = slicetype_h_path.read_text(encoding='utf-8', errors='ignore')
    slicetype_cpp_text = slicetype_cpp_path.read_text(encoding='utf-8', errors='ignore')
    encoder_text = encoder_path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    for snippet in REQUIRED_SLICETYPE_H_SNIPPETS:
        if snippet not in slicetype_h_text:
            failures.append((SLICETYPE_H_TARGET.as_posix(), 0, f'missing no-reset zone prefill guardrail: {snippet}'))
    for snippet in REQUIRED_SLICETYPE_CPP_SNIPPETS:
        if snippet not in slicetype_cpp_text:
            failures.append((SLICETYPE_CPP_TARGET.as_posix(), 0, f'missing no-reset zone prefill guardrail: {snippet}'))
    for snippet in REQUIRED_ENCODER_SNIPPETS:
        if snippet not in encoder_text:
            failures.append((ENCODER_TARGET.as_posix(), 0, f'missing no-reset zone prefill guardrail: {snippet}'))

    peek_text = extract_braced_block(slicetype_cpp_text, 'Frame* Lookahead::peekDecidedPicture()')
    if 'm_outputQueue.popFront()' in peek_text:
        failures.append((SLICETYPE_CPP_TARGET.as_posix(), 0, 'peekDecidedPicture must inspect the output queue without consuming it'))

    peek_pos = encoder_text.find('Frame* nextFrame = m_lookahead->peekDecidedPicture();')
    read_write_pos = encoder_text.find('if (zoneWrite <= zoneRead)', peek_pos if peek_pos != -1 else 0)
    staged_pos = encoder_text.find('if (zone->startFrame != m_encodedFrameNum)', read_write_pos if read_write_pos != -1 else 0)
    get_pos = encoder_text.find('frameEnc[0] = m_lookahead->getDecidedPicture();', staged_pos if staged_pos != -1 else 0)
    if -1 in (peek_pos, read_write_pos, staged_pos, get_pos) or not (peek_pos < read_write_pos < staged_pos < get_pos):
        failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder::encode must preflight the no-reset zone window before consuming the next decided picture'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check no-reset zone prefill fail-fast guards')
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

    print('No-reset zone prefill guard validated')


if __name__ == '__main__':
    main()
