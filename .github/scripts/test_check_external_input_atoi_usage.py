#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_external_input_atoi_usage.py')

# Coverage probes used by the scan for external-input atoi guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing external input atoi guardrail: ',
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
                'source/x265.cpp': 'static bool parseAbrIntValue(const char* token, int& value)\nbool bError = false;\nint parsedValue = x265_atoi(token, bError);\nif (bError || parsedValue < 0)\nbError = !parseAbrIntValue(head[1], loadLevel);\nstagedCliopt[i].loadLevel = loadLevel;\n',
                'source/x265cli.cpp': '\n'.join((
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
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'bool parseUserSeiIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'if (bError || parsedValue < 0)',
                    'if (!parseUserSeiIntToken(fields.pocToken, poc) ||',
                    '!parseUserSeiIntToken(fields.nalTypeToken, nalType) ||',
                    '!parseUserSeiIntToken(fields.payloadTypeToken, payloadType))',
                )) + '\n',
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'static bool parseRateControlIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'int deltaPOC = 0;',
                    'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
                    'rce->rpsData.deltaPOC[idx] = deltaPOC;',
                    'int bUsed = 0;',
                    'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
                    'rce->rpsData.bUsed[idx] = bUsed > 0;',
                )) + '\n',
                'source/input/lavf.cpp': 'static bool parseLavfIntValue(const char* value, int& parsedValue)\nint valueAsInt = x265_atoi(value, bError);\nif (!parseLavfIntValue(entry->value, frameCount))\ninfo.frameCount = frameCount;\n',
                'source/common/threadpool.cpp': 'static bool parseThreadPoolCountToken(const char* token, int& value)\nint parsedValue = X265_NS::x265_atoi(token, bError);\nif (bError || parsedValue < 0)\nif (!parseThreadPoolCountToken(nodeStr, count))\n',
                'source/dynamicHDR10/json11/json11.cpp': 'int x = (int)strtol(value, 0, 10);\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'int x = std::atoi(value);\n',
                'source/x265cli.cpp': 'int ok = 0;\n',
                'source/encoder/encoder.cpp': 'int ok = 0;\n',
                'source/encoder/ratecontrol.cpp': 'int ok = 0;\n',
                'source/input/lavf.cpp': 'int ok = 0;\n',
                'source/common/threadpool.cpp': 'int ok = 0;\n',
                'source/dynamicHDR10/json11/json11.cpp': 'int ok = 0;\n',
            },
        )
        expect_fail(run_checker(root), 'avoid bare atoi in reviewed parsing paths')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'bool bError = false; int x = x265_atoi(value, bError);\n',
                'source/x265cli.cpp': 'int ok = 0;\n',
                'source/encoder/encoder.cpp': 'int ok = 0;\n',
                'source/encoder/ratecontrol.cpp': 'int ok = 0;\n',
                'source/input/lavf.cpp': 'int ok = 0;\n',
                'source/common/threadpool.cpp': 'int ok = 0;\n',
                'source/dynamicHDR10/json11/json11.cpp': 'int ok = 0;\n',
            },
        )
        expect_fail(run_checker(root), 'missing external input atoi guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'static bool parseAbrIntValue(const char* token, int& value)\nbool bError = false;\nint parsedValue = x265_atoi(token, bError);\nif (bError || parsedValue < 0)\nbError = !parseAbrIntValue(head[1], loadLevel);\nstagedCliopt[i].loadLevel = loadLevel;\n',
                'source/x265cli.cpp': '\n'.join((
                    'static bool parseCliInt32Token(const char* token, int32_t& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'static bool parseCliIntOptarg(const char* optarg, int& value)',
                    'int parsedValue = x265_atoi(optarg, bError);',
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
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'bool parseUserSeiIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'if (bError || parsedValue < 0)',
                    'if (!parseUserSeiIntToken(fields.pocToken, poc) ||',
                    '!parseUserSeiIntToken(fields.nalTypeToken, nalType) ||',
                    '!parseUserSeiIntToken(fields.payloadTypeToken, payloadType))',
                )) + '\n',
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'static bool parseRateControlIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'int deltaPOC = 0;',
                    'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
                    'rce->rpsData.deltaPOC[idx] = deltaPOC;',
                    'int bUsed = 0;',
                    'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
                    'rce->rpsData.bUsed[idx] = bUsed > 0;',
                )) + '\n',
                'source/input/lavf.cpp': 'static bool parseLavfIntValue(const char* value, int& parsedValue)\nint valueAsInt = x265_atoi(value, bError);\nif (!parseLavfIntValue(entry->value, frameCount))\ninfo.frameCount = frameCount;\n',
                'source/common/threadpool.cpp': 'static bool parseThreadPoolCountToken(const char* token, int& value)\nint parsedValue = X265_NS::x265_atoi(token, bError);\nif (bError || parsedValue < 0)\nif (!parseThreadPoolCountToken(nodeStr, count))\n',
                'source/dynamicHDR10/json11/json11.cpp': 'int x = (int)strtol(value, 0, 10);\n',
            },
        )
        expect_fail(run_checker(root), 'missing external input atoi guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'static bool parseAbrIntValue(const char* token, int& value)\nint parsedValue = x265_atoi(token, bError);\nbool bError = false;\nbError = !parseAbrIntValue(head[1], loadLevel);\nstagedCliopt[i].loadLevel = loadLevel;\n',
                'source/x265cli.cpp': '\n'.join((
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
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'bool parseUserSeiIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'if (!parseUserSeiIntToken(fields.pocToken, poc) ||',
                    '!parseUserSeiIntToken(fields.nalTypeToken, nalType) ||',
                    '!parseUserSeiIntToken(fields.payloadTypeToken, payloadType))',
                )) + '\n',
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'static bool parseRateControlIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'int deltaPOC = 0;',
                    'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
                    'rce->rpsData.deltaPOC[idx] = deltaPOC;',
                    'int bUsed = 0;',
                    'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
                    'rce->rpsData.bUsed[idx] = bUsed > 0;',
                )) + '\n',
                'source/input/lavf.cpp': 'static bool parseLavfIntValue(const char* value, int& parsedValue)\nint valueAsInt = x265_atoi(value, bError);\nif (!parseLavfIntValue(entry->value, frameCount))\ninfo.frameCount = frameCount;\n',
                'source/common/threadpool.cpp': 'static bool parseThreadPoolCountToken(const char* token, int& value)\nint parsedValue = X265_NS::x265_atoi(token, bError);\nif (!parseThreadPoolCountToken(nodeStr, count))\n',
                'source/dynamicHDR10/json11/json11.cpp': 'int x = (int)strtol(value, 0, 10);\n',
            },
        )
        expect_fail(run_checker(root), 'missing external input atoi guardrail')

    print('External input atoi tests passed')


if __name__ == '__main__':
    main()
