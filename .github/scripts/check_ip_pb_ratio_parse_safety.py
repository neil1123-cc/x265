#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);',
    'OPT("pbratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.pbFactor);',
    'CHECK(param->rc.ipFactor <= 0,',
    '"ipratio must be greater than 0");',
    'CHECK(param->rc.pbFactor <= 0,',
    '"pbratio must be greater than 0");',
)
FORBIDDEN_SNIPPETS = (
    'OPT("ipratio") p->rc.ipFactor = atof(value);',
    'OPT("pbratio") p->rc.pbFactor = atof(value);',
)
PARSE_REGION_START = 'OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);'
PARSE_REGION_END = 'OPT("hevc-aq")'
VALIDATION_REGION_START = 'CHECK(param->rc.ipFactor <= 0,'
VALIDATION_REGION_END = 'CHECK(param->rc.aqBiasStrength < 0 || param->rc.aqBiasStrength > 3,'


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
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    parse_region = get_region(text, PARSE_REGION_START, PARSE_REGION_END)
    validation_region = get_region(text, VALIDATION_REGION_START, VALIDATION_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ip/pb ratio regression: {snippet}'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in parse_region and snippet not in validation_region:
            failures.append((TARGET.as_posix(), 0, f'missing ip/pb ratio guardrail: {snippet}'))
    if has_in_order(
        parse_region,
        (
            'OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);',
            'OPT("pbratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.pbFactor);',
        ),
    ) is False:
        failures.append((TARGET.as_posix(), 0, 'ipratio/pbratio parsing must preserve the reviewed ipratio-before-pbratio parse order'))
    if has_in_order(
        validation_region,
        (
            'CHECK(param->rc.ipFactor <= 0,',
            '"ipratio must be greater than 0");',
            'CHECK(param->rc.pbFactor <= 0,',
            '"pbratio must be greater than 0");',
        ),
    ) is False:
        failures.append((TARGET.as_posix(), 0, 'ipratio/pbratio validation must keep the reviewed ipratio-before-pbratio range checks'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ipratio/pbratio parse safety guardrails')
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

    print('IP/PB ratio parse safety validated')


if __name__ == '__main__':
    main()
