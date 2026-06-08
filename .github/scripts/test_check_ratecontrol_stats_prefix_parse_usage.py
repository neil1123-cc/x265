#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_stats_prefix_parse_usage.py')

# Coverage probes used by the scan for ratecontrol stats-prefix parsing guardrails.
NORMALIZED_PROBES = (
    'forbidden ratecontrol stats-prefix parse regression: ',
    'missing ratecontrol stats-prefix parse guardrail: ',
    'parseStatsPrefix must tokenize and validate the frame and encode-order prefix before publishing consumedPrefix',
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
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'static bool parseStatsPrefix(const char* p, int& frameNumber, int& encodeOrder, int& consumedPrefix)',
                    'if (!p)',
                    "while (*cursor == ' ' || *cursor == '\\r' || *cursor == '\\n')",
                    'if (std::strncmp(cursor, "in:", 3))',
                    'if (!tokenLength || tokenLength >= 16 || std::strncmp(end, " out:", 5))',
                    'if (!parseRateControlIntToken(token, frameNumber))',
                    "if (!tokenLength || tokenLength >= 16 || *end != ' ')",
                    'if (!parseRateControlIntToken(token, encodeOrder))',
                    'consumedPrefix = (int)(end - p);',
                    'return consumedPrefix > 0;',
                    'static bool parseStatsLineLabel(const char*& cursor, const char* label)',
                    'int frameNumber = -1;',
                    'int encodeOrder = -1;',
                    'int e = -1;',
                    'int consumedPrefix = 0;',
                    'if (!parseStatsPrefix(p, frameNumber, encodeOrder, consumedPrefix))',
                    'e = -1;',
                    'e = 2;',
                    'if (frameNumber < 0 || frameNumber >= m_numEntries)',
                    'if (encodeOrder < 0 || encodeOrder >= m_numEntries)',
                    'rce = &m_rce2Pass[encodeOrder];',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': 'e = sscanf(p, " in:%d out:%d%n", &frameNumber, &encodeOrder, &consumedPrefix);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ratecontrol stats-prefix parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'static bool parseStatsPrefix(const char* p, int& frameNumber, int& encodeOrder, int& consumedPrefix)',
                    'if (!p)',
                    "while (*cursor == ' ' || *cursor == '\\r' || *cursor == '\\n')",
                    'if (std::strncmp(cursor, "in:", 3))',
                    'if (!tokenLength || tokenLength >= 16 || std::strncmp(end, " out:", 5))',
                    'if (!parseRateControlIntToken(token, frameNumber))',
                    "if (!tokenLength || tokenLength >= 16 || *end != ' ')",
                    'if (!parseRateControlIntToken(token, encodeOrder))',
                    'consumedPrefix = (int)(end - p);',
                    'return consumedPrefix > 0;',
                    'static bool parseStatsLineLabel(const char*& cursor, const char* label)',
                    'int frameNumber = -1;',
                    'int encodeOrder = -1;',
                    'int e = -1;',
                    'int consumedPrefix = 0;',
                    'e = 2;',
                    'if (!parseStatsPrefix(p, frameNumber, encodeOrder, consumedPrefix))',
                    'e = -1;',
                    'if (frameNumber < 0 || frameNumber >= m_numEntries)',
                    'if (encodeOrder < 0 || encodeOrder >= m_numEntries)',
                    'rce = &m_rce2Pass[encodeOrder];',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'stats-file loading must derive frameNumber and encodeOrder from parseStatsPrefix before accepting the prefix and indexing m_rce2Pass')

    print('Ratecontrol stats-prefix parse guard tests passed')


if __name__ == '__main__':
    main()
