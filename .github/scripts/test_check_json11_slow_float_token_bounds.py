#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_json11_slow_float_token_bounds.py')

# Coverage probes used by the scan for json11 slow-float guardrails.
NORMALIZED_PROBES = (
    'missing json11 slow-float guardrail: ',
    'forbidden json11 slow-float regression: ',
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
                'source/dynamicHDR10/json11/json11.cpp': '\n'.join((
                    'static inline double parse_token_bounded_json_double(const char* begin, const char* end) {',
                    '    string token(begin, end);',
                    '    char* parse_end = nullptr;',
                    '    double value = std::strtod(token.c_str(), &parse_end);',
                    '    return parse_end == token.c_str() + token.size() ? value : 0.0;',
                    '}',
                    'Json parse_number() {',
                    '    return parse_token_bounded_json_double(str.c_str() + start_pos, str.c_str() + i);',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/dynamicHDR10/json11/json11.cpp': '\n'.join((
                    'Json parse_number() {',
                    '    return std::strtod(str.c_str() + start_pos, nullptr);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden json11 slow-float regression')

    print('json11 slow float token bounds tests passed')


if __name__ == '__main__':
    main()
