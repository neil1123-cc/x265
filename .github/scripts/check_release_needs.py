#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

REQUIRED_RELEASE_NEEDS = {
    'build.yml': ('cxx20-warning-scan', 'cxx20-gcc-compile-commands', 'build'),
    'build-profiling.yml': ('build',),
}
DEFAULT_WORKFLOWS = (
    Path('.github/workflows/build.yml'),
    Path('.github/workflows/build-profiling.yml'),
    Path('.github/workflows/build-pgo.yml'),
)


def parse_publish_release_needs(path):
    text = Path(path).read_text()
    match = re.search(r'(?m)^  publish-release:\n(?P<body>(?:^    .*\n|^\s*$)+)', text)
    if not match:
        return None
    body = match.group('body')
    needs_match = re.search(r'(?m)^    needs:\n(?P<needs>(?:^      - .+\n)+)', body)
    if needs_match:
        return [line.strip()[2:].strip() for line in needs_match.group('needs').splitlines()]
    scalar_match = re.search(r'(?m)^    needs:\s*([^\n]+)', body)
    if scalar_match:
        return [item.strip() for item in scalar_match.group(1).strip('[]').split(',') if item.strip()]
    return []


def main():
    parser = argparse.ArgumentParser(description='Check release jobs depend on required guardrail jobs')
    parser.add_argument('workflow', nargs='*', type=Path, default=DEFAULT_WORKFLOWS)
    args = parser.parse_args()

    for workflow in args.workflow:
        required = REQUIRED_RELEASE_NEEDS.get(workflow.name)
        actual = parse_publish_release_needs(workflow)
        if actual is None:
            if required is not None:
                raise SystemExit(f'publish-release job not found: {workflow}')
            print(f'{workflow}: no publish-release job')
            continue
        if required is None:
            raise SystemExit(f'{workflow}: publish-release has no required needs policy')
        missing = [need for need in required if need not in actual]
        if missing:
            raise SystemExit(f'{workflow}: publish-release missing needs: {", ".join(missing)}')
        print(f'{workflow}: publish-release needs validated: {", ".join(actual)}')


if __name__ == '__main__':
    main()
