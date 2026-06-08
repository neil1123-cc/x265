#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lavf_framecount_parse_safety.py')


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
                'source/input/lavf.cpp': '\n'.join((
                    'static bool parseLavfIntValue(const char* value, int& parsedValue)',
                    '{',
                    '    if (!value)',
                    '        return false;',
                    '    bool bError = false;',
                    '    int valueAsInt = x265_atoi(value, bError);',
                    '    if (bError || valueAsInt < 0)',
                    '        return false;',
                    '    parsedValue = valueAsInt;',
                    '    return true;',
                    '}',
                    'static enum AVPixelFormat convertPixelFormat',
                    'if (!s->nb_frames) {',
                    'const char* metadataValue = entry->value ? entry->value : "<null>";',
                    'if (!parseLavfIntValue(entry->value, frameCount))',
                    'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", metadataValue);',
                    'info.frameCount = 0;',
                    'info.frameCount = frameCount;',
                    '/* show video info */',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': '\n'.join((
                    'static bool parseLavfIntValue(const char* value, int& parsedValue)',
                    '{',
                    '    if (!value)',
                    '        return false;',
                    '    bool bError = false;',
                    '    int valueAsInt = x265_atoi(value, bError);',
                    '    if (bError)',
                    '        return false;',
                    '    parsedValue = valueAsInt;',
                    '    return true;',
                    '}',
                    'static enum AVPixelFormat convertPixelFormat',
                    'if (!s->nb_frames) {',
                    'const char* metadataValue = entry->value ? entry->value : "<null>";',
                    'if (!parseLavfIntValue(entry->value, frameCount))',
                    'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", metadataValue);',
                    'info.frameCount = frameCount;',
                    '/* show video info */',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden lavf framecount parse regression: if (bError)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': '\n'.join((
                    'static bool parseLavfIntValue(const char* value, int& parsedValue)',
                    '{',
                    '    bool bError = false;',
                    '    int valueAsInt = x265_atoi(value, bError);',
                    '    if (bError || valueAsInt < 0)',
                    '        return false;',
                    '    parsedValue = valueAsInt;',
                    '    return true;',
                    '}',
                    'static enum AVPixelFormat convertPixelFormat',
                    'if (!s->nb_frames) {',
                    'const char* metadataValue = entry->value ? entry->value : "<null>";',
                    'if (!parseLavfIntValue(entry->value, frameCount))',
                    'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", metadataValue);',
                    'info.frameCount = frameCount;',
                    '/* show video info */',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing lavf framecount parse guardrail: if (!value)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': '\n'.join((
                    'static bool parseLavfIntValue(const char* value, int& parsedValue)',
                    '{',
                    '    if (!value)',
                    '        return false;',
                    '    bool bError = false;',
                    '    int valueAsInt = x265_atoi(value, bError);',
                    '    if (bError || valueAsInt < 0)',
                    '        return false;',
                    '    parsedValue = valueAsInt;',
                    '    return true;',
                    '}',
                    'static enum AVPixelFormat convertPixelFormat',
                    'if (!s->nb_frames) {',
                    'if (!parseLavfIntValue(entry->value, frameCount))',
                    'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", entry->value);',
                    'info.frameCount = frameCount;',
                    '/* show video info */',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing lavf framecount parse guardrail: const char* metadataValue = entry->value ? entry->value : "<null>";')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': '\n'.join((
                    'static bool parseLavfIntValue(const char* value, int& parsedValue)',
                    '{',
                    '    bool bError = false;',
                    '    int valueAsInt = x265_atoi(value, bError);',
                    '    if (!value)',
                    '        return false;',
                    '    if (bError || valueAsInt < 0)',
                    '        return false;',
                    '    parsedValue = valueAsInt;',
                    '    return true;',
                    '}',
                    'static enum AVPixelFormat convertPixelFormat',
                    'if (!s->nb_frames) {',
                    'const char* metadataValue = entry->value ? entry->value : "<null>";',
                    'info.frameCount = frameCount;',
                    'if (!parseLavfIntValue(entry->value, frameCount))',
                    'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", metadataValue);',
                    'info.frameCount = 0;',
                    '/* show video info */',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'lavf framecount helper must preserve the reviewed null-check and non-negative parse flow before publishing parsedValue')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': '\n'.join((
                    'static bool parseLavfIntValue(const char* value, int& parsedValue)',
                    '{',
                    '    if (!value)',
                    '        return false;',
                    '    bool bError = false;',
                    '    int valueAsInt = x265_atoi(value, bError);',
                    '    if (bError || valueAsInt < 0)',
                    '        return false;',
                    '    parsedValue = valueAsInt;',
                    '    return true;',
                    '}',
                    'static enum AVPixelFormat convertPixelFormat',
                    'if (!s->nb_frames) {',
                    'const char* metadataValue = entry->value ? entry->value : "<null>";',
                    'info.frameCount = frameCount;',
                    'if (!parseLavfIntValue(entry->value, frameCount))',
                    'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", metadataValue);',
                    'info.frameCount = 0;',
                    '/* show video info */',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'lavf framecount metadata handling must preserve the reviewed parse/log/reset/success assignment ordering')

    print('Lavf framecount parse safety tests passed')


if __name__ == '__main__':
    main()
