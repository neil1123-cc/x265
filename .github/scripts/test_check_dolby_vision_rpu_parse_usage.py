#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_dolby_vision_rpu_parse_usage.py')

# Coverage probes used by the scan for Dolby Vision RPU parse guardrails.
NORMALIZED_PROBES = (
    'Dolby Vision RPU parsing must reset payload state and distinguish fread() failures from clean EOF/not-found handling',
    'forbidden Dolby Vision RPU parse regression: ',
    'missing Dolby Vision RPU parse guardrail: ',
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
                'source/x265cli.cpp': '\n'.join((
                    'int CLIOptions::rpuParser(x265_picture * pic)',
                    'if (!pic || !pic->rpu.payload)',
                    'uint8_t stagedPayload[1024];',
                    'int stagedPayloadSize = 0;',
                    'pic->rpu.payloadSize = 0;',
                    'while (bytesRead++ < 4 && fread(&byteVal, sizeof(uint8_t), 1, dolbyVisionRpu))',
                    'if (ferror(dolbyVisionRpu))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unable to read Dolby Vision RPU data for POC %d\\n", pic->pts);',
                    'if (code != START_CODE)',
                    'if (!stagedPayloadSize)',
                    'while (fread(&byteVal, sizeof(uint8_t), 1, dolbyVisionRpu))',
                    'if (ferror(dolbyVisionRpu))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unable to read Dolby Vision RPU data for POC %d\\n", pic->pts);',
                    'if (!bytesLeft && !stagedPayloadSize)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid Dolby Vision RPU startcode in POC %d\\n", pic->pts);',
                    'if (bytesRead >= 1024)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid Dolby Vision RPU size in POC %d\\n", pic->pts);',
                    'stagedPayload[stagedPayloadSize++] = (code >> (3 * 8)) & 0xFF;',
                    'std::memcpy(pic->rpu.payload, stagedPayload, stagedPayloadSize);',
                    'pic->rpu.payloadSize = stagedPayloadSize;',
                    'x265_log(nullptr, X265_LOG_WARNING, "Dolby Vision RPU not found for POC %d\\n", pic->pts);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'pic->rpu.payload[pic->rpu.payloadSize++] = byteVal;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden Dolby Vision RPU parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'int CLIOptions::rpuParser(x265_picture * pic)\n',
            },
        )
        expect_fail(run_checker(root), 'missing Dolby Vision RPU parse guardrail')

    print('Dolby Vision RPU parse guard tests passed')


if __name__ == '__main__':
    main()
