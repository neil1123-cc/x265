#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_strict_scan_parsing_usage.py')

# Coverage probes used by the scan for strict-scan parsing guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'forbidden strict-scan regression: ',
    'missing strict-scan guardrail: ',
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
                    'bError = sscanf(value, "%d:%d%n", &p->vui.sarWidth, &p->vui.sarHeight, &consumed) != 2 || value[consumed] != \'\\0\';',
                    "char* zoneEnd = (i + 1 < zoneCount) ? std::strchr((char*)c, '/') : nullptr;",
                    'static const char* findTokenChar(const char* token, size_t length, char target)',
                    'static bool parseZoneOptionEntry(char* entry, char* entryEnd, x265_zone& zone)',
                    'if (splitCommaOption(entry, parts, lengths, 3) != 3)',
                    "const char* equals = findTokenChar(parts[2], lengths[2], '=');",
                    "if (parts[2][0] == 'q')",
                    "else if (parts[2][0] == 'b')",
                    'int qp = parseOptionIntToken(equals + 1, modeValueLength, bLocalError);',
                    'if (!parseOptionDoubleToken(equals + 1, modeValueLength, bitrateFactor) || bitrateFactor <= 0.0)',
                    'if (zoneEnd)',
                    'static int parseOptionIntToken(const char* token, size_t length, bool& bError)',
                    'const char* separator = std::strchr(value, \':\');',
                    'separator = std::strchr(value, \',\');',
                    'bool bLocalError = !parseOptionIntPair(value, *separator, tcOffset, betaOffset);',
                    'p->deblockingFilterTCOffset = tcOffset;',
                    'p->deblockingFilterBetaOffset = betaOffset;',
                    'int offset = parseOptionIntToken(value, std::strlen(value), bLocalError);',
                    'p->deblockingFilterBetaOffset = offset;',
                    'p->bEnableLoopFilter = atobool(value);',
                    'static uint16_t parseOptionUint16Token(const char* token, size_t length, bool& bError)',
                    'static bool splitOptionPair(const char* value, char separatorChar,',
                    'static bool parseOptionUint16Pair(const char* value, char separatorChar, uint16_t& first, uint16_t& second)',
                    "bool bLocalError = !parseOptionIntPair(value, ':', sarWidth, sarHeight);",
                    'p->vui.sarWidth = sarWidth;',
                    'p->vui.sarHeight = sarHeight;',
                    "bool bLocalError = !parseOptionUint16Pair(value, ',', maxCLL, maxFALL);",
                    'p->maxCLL = maxCLL;',
                    'p->maxFALL = maxFALL;',
                    'svtHevcParam->maxCLL = maxCLL;',
                    'svtHevcParam->maxFALL = maxFALL;',
                    'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
                    'static bool parseOptionUintPair(const char* value, char separatorChar, uint32_t& first, uint32_t& second)',
                    'static bool parseOptionIntQuad(const char* value, int& first, int& second, int& third, int& fourth)',
                    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
                    'uint32_t parsedNumerator = 0;',
                    'uint32_t parsedDenominator = 0;',
                    "bError |= !parseFpsValue(value, p->fpsNum, p->fpsDenom);",
                    "bError |= !parseFpsValue(value, svtHevcParam->frameRateNumerator, svtHevcParam->frameRateDenominator);",
                    'if (svtHevcParam->frameRateDenominator == 1 && svtHevcParam->frameRateNumerator < 1000)',
                    "bError |= !parseOptionIntPair(value, 'x', p->sourceWidth, p->sourceHeight);",
                    'bool bDisplayWindowError = !parseOptionIntQuad(value,',
                    'p->vui.bEnableDefaultDisplayWindowFlag = 1;',
                    'p->vui.defDispWinLeftOffset = defDispWinLeftOffset;',
                    "if (!parseOptionIntPair(value, 'x', sourceWidth, sourceHeight))",
                    'svtHevcParam->sourceWidth = (uint32_t)sourceWidth;',
                    'svtHevcParam->sourceHeight = (uint32_t)sourceHeight;',
                )) + '\n',
                'source/filters/zimgfilter.cpp': '\n'.join((
                    'const char* findZimgChar(const char* begin, const char* end, char target)',
                    'ZimgClauseParseResult parseZimgClause(const char* cursor, const char* end, const char*& next,',
                    "const char* open = findZimgChar(cursor, end, '(');",
                    "const char* close = findZimgChar(valueBegin, end, ')');",
                    'switch (parseZimgClause(cursor, end, next, pName, sizeof(pName), pValue, sizeof(pValue)))',
                    'int splitZimgCommaTokens(const char* value, const char* parts[], size_t lengths[], int maxParts)',
                    'bool parseZimgDoubleToken(const char* token, size_t length, double& value)',
                    'bool parseZimgIntToken(const char* token, size_t length, int& value)',
                    'if (splitZimgCommaTokens(pValue, parts, lengths, 4) != 4 ||',
                    'int count = splitZimgCommaTokens(pValue, parts, lengths, 4);',
                    'if (!((count == 2 || count == 4) &&',
                    'parseZimgIntToken(parts[0], lengths[0], rWidth)',
                    'parseZimgDoubleToken(parts[2], lengths[2], param1)',
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
                    'bError = sscanf(value, "%d:%d", &p->vui.sarWidth, &p->vui.sarHeight) != 2;',
                    'if (sscanf(value, "%u/%u", &p->fpsNum, &p->fpsDenom) == 2)',
                    'bError |= sscanf(value, "%dx%d", &p->sourceWidth, &p->sourceHeight) != 2;',
                    'bError |= sscanf(value, "%d,%d,%d,%d", &p->vui.defDispWinLeftOffset, &p->vui.defDispWinTopOffset, &p->vui.defDispWinRightOffset, &p->vui.defDispWinBottomOffset) != 4;',
                    'sscanf(c, "%d,%d,q=%d%n", &p->rc.zones[i].startFrame, &p->rc.zones[i].endFrame, &p->rc.zones[i].qp, &len)',
                )) + '\n',
                'source/filters/zimgfilter.cpp': 'int count = std::sscanf(pValue, "%lf,%lf,%lf,%lf", &dLeft, &dTop, &dRight, &dBottom);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden strict-scan regression')

    print('Strict scan parsing guard tests passed')


if __name__ == '__main__':
    main()
