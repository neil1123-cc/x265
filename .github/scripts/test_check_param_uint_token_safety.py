#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_uint_token_safety.py')

# Normalized checker probes used by the coverage scan for unsigned-token guardrails.
NORMALIZED_PROBES = (
    'missing uint token helper definition',
    'forbidden uint16 token regression: wrapper must use shared non-negative token helper',
    'forbidden uint8 token regression: wrapper must use shared non-negative token helper',
    'forbidden uint32 token regression: wrapper must use shared non-negative token helper',
    'forbidden uint token regression: ',
    'missing uint token guardrail: ',
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
                    '#include <charconv>',
                    'static int parseOptionIntToken(const char* token, size_t length, bool& bError)',
                    'const char* digitsBegin = begin;',
                    'std::from_chars_result parsed = std::from_chars(digitsBegin, end, magnitude, base);',
                    'if (parsed.ec != std::errc() || parsed.ptr != end)',
                    'static const char* parsePresetIndexName(const char* preset)',
                    'static bool parseOptionNonNegativeIntToken(const char* token, size_t length, int maxValue, int& value)',
                    'int parsedValue = parseOptionIntToken(token, length, bLocalError);',
                    'if (bLocalError || parsedValue < 0 || parsedValue > maxValue)',
                    'static uint16_t parseOptionUint16Token(const char* token, size_t length, bool& bError)',
                    'if (!parseOptionNonNegativeIntToken(token, length, UINT16_MAX, value))',
                    'return (uint16_t)value;',
                    'static uint8_t parseOptionUint8Token(const char* token, size_t length, bool& bError)',
                    'static uint8_t parseOptionUint8Value(const char* value, bool& bError)',
                    'static uint8_t parseOptionUint8Value(const char* value, bool& bError)\n{\n    if (!value)\n    {\n        bError = true;\n        return 0;\n    }',
                    'if (!parseOptionNonNegativeIntToken(token, length, UINT8_MAX, value))',
                    'return (uint8_t)value;',
                    'static uint32_t parseOptionUint32Token(const char* token, size_t length, bool& bError)',
                    'if (!parseOptionNonNegativeIntToken(token, length, INT_MAX, value))',
                    'return (uint32_t)value;',
                    'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
                    'uint32_t maxCUSize = parseOptionUint32Token(value, std::strlen(value), bMaxCUSizeError);',
                    'p->maxCUSize = maxCUSize;',
                    'uint16_t minLuma = parseOptionUint16Token(value, std::strlen(value), bMinLumaError);',
                    'p->minLuma = minLuma;',
                    'uint16_t maxLuma = parseOptionUint16Token(value, std::strlen(value), bMaxLumaError);',
                    'p->maxLuma = maxLuma;',
                    'static bool parseOptionUint16Pair(const char* value, char separatorChar, uint16_t& first, uint16_t& second)',
                    "bool bLocalError = !parseOptionUint16Pair(value, ',', maxCLL, maxFALL);",
                    'svtHevcParam->maxCLL = maxCLL;',
                    'svtHevcParam->maxFALL = maxFALL;',
                    'uint8_t predStructure = parseOptionUint8Value(value, bPredStructureError);',
                    'svtHevcParam->predStructure = predStructure;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static int parseOptionIntToken(const char* token, size_t length, bool& bError)',
                    '{',
                    '    char number[16];',
                    '    std::memcpy(number, token, length);',
                    '    return x265_atoi(number, bError);',
                    '}',
                    'static const char* parsePresetIndexName(const char* preset)',
                    'static uint16_t parseOptionUint16Token(const char* token, size_t length, bool& bError)',
                    '{',
                    '    int value = parseOptionIntToken(token, length, bError);',
                    '    if (bError || value > UINT16_MAX)',
                    '        return 0;',
                    '}',
                    'static uint8_t parseOptionUint8Token(const char* token, size_t length, bool& bError)',
                    'static uint32_t parseOptionUint32Token(const char* token, size_t length, bool& bError)',
                    'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
                    'OPT("min-luma") p->minLuma = parseOptionUint16Token(value, std::strlen(value), bError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden uint')

    print('Unsigned token helper safety tests passed')


if __name__ == '__main__':
    main()
