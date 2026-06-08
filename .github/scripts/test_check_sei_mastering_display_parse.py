#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_sei_mastering_display_parse.py')

# Coverage probes used by the scan for mastering-display parse guardrails.
NORMALIZED_PROBES = (
    'forbidden mastering-display parse regression: ',
    'missing mastering-display parse guardrail: ',
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
                'source/encoder/sei.h': '\n'.join((
                    'static bool parseSeiUnsignedToken(const char*& cursor, uint32_t& value)',
                    'static bool consumeSeiLiteral(const char*& cursor, const char* literal)',
                    'class SEIMasteringDisplayColorVolume : public SEI',
                    'bool parse(const char* value)',
                    'const char* cursor = value;',
                    'uint32_t values[10];',
                    'if (!consumeSeiLiteral(cursor, "G(") ||',
                    '!consumeSeiLiteral(cursor, ")L(") ||',
                    '!parseSeiUnsignedToken(cursor, values[9]) ||',
                    "!consumeSeiLiteral(cursor, \")\") ||",
                    "*cursor != '\\0')",
                    'for (int i = 0; i < 3; i++)',
                    'if (values[i * 2] > UINT16_MAX || values[i * 2 + 1] > UINT16_MAX)',
                    'displayPrimaryX[i] = (uint16_t)values[i * 2];',
                    'displayPrimaryY[i] = (uint16_t)values[i * 2 + 1];',
                    'if (values[6] > UINT16_MAX || values[7] > UINT16_MAX)',
                    'whitePointX = (uint16_t)values[6];',
                    'whitePointY = (uint16_t)values[7];',
                    'maxDisplayMasteringLuminance = values[8];',
                    'minDisplayMasteringLuminance = values[9];',
                    'return true;',
                    'class SEIContentLightLevel : public SEI',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/sei.h': 'return std::sscanf(value, "G(%hu,%hu)B(%hu,%hu)R(%hu,%hu)WP(%hu,%hu)L(%u,%u)%n",\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden mastering-display parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/sei.h': '\n'.join((
                    'static bool parseSeiUnsignedToken(const char*& cursor, uint32_t& value)',
                    'static bool consumeSeiLiteral(const char*& cursor, const char* literal)',
                    'class SEIMasteringDisplayColorVolume : public SEI',
                    'bool parse(const char* value)',
                    'const char* cursor = value;',
                    'uint32_t values[10];',
                    'if (!consumeSeiLiteral(cursor, "G(") ||',
                    '!consumeSeiLiteral(cursor, ")L(") ||',
                    '!parseSeiUnsignedToken(cursor, values[9]) ||',
                    "!consumeSeiLiteral(cursor, \")\") ||",
                    "*cursor != '\\0')",
                    'for (int i = 0; i < 3; i++)',
                    'if (values[i * 2] > UINT16_MAX || values[i * 2 + 1] > UINT16_MAX)',
                    'displayPrimaryX[i] = (uint16_t)values[i * 2];',
                    'displayPrimaryY[i] = (uint16_t)values[i * 2 + 1];',
                    'whitePointX = (uint16_t)values[6];',
                    'whitePointY = (uint16_t)values[7];',
                    'if (values[6] > UINT16_MAX || values[7] > UINT16_MAX)',
                    'maxDisplayMasteringLuminance = values[8];',
                    'minDisplayMasteringLuminance = values[9];',
                    'return true;',
                    'class SEIContentLightLevel : public SEI',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SEIMasteringDisplayColorVolume::parse must fully consume and validate the mastering-display token stream before publishing white-point and luminance values')

    print('Mastering-display parse guard tests passed')


if __name__ == '__main__':
    main()
