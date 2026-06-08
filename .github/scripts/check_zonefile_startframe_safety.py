#!/usr/bin/env python3
import argparse
from pathlib import Path


PARAM_TARGET = Path('source/common/param.cpp')
API_TARGET = Path('source/encoder/api.cpp')
PARAM_REQUIRED_SNIPPETS = (
    'OPT("radl")',
    'int radl = parseOptionIntValue(value, bRadlError);',
    'p->radl = radl;',
    'if (param->rc.zonefileCount && param->rc.zones)',
    'for (int i = 0; i < param->rc.zonefileCount; i++)',
    'CHECK(param->rc.zones[i].startFrame < 0,',
    '"Zonefile start frames must be non-negative");',
    'CHECK(param->rc.zones[i].zoneParam->radl < 0 || param->rc.zones[i].zoneParam->radl > param->rc.zones[i].zoneParam->bframes,',
    '"Zonefile radl must be between 0 and the configured bframes");',
    'CHECK(param->rc.zones[i].zoneParam->rc.bitrate < 0,',
    '"Zonefile bitrate must be non-negative");',
    'CHECK(param->rc.zones[i].zoneParam->rc.vbvMaxBitrate < 0,',
    '"Zonefile vbv-maxrate must be non-negative");',
    'if (!param->bResetZoneConfig)',
    'CHECK(param->rc.zones[i].startFrame % param->reconfigWindowSize != 0,',
    '"Zonefile start frames must align with the reconfig window size");',
    'if (i > 0)',
    'CHECK(param->rc.zones[i - 1].startFrame >= param->rc.zones[i].startFrame,',
    '"Zonefile start frames must be strictly increasing");',
    'if (param->bResetZoneConfig)',
    'int prevEffectiveStart = param->rc.zones[i - 1].startFrame;',
    'prevEffectiveStart += prevEffectiveStart ? param->rc.zones[i - 1].zoneParam->radl : 0;',
    'int effectiveStart = param->rc.zones[i].startFrame;',
    'effectiveStart += effectiveStart ? param->rc.zones[i].zoneParam->radl : 0;',
    'CHECK(prevEffectiveStart >= effectiveStart,',
    '"Zonefile effective start frames must be strictly increasing");',
)
API_REQUIRED_SNIPPETS = (
    'if (zone_in->startFrame < 0)',
    'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires a non-negative startFrame\\n");',
    'if (zone_in->zoneParam->rc.bitrate < 0)',
    'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires a non-negative bitrate\\n");',
    'if (zone_in->zoneParam->rc.vbvMaxBitrate < 0)',
    'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires a non-negative vbv-maxrate\\n");',
    'if (activeParam->reconfigWindowSize && (zone_in->startFrame % activeParam->reconfigWindowSize != 0))',
    'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires startFrame alignment with the reconfig window size\\n");',
    'uint64_t expectedStartFrame = (uint64_t)encoder->m_zoneIndex * activeParam->reconfigWindowSize;',
    'expectedStartFrame = (uint64_t)zone->startFrame +',
    '(uint64_t)activeParam->rc.zonefileCount * (uint64_t)activeParam->reconfigWindowSize;',
    'if (expectedStartFrame > INT_MAX)',
    'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration sequence exceeds supported startFrame range\\n");',
    'if ((uint64_t)zone_in->startFrame != expectedStartFrame)',
    'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires contiguous startFrame sequencing per reconfig window\\n");',
    'return -1;',
)
PARAM_FORBIDDEN_SNIPPETS = (
    'CHECK(param->rc.zones[i].startFrame <= 0,',
    'CHECK(param->rc.zones[i - 1].startFrame > param->rc.zones[i].startFrame,',
    'CHECK(param->rc.zones[i].startFrame % param->reconfigWindowSize == 0,',
    'CHECK(prevEffectiveStart > effectiveStart,',
)
PARAM_PARSE_REGION_START = 'OPT("radl")'
PARAM_PARSE_REGION_END = 'OPT("max-ausize-factor")'
PARAM_VALIDATION_REGION_START = 'if (param->rc.zonefileCount && param->rc.zones)'
PARAM_VALIDATION_REGION_END = 'CHECK(param->vui.aspectRatioIdc < 0'
API_REGION_START = 'if (zone_in->startFrame < 0)'
API_REGION_END = 'if (write && (read < write))'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    param_path = repo_root / PARAM_TARGET
    api_path = repo_root / API_TARGET
    if not param_path.is_file():
        return [(PARAM_TARGET.as_posix(), 0, 'missing file')]
    if not api_path.is_file():
        return [(API_TARGET.as_posix(), 0, 'missing file')]

    param_text = param_path.read_text(encoding='utf-8', errors='ignore')
    api_text = api_path.read_text(encoding='utf-8', errors='ignore')
    param_parse_region = get_region(param_text, PARAM_PARSE_REGION_START, PARAM_PARSE_REGION_END)
    param_validation_region = get_region(param_text, PARAM_VALIDATION_REGION_START, PARAM_VALIDATION_REGION_END)
    api_region = get_region(api_text, API_REGION_START, API_REGION_END)
    failures = []
    for snippet in PARAM_FORBIDDEN_SNIPPETS:
        if snippet in param_text:
            failures.append((PARAM_TARGET.as_posix(), 0, f'forbidden zonefile startFrame regression: {snippet}'))
            return failures
    for snippet in PARAM_REQUIRED_SNIPPETS:
        if snippet not in param_text:
            failures.append((PARAM_TARGET.as_posix(), 0, f'missing zonefile startFrame guardrail: {snippet}'))
    for snippet in API_REQUIRED_SNIPPETS:
        if snippet not in api_text:
            failures.append((API_TARGET.as_posix(), 0, f'missing zonefile startFrame guardrail: {snippet}'))
    if not has_in_order(
        param_parse_region,
        (
            'OPT("radl")',
            'int radl = parseOptionIntValue(value, bRadlError);',
            'p->radl = radl;',
        ),
    ):
        failures.append((PARAM_TARGET.as_posix(), 0, 'Zonefile radl parsing must preserve the reviewed staged parse-and-publish order'))
    if not has_in_order(
        param_validation_region,
        (
            'if (param->rc.zonefileCount && param->rc.zones)',
            'for (int i = 0; i < param->rc.zonefileCount; i++)',
            'CHECK(param->rc.zones[i].startFrame < 0,',
            'CHECK(param->rc.zones[i].zoneParam->radl < 0 || param->rc.zones[i].zoneParam->radl > param->rc.zones[i].zoneParam->bframes,',
            'CHECK(param->rc.zones[i].zoneParam->rc.bitrate < 0,',
            'CHECK(param->rc.zones[i].zoneParam->rc.vbvMaxBitrate < 0,',
            'if (!param->bResetZoneConfig)',
            'CHECK(param->rc.zones[i].startFrame % param->reconfigWindowSize != 0,',
            'if (i > 0)',
            'CHECK(param->rc.zones[i - 1].startFrame >= param->rc.zones[i].startFrame,',
            'if (param->bResetZoneConfig)',
            'int prevEffectiveStart = param->rc.zones[i - 1].startFrame;',
            'prevEffectiveStart += prevEffectiveStart ? param->rc.zones[i - 1].zoneParam->radl : 0;',
            'int effectiveStart = param->rc.zones[i].startFrame;',
            'effectiveStart += effectiveStart ? param->rc.zones[i].zoneParam->radl : 0;',
            'CHECK(prevEffectiveStart >= effectiveStart,',
        ),
    ):
        failures.append((PARAM_TARGET.as_posix(), 0, 'Zonefile startFrame validation must preserve the reviewed non-negative, alignment, ordering, and effective-start guard sequence'))
    if not has_in_order(
        api_region,
        (
            'if (zone_in->startFrame < 0)',
            'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires a non-negative startFrame\\n");',
            'if (zone_in->zoneParam->rc.bitrate < 0)',
            'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires a non-negative bitrate\\n");',
            'if (zone_in->zoneParam->rc.vbvMaxBitrate < 0)',
            'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires a non-negative vbv-maxrate\\n");',
            'if (activeParam->reconfigWindowSize && (zone_in->startFrame % activeParam->reconfigWindowSize != 0))',
            'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires startFrame alignment with the reconfig window size\\n");',
            'uint64_t expectedStartFrame = (uint64_t)encoder->m_zoneIndex * activeParam->reconfigWindowSize;',
            'expectedStartFrame = (uint64_t)zone->startFrame +',
            '(uint64_t)activeParam->rc.zonefileCount * (uint64_t)activeParam->reconfigWindowSize;',
            'if (expectedStartFrame > INT_MAX)',
            'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration sequence exceeds supported startFrame range\\n");',
            'if ((uint64_t)zone_in->startFrame != expectedStartFrame)',
            'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration requires contiguous startFrame sequencing per reconfig window\\n");',
        ),
    ):
        failures.append((API_TARGET.as_posix(), 0, 'Zone reconfiguration API checks must preserve the reviewed guard ordering before accepting a new zone startFrame'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check zonefile startFrame safety guardrails')
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

    print('Zonefile startFrame safety validated')


if __name__ == '__main__':
    main()
