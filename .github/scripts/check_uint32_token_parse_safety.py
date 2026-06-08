#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'OPT("ctu") p->maxCUSize = parseOptionUint32Token(value, std::strlen(value), bError);',
    'OPT("min-cu-size") p->minCUSize = parseOptionUint32Token(value, std::strlen(value), bError);',
    'OPT("tu-intra-depth") p->tuQTMaxIntraDepth = parseOptionUint32Token(value, std::strlen(value), bError);',
    'OPT("tu-inter-depth") p->tuQTMaxInterDepth = parseOptionUint32Token(value, std::strlen(value), bError);',
    'OPT("max-tu-size") p->maxTUSize = parseOptionUint32Token(value, std::strlen(value), bError);',
    'OPT("max-merge") p->maxNumMergeCand = parseOptionUint32Token(value, std::strlen(value), bError);',
)
REQUIRED_COUNTS = {
    'bool bMaxCUSizeError = false;': 1,
    'uint32_t maxCUSize = parseOptionUint32Token(value, std::strlen(value), bMaxCUSizeError);': 1,
    'bError |= bMaxCUSizeError;': 1,
    'p->maxCUSize = maxCUSize;': 1,
    'bool bMinCUSizeError = false;': 1,
    'uint32_t minCUSize = parseOptionUint32Token(value, std::strlen(value), bMinCUSizeError);': 1,
    'bError |= bMinCUSizeError;': 1,
    'p->minCUSize = minCUSize;': 1,
    'bool bTuQTMaxIntraDepthError = false;': 1,
    'uint32_t tuQTMaxIntraDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxIntraDepthError);': 1,
    'bError |= bTuQTMaxIntraDepthError;': 1,
    'p->tuQTMaxIntraDepth = tuQTMaxIntraDepth;': 1,
    'bool bTuQTMaxInterDepthError = false;': 1,
    'uint32_t tuQTMaxInterDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxInterDepthError);': 1,
    'bError |= bTuQTMaxInterDepthError;': 1,
    'p->tuQTMaxInterDepth = tuQTMaxInterDepth;': 1,
    'bool bMaxTUSizeError = false;': 1,
    'uint32_t maxTUSize = parseOptionUint32Token(value, std::strlen(value), bMaxTUSizeError);': 1,
    'bError |= bMaxTUSizeError;': 1,
    'p->maxTUSize = maxTUSize;': 1,
    'bool bMaxNumMergeCandError = false;': 2,
    'uint32_t maxNumMergeCand = parseOptionUint32Token(value, std::strlen(value), bMaxNumMergeCandError);': 2,
    'bError |= bMaxNumMergeCandError;': 2,
    'p->maxNumMergeCand = maxNumMergeCand;': 2,
}


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, 'forbidden uint32 token regression: invalid values must not overwrite prior state'))
            return failures
    for snippet, expected_count in REQUIRED_COUNTS.items():
        actual_count = text.count(snippet)
        if actual_count != expected_count:
            failures.append((TARGET.as_posix(), 0, f'missing uint32 token guardrail count {expected_count} for: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check uint32 token parse safety guardrails')
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

    print('Uint32 token parse safety validated')


if __name__ == '__main__':
    main()
