#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'bool AbrEncoder::allocBuffers()',
    'm_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
    'if (!m_readFlag[pass])',
    'goto fail;',
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
            failures.append((TARGET.as_posix(), 0, f'missing abr allocBuffers readFlag guardrail: {snippet}'))

    def extract_braced_block(signature):
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

    alloc_buffers_text = extract_braced_block('bool AbrEncoder::allocBuffers()')
    branch1_start = alloc_buffers_text.find('if (primaryParam->numViews > 1)')
    branch1_end = alloc_buffers_text.find('else', branch1_start if branch1_start != -1 else 0)
    branch2_start = alloc_buffers_text.find('for (uint8_t pass = 0; pass < m_numEncodes; pass++)', branch1_end if branch1_end != -1 else 0)
    branch2_end = alloc_buffers_text.find('#if ENABLE_MULTIVIEW', branch2_start if branch2_start != -1 else 0)
    branch1_text = alloc_buffers_text[branch1_start:branch1_end] if -1 not in (branch1_start, branch1_end) else alloc_buffers_text
    branch2_text = alloc_buffers_text[branch2_start:branch2_end] if -1 not in (branch2_start, branch2_end) else alloc_buffers_text

    def has_guarded_readflag(block):
        alloc_pos = block.find('m_readFlag[pass] = X265_MALLOC(int, m_queueSize);')
        guard_pos = block.find('if (!m_readFlag[pass])', alloc_pos if alloc_pos != -1 else 0)
        goto_pos = block.find('goto fail;', guard_pos if guard_pos != -1 else 0)
        return -1 not in (alloc_pos, guard_pos, goto_pos) and alloc_pos < guard_pos < goto_pos

    if not has_guarded_readflag(branch1_text) or not has_guarded_readflag(branch2_text):
        failures.append((TARGET.as_posix(), 0, 'AbrEncoder::allocBuffers must guard m_readFlag[pass] allocation in both queue setup branches'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check AbrEncoder allocBuffers readFlag allocation guards')
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

    print('AbrEncoder allocBuffers readFlag guards validated')


if __name__ == '__main__':
    main()
