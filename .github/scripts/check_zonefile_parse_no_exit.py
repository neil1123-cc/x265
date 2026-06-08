#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
    'x265_zone_free(&stagedParam);',
    'cliopt.destroy();',
    'return false;',
)
FORBIDDEN_SNIPPETS = (
    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))\n                {\n                    x265_zone_free(&stagedParam);\n                    cliopt.destroy();\n                    if (cliopt.api)\n                        cliopt.api->param_free(cliopt.param);\n                    std::exit(1);\n                }',
    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))\n                {\n                    x265_zone_free(&stagedParam);\n                    cliopt.destroy();\n                    if (cliopt.api)\n                        cliopt.api->param_free(cliopt.param);\n                    return false;\n                }',
    'cliopt.api->param_free(cliopt.param);',
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
            failures.append((TARGET.as_posix(), 0, f'missing zonefile no-exit guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, 'forbidden zonefile no-exit regression: parseZoneFile must not terminate the process on zone parse failure'))

    parse_pos = text.find('if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))')
    free_pos = text.find('x265_zone_free(&stagedParam);', parse_pos)
    return_pos = text.find('return false;', parse_pos)
    if -1 not in (parse_pos, free_pos, return_pos) and not (parse_pos < free_pos < return_pos):
        failures.append((TARGET.as_posix(), 0, 'parseZoneFile must clean up and return false on zone parse failure'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check parseZoneFile no-exit guardrail')
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

    print('Zonefile no-exit guard validated')


if __name__ == '__main__':
    main()
