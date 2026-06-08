#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
BLOCK_REQUIRED_SNIPPETS = (
    'OPT("zones")',
    'int zoneCount = 1;',
    'x265_zone* zones = X265_MALLOC(x265_zone, zoneCount);',
    'char* zoneText = nullptr;',
    'bool bZoneParseError = false;',
    'zoneText = strdup(value);',
    'std::fill_n(zones, zoneCount, x265_zone());',
    'if (!parseZoneOptionEntry((char*)c, entryEnd, zones[i]))',
    'free(zoneText);',
    'bError |= bZoneParseError;',
    'p->rc.zoneCount = zoneCount;',
    'p->rc.zones = zones;',
    'X265_FREE(zones);',
)
HELPER_REQUIRED_SNIPPETS = (
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
)
FORBIDDEN_SNIPPETS = (
    'p->rc.zoneCount = 1;',
    'p->rc.zoneCount += (*c == \'/\');',
    'p->rc.zones = X265_MALLOC(x265_zone, p->rc.zoneCount);',
    'p->rc.zones[i].startFrame = x265_atoi(c, bZoneValueError);',
    'p->rc.zones[i].endFrame = x265_atoi(firstComma + 1, bZoneValueError);',
    'p->rc.zones[i].qp = x265_atoi(modeValue, bZoneValueError);',
    'p->rc.zones[i].bitrateFactor = x265_atof(modeValue, bZoneValueError);',
    'zones[i].startFrame = x265_atoi(c, bZoneValueError);',
    'zones[i].endFrame = x265_atoi(firstComma + 1, bZoneValueError);',
    'zones[i].qp = x265_atoi(modeValue, bZoneValueError);',
    'zones[i].bitrateFactor = x265_atof(modeValue, bZoneValueError);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    block_start = text.find('OPT("zones")')
    if block_start == -1:
        return [(TARGET.as_posix(), 0, 'missing zones option block')]
    block_end = text.find('OPT("input-res")', block_start)
    block_text = text[block_start:block_end if block_end != -1 else None]
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in block_text:
            failures.append((TARGET.as_posix(), 0, 'forbidden zones regression: invalid zones input must not partially mutate zone state'))
            return failures
    for snippet in BLOCK_REQUIRED_SNIPPETS:
        if snippet not in block_text:
            failures.append((TARGET.as_posix(), 0, f'missing zones guardrail: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing zones guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check zones parse safety guardrails')
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

    print('Zones parse safety validated')


if __name__ == '__main__':
    main()
