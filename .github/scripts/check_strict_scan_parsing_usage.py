#!/usr/bin/env python3
import argparse
from pathlib import Path


CHECKS = (
    (
        Path('source/common/param.cpp'),
        (
            'sscanf(value, "%d:%d", &p->vui.sarWidth, &p->vui.sarHeight) != 2;',
            'sscanf(value, "%u/%u", &p->fpsNum, &p->fpsDenom) == 2',
            'sscanf(value, "%u/%u", &svtHevcParam->frameRateNumerator, &svtHevcParam->frameRateDenominator) == 2',
            'sscanf(value, "%dx%d", &p->sourceWidth, &p->sourceHeight) != 2',
            'sscanf(value, "%dx%d", &svtHevcParam->sourceWidth, &svtHevcParam->sourceHeight) != 2',
            'sscanf(value, "%hu,%hu", &p->maxCLL, &p->maxFALL) != 2',
            'sscanf(value, "%hu,%hu", &svtHevcParam->maxCLL, &svtHevcParam->maxFALL) != 2',
            'sscanf(value, "%d,%d,%d,%d",',
            'sscanf(c, "%d,%d,q=%d%n", &p->rc.zones[i].startFrame, &p->rc.zones[i].endFrame, &p->rc.zones[i].qp, &len)',
            'sscanf(c, "%d,%d,b=%f%n", &p->rc.zones[i].startFrame, &p->rc.zones[i].endFrame, &p->rc.zones[i].bitrateFactor, &len)',
            '2 == sscanf(value, "%d:%d", &p->deblockingFilterTCOffset, &p->deblockingFilterBetaOffset)',
            '2 == sscanf(value, "%d,%d", &p->deblockingFilterTCOffset, &p->deblockingFilterBetaOffset)',
            'sscanf(value, "%d", &p->deblockingFilterTCOffset)',
            '2 == sscanf(value, "%d:%d%n", &p->deblockingFilterTCOffset, &p->deblockingFilterBetaOffset, &consumed)',
            '2 == sscanf(value, "%d,%d%n", &p->deblockingFilterTCOffset, &p->deblockingFilterBetaOffset, &consumed)',
            'sscanf(value, "%d%n", &p->deblockingFilterTCOffset, &consumed)',
        ),
        (
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
        ),
    ),
    (
        Path('source/filters/zimgfilter.cpp'),
        (
            'std::sscanf(pValue, "%lf,%lf,%lf,%lf", &dLeft, &dTop, &dRight, &dBottom);',
            'std::sscanf(pValue, "%d,%d,%lf,%lf", &rWidth, &rHeight, &param1, &param2);',
            'std::sscanf(pValue, "%lf,%lf,%lf,%lf%n", &dLeft, &dTop, &dRight, &dBottom, &consumed);',
            'std::sscanf(pValue, "%d,%d,%lf,%lf%n", &rWidth, &rHeight, &param1, &param2, &consumed);',
            "while (p < end && p[0] != '(') p++;",
            "while (p < end && p[0] != ')') p++;",
        ),
        (
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
            'int parsedWidth = 0;',
            'int parsedHeight = 0;',
            'if (!((count == 2 || count == 4) &&',
            'parseZimgIntToken(parts[0], lengths[0], parsedWidth)',
            'parseZimgIntToken(parts[1], lengths[1], parsedHeight)',
            'parseZimgDoubleToken(parts[2], lengths[2], param1)',
            'rWidth = (uint32_t)parsedWidth;',
            'rHeight = (uint32_t)parsedHeight;',
        ),
    ),
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for relative_path, forbidden_snippets, required_snippets in CHECKS:
        path = repo_root / relative_path
        if not path.is_file():
            failures.append((relative_path.as_posix(), 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        for snippet in forbidden_snippets:
            if snippet in text:
                failures.append((relative_path.as_posix(), 0, f'forbidden strict-scan regression: {snippet}'))
        for snippet in required_snippets:
            if snippet not in text:
                failures.append((relative_path.as_posix(), 0, f'missing strict-scan guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed strict scan parsing guardrails')
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

    print('Strict scan parsing usage validated')


if __name__ == '__main__':
    main()
