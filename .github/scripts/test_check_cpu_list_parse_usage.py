#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cpu_list_parse_usage.py')

# Coverage probes used by the scan for CPU list parse guardrails.
NORMALIZED_PROBES = (
    'forbidden CPU list parse regression: ',
    'missing CPU list parse guardrail: ',
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
                    'int parseCpuName(const char* value, bool& bError, bool bEnableavx512)',
                    'if (bError)',
                    'char *buf = strdup(value);',
                    'bError = 0;',
                    'cpu = 0;',
                    'for (char* scan = buf; scan && *scan; )',
                    "char* separator = std::strchr(scan, ',');",
                    "if (separator)\n                *separator = '\\0';",
                    'tok = scan;',
                    'scan = separator ? separator + 1 : nullptr;',
                    'if (!*tok)',
                    'cpu |= X265_NS::cpu_names[i].flags;',
                    'free(buf);',
                    'static const int fixedRatios[][2] =',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': 'for (init = buf; (tok = strtok_r(init, ",", &saveptr)); init = nullptr)\n'})
        expect_fail(run_checker(root), 'forbidden CPU list parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'int parseCpuName(const char* value, bool& bError, bool bEnableavx512)',
                    'if (bError)',
                    'char *buf = strdup(value);',
                    'bError = 0;',
                    'cpu = 0;',
                    'for (char* scan = buf; scan && *scan; )',
                    "char* separator = std::strchr(scan, ',');",
                    'tok = scan;',
                    'scan = separator ? separator + 1 : nullptr;',
                    "if (separator)\n                *separator = '\\0';",
                    'if (!*tok)',
                    'cpu |= X265_NS::cpu_names[i].flags;',
                    'free(buf);',
                    'static const int fixedRatios[][2] =',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'parseCpuName must split the CPU list with the reviewed comma scanner and reject empty tokens before accumulating CPU flags')

    print('CPU list parse guard tests passed')


if __name__ == '__main__':
    main()
