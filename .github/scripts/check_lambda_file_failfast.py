#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'value = x265_atof(tok, bValueError);',
    'if (!bValueError)',
    'x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
    'bool closeFailed = ferror(lfn) != 0;',
    'if (fclose(lfn))',
    'closeFailed = true;',
    'return true;',
)
FORBIDDEN_SNIPPETS = (
    'if (tok)\n                {\n                    bool bValueError = false;\n                    value = x265_atof(tok, bValueError);\n                    if (!bValueError)\n                        break;\n                }\n            }\n            while (1);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing lambda fail-fast guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden lambda fail-fast regression: {snippet[:80]}...'))

    parse_pos = text.find('value = x265_atof(tok, bValueError);')
    success_pos = text.find('if (!bValueError)', parse_pos)
    error_pos = text.find('x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);', parse_pos)
    return_pos = text.find('return true;', error_pos)
    if -1 not in (parse_pos, success_pos, error_pos, return_pos) and not (parse_pos < success_pos < error_pos < return_pos):
        failures.append((TARGET.as_posix(), 0, 'parseLambdaFile must fail fast on invalid lambda tokens'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check lambda-file invalid-token fail-fast guardrail')
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

    print('Lambda-file fail-fast validated')


if __name__ == '__main__':
    main()
