#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zones_parse_safety.py')


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
                    'OPT("zones")',
                    'static const char* findTokenChar(const char* token, size_t length, char target)',
                    'static bool parseZoneOptionEntry(char* entry, char* entryEnd, x265_zone& zone)',
                    'if (splitCommaOption(entry, parts, lengths, 3) != 3)',
                    "const char* equals = findTokenChar(parts[2], lengths[2], '=');",
                    "if (parts[2][0] == 'q')",
                    "else if (parts[2][0] == 'b')",
                    'int qp = parseOptionIntToken(equals + 1, modeValueLength, bLocalError);',
                    'if (bLocalError || startFrame < 0 || endFrame <= startFrame)',
                    'if (bLocalError || qp < -6 * (X265_DEPTH - 8) || qp > QP_MAX_MAX)',
                    'if (!parseOptionDoubleToken(equals + 1, modeValueLength, bitrateFactor) || bitrateFactor <= 0.0)',
                    'zone.startFrame = startFrame;',
                    'zone.endFrame = endFrame;',
                    '{',
                    '    int zoneCount = 1;',
                    '    const char* c;',
                    '    for (c = value; *c; c++)',
                    '        zoneCount += (*c == \'/\');',
                    '    x265_zone* zones = X265_MALLOC(x265_zone, zoneCount);',
                    '    char* zoneText = nullptr;',
                    '    bool bZoneParseError = false;',
                    '    if (!zones)',
                    '        bZoneParseError = true;',
                    '    else',
                    '        zoneText = strdup(value);',
                    '    if (!bZoneParseError)',
                    '    {',
                    '        std::fill_n(zones, zoneCount, x265_zone());',
                    '        if (!parseZoneOptionEntry((char*)c, entryEnd, zones[i]))',
                    '            bZoneParseError = true;',
                    '    }',
                    '    free(zoneText);',
                    '    bError |= bZoneParseError;',
                    '    if (!bZoneParseError)',
                    '    {',
                    '        p->rc.zoneCount = zoneCount;',
                    '        p->rc.zones = zones;',
                    '    }',
                    '    else',
                    '        X265_FREE(zones);',
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
                'source/common/param.cpp': '\n'.join((
                    'OPT("zones")',
                    '{',
                        '    p->rc.zoneCount = 1;',
                    '    p->rc.zones = X265_MALLOC(x265_zone, p->rc.zoneCount);',
                    '    p->rc.zones[i].startFrame = x265_atoi(c, bZoneValueError);',
                    '    p->rc.zones[i].endFrame = x265_atoi(firstComma + 1, bZoneValueError);',
                    '    p->rc.zones[i].qp = x265_atoi(modeValue, bZoneValueError);',
                    '    p->rc.zones[i].bitrateFactor = x265_atof(modeValue, bZoneValueError);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden zones regression: invalid zones input must not partially mutate zone state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("zones")',
                    'static const char* findTokenChar(const char* token, size_t length, char target)',
                    'static bool parseZoneOptionEntry(char* entry, char* entryEnd, x265_zone& zone)',
                    'if (splitCommaOption(entry, parts, lengths, 3) != 3)',
                    "const char* equals = findTokenChar(parts[2], lengths[2], '=');",
                    "if (parts[2][0] == 'q')",
                    "else if (parts[2][0] == 'b')",
                    'int qp = parseOptionIntToken(equals + 1, modeValueLength, bLocalError);',
                    'if (bLocalError || qp < -6 * (X265_DEPTH - 8) || qp > QP_MAX_MAX)',
                    'if (!parseOptionDoubleToken(equals + 1, modeValueLength, bitrateFactor) || bitrateFactor <= 0.0)',
                    'zone.startFrame = startFrame;',
                    'zone.endFrame = endFrame;',
                    '{',
                    '    int zoneCount = 1;',
                    '    const char* c;',
                    '    for (c = value; *c; c++)',
                    '        zoneCount += (*c == \'/\');',
                    '    x265_zone* zones = X265_MALLOC(x265_zone, zoneCount);',
                    '    char* zoneText = nullptr;',
                    '    bool bZoneParseError = false;',
                    '    if (!zones)',
                    '        bZoneParseError = true;',
                    '    else',
                    '        zoneText = strdup(value);',
                    '    if (!bZoneParseError)',
                    '    {',
                    '        std::fill_n(zones, zoneCount, x265_zone());',
                    '        if (!parseZoneOptionEntry((char*)c, entryEnd, zones[i]))',
                    '            bZoneParseError = true;',
                    '    }',
                    '    free(zoneText);',
                    '    bError |= bZoneParseError;',
                    '    if (!bZoneParseError)',
                    '    {',
                    '        p->rc.zoneCount = zoneCount;',
                    '        p->rc.zones = zones;',
                    '    }',
                    '    else',
                    '        X265_FREE(zones);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing zones guardrail: if (bLocalError || startFrame < 0 || endFrame <= startFrame)')

    print('Zones parse safety tests passed')


if __name__ == '__main__':
    main()
