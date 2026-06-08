#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
TOP_LEVEL_SNIPPET = 'x265_log(param, X265_LOG_WARNING, "extra unused command arguments given <%s>\\n", argv[optind]);'
NESTED_SNIPPET = 'x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if TOP_LEVEL_SNIPPET not in text:
        failures.append((TARGET.as_posix(), 0, f'missing scenecut trailing-arg diagnostic guardrail: {TOP_LEVEL_SNIPPET}'))
    if NESTED_SNIPPET not in text:
        failures.append((TARGET.as_posix(), 0, f'missing scenecut trailing-arg diagnostic guardrail: {NESTED_SNIPPET}'))

    parse_pos = text.find('bool CLIOptions::parse(int argc, char **argv)')
    top_level_pos = text.find(TOP_LEVEL_SNIPPET, parse_pos if parse_pos >= 0 else 0)
    nested_parse_pos = text.find('bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)')
    nested_pos = text.find(NESTED_SNIPPET, nested_parse_pos if nested_parse_pos >= 0 else 0)
    if -1 in (parse_pos, top_level_pos, nested_parse_pos, nested_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI and nested scenecut trailing-arg diagnostics must both be present'))
    elif not (parse_pos < top_level_pos < nested_parse_pos < nested_pos):
        failures.append((TARGET.as_posix(), 0, 'scenecut trailing-arg diagnostics must stay attached to the correct parser layer'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scenecut trailing-arg diagnostics stay on the correct parser layers')
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

    print('Scenecut trailing-arg diagnostics validated')


if __name__ == '__main__':
    main()
