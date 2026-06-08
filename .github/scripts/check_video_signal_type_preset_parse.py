#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
FORBIDDEN_SNIPPETS = (
    'std::sscanf(p->videoSignalTypePreset, "%19[^:]:%19s", systemId, colorVolume);',
    'std::sscanf(p->videoSignalTypePreset, "%19[^:]:%19s", systemId, colorVolume)',
    'std::sscanf(p->videoSignalTypePreset, "%19[^:]:%19[^:]%n", systemId, colorVolume, &consumed);',
    'parsed = std::sscanf(p->videoSignalTypePreset, "%19[^:]%n", systemId, &consumed);',
)
HELPER_REQUIRED_SNIPPETS = (
    'static bool copyVideoSignalTypeToken(const char* start, size_t length, char (&out)[20])',
    'if (!start || !length || length >= sizeof(out))',
    'std::memcpy(out, start, length);',
    "out[length] = '\\0';",
    'static bool parseVideoSignalTypePresetTokens(const char* preset, char (&systemId)[20], char (&colorVolume)[20])',
    "const char* separator = std::strchr(preset, ':');",
    'return copyVideoSignalTypeToken(preset, std::strlen(preset), systemId);',
    'if (!systemIdLength || !colorVolumeLength)',
)
CALLER_REQUIRED_SNIPPETS = (
    'void Encoder::configureVideoSignalTypePreset(x265_param* p)',
    'char systemId[20] = {};',
    'char colorVolume[20] = {};',
    'if (!parseVideoSignalTypePresetTokens(p->videoSignalTypePreset, systemId, colorVolume))',
    'x265_log(nullptr, X265_LOG_ERROR, "Incorrect video-signal-type-preset, aborting\\n");',
    'm_aborted = true;',
    'return;',
    'uint32_t sysId = 0;',
    'while (std::strcmp(vstPresets[sysId].systemId, systemId))',
)
HELPER_REGION_START = 'static bool copyVideoSignalTypeToken(const char* start, size_t length, char (&out)[20])'
HELPER_REGION_END = 'using namespace X265_NS;'
CALLER_REGION_START = 'void Encoder::configureVideoSignalTypePreset(x265_param* p)'
CALLER_REGION_END = 'while (std::strcmp(vstPresets[sysId].systemId, systemId))'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    end += len(end_marker)
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
    helper_region = get_region(text, HELPER_REGION_START, HELPER_REGION_END)
    caller_region = get_region(text, CALLER_REGION_START, CALLER_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden video-signal-type-preset parse regression: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing video-signal-type-preset parse guardrail: {snippet}'))
    for snippet in CALLER_REQUIRED_SNIPPETS:
        if snippet not in caller_region:
            failures.append((TARGET.as_posix(), 0, f'missing video-signal-type-preset parse guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(
            helper_region,
            (
                'static bool copyVideoSignalTypeToken(const char* start, size_t length, char (&out)[20])',
                'if (!start || !length || length >= sizeof(out))',
                'std::memcpy(out, start, length);',
                "out[length] = '\\0';",
                'static bool parseVideoSignalTypePresetTokens(const char* preset, char (&systemId)[20], char (&colorVolume)[20])',
                "const char* separator = std::strchr(preset, ':');",
                'return copyVideoSignalTypeToken(preset, std::strlen(preset), systemId);',
                'if (!systemIdLength || !colorVolumeLength)',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'video-signal-type-preset parsing must copy bounded tokens before validating optional colon-separated components'))
    if all(snippet in caller_region for snippet in CALLER_REQUIRED_SNIPPETS):
        if not has_in_order(
            caller_region,
            CALLER_REQUIRED_SNIPPETS,
        ):
            failures.append((TARGET.as_posix(), 0, 'configureVideoSignalTypePreset must reject malformed preset tokens before initializing the preset lookup state'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check strict video-signal-type-preset parsing guardrails')
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

    print('Video signal type preset parsing validated')


if __name__ == '__main__':
    main()
