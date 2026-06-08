#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'int i = strtol(preset, &end, 10);',
    'if (*end == 0 && i >= 0 && i < (int)(sizeof(x265_preset_names) / sizeof(*x265_preset_names) - 1))',
)
REQUIRED_SNIPPETS = (
    'static const char* parsePresetIndexName(const char* preset)',
    'int index = parseOptionIntToken(preset, std::strlen(preset), bPresetIndexError);',
    'if (!bPresetIndexError && index >= 0 && index < (int)(sizeof(x265_preset_names) / sizeof(*x265_preset_names) - 1))',
    'preset = parsePresetIndexName(preset);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden preset index parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing preset index parse guardrail: {snippet}'))
    if text.count('preset = parsePresetIndexName(preset);') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected preset index parse helper to be used in both preset entry points'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed preset index parsing guardrails in common/param.cpp')
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

    print('Preset index parse usage validated')


if __name__ == '__main__':
    main()
