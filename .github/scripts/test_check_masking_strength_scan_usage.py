#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_masking_strength_scan_usage.py')

# Coverage probes used by the scan for masking-strength scan guardrails.
NORMALIZED_PROBES = (
    'forbidden masking-strength scan regression: ',
    'missing masking-strength scan guardrail: ',
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
                'source/common/param.cpp': '\n'.join((
                    'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)',
                    'static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])',
                    'int parsedWindow[12];',
                    'double parsedRefQpDelta[12];',
                    'double parsedNonRefQpDelta[12];',
                    'const int expectedValues = expectedTriples * 3;',
                    'if (expectedTriples <= 0 || expectedTriples > 12)',
                    'return false;',
                    'if (splitCommaOption(value, parts, lengths, expectedValues) != expectedValues)',
                    'return false;',
                    'for (int i = 0; i < expectedTriples; i++)',
                    'bool bWindowError = false;',
                    'parsedWindow[i] = parseOptionIntToken(parts[i * 3], lengths[i * 3], bWindowError);',
                    'if (bWindowError ||',
                    '!parseOptionDoubleToken(parts[i * 3 + 1], lengths[i * 3 + 1], parsedRefQpDelta[i]) ||',
                    '!parseOptionDoubleToken(parts[i * 3 + 2], lengths[i * 3 + 2], parsedNonRefQpDelta[i]))',
                    'return false;',
                    'for (int i = 0; i < expectedTriples; i++)',
                    'window[i] = parsedWindow[i];',
                    'refQpDelta[i] = parsedRefQpDelta[i];',
                    'nonRefQpDelta[i] = parsedNonRefQpDelta[i];',
                    'return true;',
                    'static void applyCompactMaskingStrength',
                    'bool parseMaskingStrength(x265_param* p, const char* value)',
                    'if (p->bEnableSceneCutAwareQp == FORWARD)',
                    'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                    'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'else if (p->bEnableSceneCutAwareQp == BACKWARD)',
                    'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                    'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'else if (p->bEnableSceneCutAwareQp == BI_DIRECTIONAL)',
                    'int window2[12];',
                    'double refQpDelta2[12], nonRefQpDelta2[12];',
                    'if (parseMaskingStrengthTriples(value, 2, window2, refQpDelta2, nonRefQpDelta2))',
                    'applyCompactMaskingStrength(window2[0], refQpDelta2[0], nonRefQpDelta2[0],',
                    'applyCompactMaskingStrength(window2[1], refQpDelta2[1], nonRefQpDelta2[1],',
                    'else if (parseMaskingStrengthTriples(value, 12, window2, refQpDelta2, nonRefQpDelta2))',
                    'p->fwdMaxScenecutWindow = 0;',
                    'p->bwdMaxScenecutWindow = 0;',
                    'for (int i = 0; i < 6; i++)',
                    'p->fwdScenecutWindow[i] = window2[i];',
                    'p->fwdRefQpDelta[i] = refQpDelta2[i];',
                    'p->fwdNonRefQpDelta[i] = nonRefQpDelta2[i];',
                    'p->bwdScenecutWindow[i] = window2[i + 6];',
                    'p->bwdRefQpDelta[i] = refQpDelta2[i + 6];',
                    'p->bwdNonRefQpDelta[i] = nonRefQpDelta2[i + 6];',
                    'p->fwdMaxScenecutWindow += p->fwdScenecutWindow[i];',
                    'p->bwdMaxScenecutWindow += p->bwdScenecutWindow[i];',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'return bError;',
                    'void x265_copy_params',
                    'p->bwdScenecutWindow[i] = window2[i + 6];',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'if (3 == sscanf(value, "%d,%lf,%lf", &window1[0], &refQpDelta1[0], &nonRefQpDelta1[0]))\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden masking-strength scan regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)',
                    'static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])',
                    'const int expectedValues = expectedTriples * 3;',
                    'if (expectedTriples <= 0 || expectedTriples > 12)',
                    'return false;',
                    'if (splitCommaOption(value, parts, lengths, expectedValues) != expectedValues)',
                    'return false;',
                    'for (int i = 0; i < expectedTriples; i++)',
                    'bool bWindowError = false;',
                    'window[i] = parsedWindow[i];',
                    'refQpDelta[i] = parsedRefQpDelta[i];',
                    'nonRefQpDelta[i] = parsedNonRefQpDelta[i];',
                    'parsedWindow[i] = parseOptionIntToken(parts[i * 3], lengths[i * 3], bWindowError);',
                    'if (bWindowError ||',
                    '!parseOptionDoubleToken(parts[i * 3 + 1], lengths[i * 3 + 1], parsedRefQpDelta[i]) ||',
                    '!parseOptionDoubleToken(parts[i * 3 + 2], lengths[i * 3 + 2], parsedNonRefQpDelta[i]))',
                    'return false;',
                    'for (int i = 0; i < expectedTriples; i++)',
                    'int parsedWindow[12];',
                    'double parsedRefQpDelta[12];',
                    'double parsedNonRefQpDelta[12];',
                    'return true;',
                    'static void applyCompactMaskingStrength',
                    'bool parseMaskingStrength(x265_param* p, const char* value)',
                    'if (p->bEnableSceneCutAwareQp == FORWARD)',
                    'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                    'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'else if (p->bEnableSceneCutAwareQp == BACKWARD)',
                    'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                    'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'else if (p->bEnableSceneCutAwareQp == BI_DIRECTIONAL)',
                    'int window2[12];',
                    'double refQpDelta2[12], nonRefQpDelta2[12];',
                    'if (parseMaskingStrengthTriples(value, 2, window2, refQpDelta2, nonRefQpDelta2))',
                    'applyCompactMaskingStrength(window2[0], refQpDelta2[0], nonRefQpDelta2[0],',
                    'applyCompactMaskingStrength(window2[1], refQpDelta2[1], nonRefQpDelta2[1],',
                    'else if (parseMaskingStrengthTriples(value, 12, window2, refQpDelta2, nonRefQpDelta2))',
                    'p->fwdMaxScenecutWindow = 0;',
                    'p->bwdMaxScenecutWindow = 0;',
                    'for (int i = 0; i < 6; i++)',
                    'p->fwdScenecutWindow[i] = window2[i];',
                    'p->fwdRefQpDelta[i] = refQpDelta2[i];',
                    'p->fwdNonRefQpDelta[i] = nonRefQpDelta2[i];',
                    'p->bwdScenecutWindow[i] = window2[i + 6];',
                    'p->bwdRefQpDelta[i] = refQpDelta2[i + 6];',
                    'p->bwdNonRefQpDelta[i] = nonRefQpDelta2[i + 6];',
                    'p->fwdMaxScenecutWindow += p->fwdScenecutWindow[i];',
                    'p->bwdMaxScenecutWindow += p->bwdScenecutWindow[i];',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'return bError;',
                    'void x265_copy_params',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'parseMaskingStrengthTriples must finish staged token parsing before publishing any window or delta values')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)',
                    'static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])',
                    'int parsedWindow[12];',
                    'double parsedRefQpDelta[12];',
                    'double parsedNonRefQpDelta[12];',
                    'const int expectedValues = expectedTriples * 3;',
                    'if (expectedTriples <= 0 || expectedTriples > 12)',
                    'return false;',
                    'if (splitCommaOption(value, parts, lengths, expectedValues) != expectedValues)',
                    'return false;',
                    'for (int i = 0; i < expectedTriples; i++)',
                    'bool bWindowError = false;',
                    'parsedWindow[i] = parseOptionIntToken(parts[i * 3], lengths[i * 3], bWindowError);',
                    'if (bWindowError ||',
                    '!parseOptionDoubleToken(parts[i * 3 + 1], lengths[i * 3 + 1], parsedRefQpDelta[i]) ||',
                    '!parseOptionDoubleToken(parts[i * 3 + 2], lengths[i * 3 + 2], parsedNonRefQpDelta[i]))',
                    'return false;',
                    'for (int i = 0; i < expectedTriples; i++)',
                    'window[i] = parsedWindow[i];',
                    'refQpDelta[i] = parsedRefQpDelta[i];',
                    'nonRefQpDelta[i] = parsedNonRefQpDelta[i];',
                    'return true;',
                    'static void applyCompactMaskingStrength',
                    'bool parseMaskingStrength(x265_param* p, const char* value)',
                    'if (p->bEnableSceneCutAwareQp == FORWARD)',
                    'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                    'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'else if (p->bEnableSceneCutAwareQp == BACKWARD)',
                    'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                    'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                    'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'else if (p->bEnableSceneCutAwareQp == BI_DIRECTIONAL)',
                    'int window2[12];',
                    'double refQpDelta2[12], nonRefQpDelta2[12];',
                    'if (parseMaskingStrengthTriples(value, 2, window2, refQpDelta2, nonRefQpDelta2))',
                    'applyCompactMaskingStrength(window2[0], refQpDelta2[0], nonRefQpDelta2[0],',
                    'applyCompactMaskingStrength(window2[1], refQpDelta2[1], nonRefQpDelta2[1],',
                    'else if (parseMaskingStrengthTriples(value, 12, window2, refQpDelta2, nonRefQpDelta2))',
                    'p->fwdMaxScenecutWindow = 0;',
                    'p->bwdMaxScenecutWindow = 0;',
                    'for (int i = 0; i < 6; i++)',
                    'p->fwdScenecutWindow[i] = window2[i];',
                    'p->fwdRefQpDelta[i] = refQpDelta2[i];',
                    'p->fwdNonRefQpDelta[i] = nonRefQpDelta2[i];',
                    'p->bwdScenecutWindow[i] = window2[i + 6];',
                    'p->bwdRefQpDelta[i] = refQpDelta2[i + 6];',
                    'p->bwdNonRefQpDelta[i] = nonRefQpDelta2[i + 6];',
                    'p->fwdMaxScenecutWindow += p->fwdScenecutWindow[i];',
                    'p->bwdMaxScenecutWindow += p->bwdScenecutWindow[i];',
                    'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                    'bError = true;',
                    'return bError;',
                    'void x265_copy_params',
                    'p->bwdScenecutWindow[i] = window2[i + 6];',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'parseMaskingStrength must preserve the reviewed compact-before-expanded branch order and directional array publishing flow')

    print('Masking-strength scan guard tests passed')


if __name__ == '__main__':
    main()
