#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_uint32_token_parse_safety.py')

# Normalized checker probe used by the coverage scan for occurrence-count guardrail failures.
NORMALIZED_PROBES = (
    'missing uint32 token guardrail count  for: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("max-merge")',
                    '{',
                    '    bool bMaxNumMergeCandError = false;',
                    '    uint32_t maxNumMergeCand = parseOptionUint32Token(value, std::strlen(value), bMaxNumMergeCandError);',
                    '    bError |= bMaxNumMergeCandError;',
                    '    if (!bMaxNumMergeCandError)',
                    '        p->maxNumMergeCand = maxNumMergeCand;',
                    '}',
                    'OPT("ctu")',
                    '{',
                    '    bool bMaxCUSizeError = false;',
                    '    uint32_t maxCUSize = parseOptionUint32Token(value, std::strlen(value), bMaxCUSizeError);',
                    '    bError |= bMaxCUSizeError;',
                    '    if (!bMaxCUSizeError)',
                    '        p->maxCUSize = maxCUSize;',
                    '}',
                    'OPT("min-cu-size")',
                    '{',
                    '    bool bMinCUSizeError = false;',
                    '    uint32_t minCUSize = parseOptionUint32Token(value, std::strlen(value), bMinCUSizeError);',
                    '    bError |= bMinCUSizeError;',
                    '    if (!bMinCUSizeError)',
                    '        p->minCUSize = minCUSize;',
                    '}',
                    'OPT("tu-intra-depth")',
                    '{',
                    '    bool bTuQTMaxIntraDepthError = false;',
                    '    uint32_t tuQTMaxIntraDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxIntraDepthError);',
                    '    bError |= bTuQTMaxIntraDepthError;',
                    '    if (!bTuQTMaxIntraDepthError)',
                    '        p->tuQTMaxIntraDepth = tuQTMaxIntraDepth;',
                    '}',
                    'OPT("tu-inter-depth")',
                    '{',
                    '    bool bTuQTMaxInterDepthError = false;',
                    '    uint32_t tuQTMaxInterDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxInterDepthError);',
                    '    bError |= bTuQTMaxInterDepthError;',
                    '    if (!bTuQTMaxInterDepthError)',
                    '        p->tuQTMaxInterDepth = tuQTMaxInterDepth;',
                    '}',
                    'OPT("max-tu-size")',
                    '{',
                    '    bool bMaxTUSizeError = false;',
                    '    uint32_t maxTUSize = parseOptionUint32Token(value, std::strlen(value), bMaxTUSizeError);',
                    '    bError |= bMaxTUSizeError;',
                    '    if (!bMaxTUSizeError)',
                    '        p->maxTUSize = maxTUSize;',
                    '}',
                    'OPT("max-merge")',
                    '{',
                    '    bool bMaxNumMergeCandError = false;',
                    '    uint32_t maxNumMergeCand = parseOptionUint32Token(value, std::strlen(value), bMaxNumMergeCandError);',
                    '    bError |= bMaxNumMergeCandError;',
                    '    if (!bMaxNumMergeCandError)',
                    '        p->maxNumMergeCand = maxNumMergeCand;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("ctu") p->maxCUSize = parseOptionUint32Token(value, std::strlen(value), bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden uint32 token regression: invalid values must not overwrite prior state')

    print('Uint32 token parse safety tests passed')


if __name__ == '__main__':
    main()
