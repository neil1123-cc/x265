#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/x265.cpp'),
    Path('source/x265cli.cpp'),
    Path('source/encoder/encoder.cpp'),
    Path('source/encoder/ratecontrol.cpp'),
    Path('source/input/lavf.cpp'),
    Path('source/common/threadpool.cpp'),
    Path('source/dynamicHDR10/json11/json11.cpp'),
)
REQUIRED_SNIPPETS = {
    'source/x265.cpp': (
        'static bool parseAbrIntValue(const char* token, int& value)',
        'int parsedValue = x265_atoi(token, bError);',
        'if (bError || parsedValue < 0)',
        'bError = !parseAbrIntValue(head[1], loadLevel);',
        'stagedCliopt[i].loadLevel = loadLevel;',
    ),
    'source/x265cli.cpp': (
        'static bool parseCliInt32Token(const char* token, int32_t& value)',
        'int parsedValue = x265_atoi(token, bError);',
        'static bool parseCliIntOptarg(const char* optarg, int& value)',
        'int parsedValue = x265_atoi(optarg, bError);',
        'if (bError || parsedValue < 0)',
        'if (!parseCliInt32Token(frameToken, parsedNum))',
        'if (!parseCliInt32Token(qpToken, parsedQp))',
        'num = parsedNum;',
        'qp = parsedQp;',
        'bool bOutputBitDepthError = !parseCliIntOptarg(optarg, parsedOutputBitDepth)',
        '!isRecognizedOutputBitDepth(parsedOutputBitDepth);',
        'if (!parseCliIntOptarg(optarg, parsedSeek))',
        'this->seek = (uint32_t)parsedSeek;',
        'if (!parseCliIntOptarg(optarg, parsedFramesToBeEncoded))',
        'this->framesToBeEncoded = (uint32_t)parsedFramesToBeEncoded;',
        'if (!parseCliIntOptarg(optarg, parsedInputBitDepth))',
        'inputBitDepth = (uint32_t)parsedInputBitDepth;',
        'if (!parseCliIntOptarg(optarg, parsedReconFileBitDepth))',
        'reconFileBitDepth = (uint32_t)parsedReconFileBitDepth;',
        'int32_t startFrame = 0;',
        'if (!parseCliInt32Token(argLine, startFrame))',
        'stagedParam.rc.zones[i].startFrame = startFrame;',
        'bool bNumViewsError = !parseCliIntOptarg(optarg, numViews);',
        'stagedNumViews = numViews;',
        'bool bFormatError = !parseCliIntOptarg(optarg, format);',
        'stagedFormat = format;',
    ),
    'source/encoder/encoder.cpp': (
        'bool parseUserSeiIntToken(const char* token, int& value)',
        'int parsedValue = x265_atoi(token, bError);',
        'if (bError || parsedValue < 0)',
        'if (!parseUserSeiIntToken(fields.pocToken, poc) ||',
        '!parseUserSeiIntToken(fields.nalTypeToken, nalType) ||',
        '!parseUserSeiIntToken(fields.payloadTypeToken, payloadType))',
    ),
    'source/encoder/ratecontrol.cpp': (
        'static bool parseRateControlIntToken(const char* token, int& value)',
        'int parsedValue = x265_atoi(token, bError);',
        'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
        'rce->rpsData.deltaPOC[idx] = deltaPOC;',
        'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
        'rce->rpsData.bUsed[idx] = bUsed > 0;',
    ),
    'source/input/lavf.cpp': (
        'static bool parseLavfIntValue(const char* value, int& parsedValue)',
        'int valueAsInt = x265_atoi(value, bError);',
        'if (!parseLavfIntValue(entry->value, frameCount))',
        'info.frameCount = frameCount;',
    ),
    'source/common/threadpool.cpp': (
        'static bool parseThreadPoolCountToken(const char* token, int& value)',
        'int parsedValue = X265_NS::x265_atoi(token, bError);',
        'if (bError || parsedValue < 0)',
        'if (!parseThreadPoolCountToken(nodeStr, count))',
    ),
}


def find_atoi_tokens(text):
    line = 1
    index = 0
    length = len(text)
    in_line_comment = False
    in_block_comment = False
    in_single_quote = False
    in_double_quote = False
    escaped = False

    while index < length:
        char = text[index]
        nxt = text[index + 1] if index + 1 < length else ''

        if char == '\n':
            line += 1
            in_line_comment = False
            escaped = False
            index += 1
            continue

        if in_line_comment:
            index += 1
            continue

        if in_block_comment:
            if char == '*' and nxt == '/':
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if in_single_quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == "'":
                in_single_quote = False
            index += 1
            continue

        if in_double_quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_double_quote = False
            index += 1
            continue

        if char == '/' and nxt == '/':
            in_line_comment = True
            index += 2
            continue

        if char == '/' and nxt == '*':
            in_block_comment = True
            index += 2
            continue

        if char == "'":
            in_single_quote = True
            index += 1
            continue

        if char == '"':
            in_double_quote = True
            index += 1
            continue

        if text.startswith('std::atoi(', index):
            before = text[index - 1] if index > 0 else ''
            if not before or not (before.isalnum() or before == '_'):
                yield line
            index += 10
            continue

        if text.startswith('atoi(', index):
            before = text[index - 1] if index > 0 else ''
            if not before or not (before.isalnum() or before == '_'):
                yield line
            index += 5
            continue

        index += 1


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for relative_path in TARGETS:
        path = repo_root / relative_path
        if not path.is_file():
            failures.append((relative_path.as_posix(), 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        for line in find_atoi_tokens(text):
            failures.append((relative_path.as_posix(), line, 'avoid bare atoi in reviewed parsing paths'))
        for snippet in REQUIRED_SNIPPETS.get(relative_path.as_posix(), ()):
            if snippet not in text:
                failures.append((relative_path.as_posix(), 0, f'missing external input atoi guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check key external-input parsing paths for atoi regressions')
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

    print('External input atoi usage validated')


if __name__ == '__main__':
    main()
