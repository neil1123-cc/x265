#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'bool bQpValueError = false;',
    'int qp = parseOptionIntValue(value, bQpValueError);',
    'bError |= bQpValueError;',
    'if (!bQpValueError)',
    'p->rc.qp = qp;',
    'p->rc.rateControlMode = X265_RC_CQP;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if text.count('p->rc.qp = x265_atoi(value, bError);\n        p->rc.rateControlMode = X265_RC_CQP;') != 0:
        failures.append((TARGET.as_posix(), 0, 'forbidden qp mode regression: invalid qp must not switch rate control mode'))
        return failures
    if text.count('bool bQpValueError = false;') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing qp mode guardrail in both param parsers'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing qp mode guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check qp mode parse safety guardrails')
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

    print('QP mode parse safety validated')


if __name__ == '__main__':
    main()
