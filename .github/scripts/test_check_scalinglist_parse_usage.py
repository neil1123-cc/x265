#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scalinglist_parse_usage.py')

# Coverage probes used by the scan for scaling-list parse guardrails.
NORMALIZED_PROBES = (
    'forbidden scaling-list parse regression: ',
    'missing scaling-list parse guardrail: ',
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
                'source/common/scalinglist.cpp': '\n'.join((
                    'static bool parseScalingListIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'if (bError || parsedValue <= 0)',
                    'value = parsedValue;',
                    'static bool readScalingListValue(FILE* fp, int& data)',
                    'char token[32];',
                    'if (std::fscanf(fp, " %31[^,\\r\\n],", token) != 1)',
                    'return parseScalingListIntToken(token, data);',
                    'namespace X265_NS {',
                    'for (int i = 0; i < size; i++)',
                    'int data;',
                    'if (!readScalingListValue(fp, data))',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
                    'src[i] = data;',
                    'm_scalingListDC[sizeIdc][listIdc] = src[0];',
                    'int data;',
                    'if (!readScalingListValue(fp, data))',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
                    'scalingListDC[sizeIdc][listIdc] = data;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/scalinglist.cpp': 'data = x265_atoi(token, bError);\n'})
        expect_fail(run_checker(root), 'forbidden scaling-list parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': '\n'.join((
                    'static bool parseScalingListIntToken(const char* token, int& value)',
                    'static bool readScalingListValue(FILE* fp, int& data)',
                    'if (std::fscanf(fp, " %31[^,\\r\\n],", token) != 1)',
                    'return parseScalingListIntToken(token, data);',
                    'if (!readScalingListValue(fp, data))',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing scaling-list parse guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': '\n'.join((
                    'static bool parseScalingListIntToken(const char* token, int& value)',
                    'value = parsedValue;',
                    'int parsedValue = x265_atoi(token, bError);',
                    'if (bError || parsedValue <= 0)',
                    'static bool readScalingListValue(FILE* fp, int& data)',
                    'char token[32];',
                    'return parseScalingListIntToken(token, data);',
                    'if (std::fscanf(fp, " %31[^,\\r\\n],", token) != 1)',
                    'namespace X265_NS {',
                    'for (int i = 0; i < size; i++)',
                    'int data;',
                    'src[i] = data;',
                    'if (!readScalingListValue(fp, data))',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
                    'm_scalingListDC[sizeIdc][listIdc] = src[0];',
                    'int data;',
                    'if (!readScalingListValue(fp, data))',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
                    'scalingListDC[sizeIdc][listIdc] = data;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Scaling-list helpers must preserve the reviewed token-parse flow before publishing parsed values')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': '\n'.join((
                    'static bool parseScalingListIntToken(const char* token, int& value)',
                    'int parsedValue = x265_atoi(token, bError);',
                    'if (bError || parsedValue <= 0)',
                    'value = parsedValue;',
                    'static bool readScalingListValue(FILE* fp, int& data)',
                    'char token[32];',
                    'if (std::fscanf(fp, " %31[^,\\r\\n],", token) != 1)',
                    'return parseScalingListIntToken(token, data);',
                    'namespace X265_NS {',
                    'for (int i = 0; i < size; i++)',
                    'int data;',
                    'src[i] = data;',
                    'if (!readScalingListValue(fp, data))',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
                    'm_scalingListDC[sizeIdc][listIdc] = src[0];',
                    'int data;',
                    'if (!readScalingListValue(fp, data))',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
                    'scalingListDC[sizeIdc][listIdc] = data;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Scaling-list parsing must preserve the reviewed matrix and DC read/close ordering around readScalingListValue failures')

    print('Scaling-list parse guard tests passed')


if __name__ == '__main__':
    main()
