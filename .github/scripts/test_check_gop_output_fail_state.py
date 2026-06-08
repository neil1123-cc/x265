#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_output_fail_state.py')

# Coverage probes used by the scan for GOP output fail-state guardrails.
NORMALIZED_PROBES = (
    'GOP output must reject writes after fail-state in both header and frame writers',
    'missing GOP output fail-state guardrail: ',
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
                'source/output/gop.cpp': '\n'.join((
                    'if (b_fail || !gop_file)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'if (std::fprintf(gop_file, "#headers %s.headers\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
                    '{',
                    '    b_fail = true;',
                    '    std::fclose(hdr_file);',
                    '    return -1;',
                    '}',
                    'if (b_fail || !gop_file)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'if (std::fprintf(gop_file, "%s\\n", data_filename.c_str()) < 0 || std::fflush(gop_file))',
                    '{',
                    '    b_fail = true;',
                    '    std::fclose(data_file);',
                    '    data_file = nullptr;',
                    '    return -1;',
                    '}',
                    'else if (!data_file)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/gop.cpp': 'if (std::fprintf(gop_file, "%s\\n", data_filename.c_str()) < 0)\n{\n    return -1;\n}\n'})
        expect_fail(run_checker(root), 'missing GOP output fail-state guardrail')

    print('GOP output fail-state guard tests passed')


if __name__ == '__main__':
    main()
