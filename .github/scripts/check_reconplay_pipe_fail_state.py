#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/reconplay.cpp')
REQUIRED_SNIPPETS = (
    'if (std::fprintf(outputPipe, "YUV4MPEG2 W%d H%d F%d:%d Ip C%s%s\\n", width, height, param.fpsNum, param.fpsDenom, csp, depth) < 0',
    '|| std::fflush(outputPipe) || std::ferror(outputPipe))',
    'bool closeFailed = std::ferror(outputPipe) != 0;',
    'if (pclose(outputPipe))',
    'outputPipe = nullptr;',
    'if (std::fprintf(outputPipe, "FRAME\\n") < 0 || std::fflush(outputPipe) || std::ferror(outputPipe))',
    'if (retCount <= 0 || std::ferror(outputPipe) || !pipeValid)',
    'pipeValid = false;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ReconPlay pipe fail-state guardrail: {snippet}'))

    if text.count('pipeValid = false;') < 2:
        failures.append((TARGET.as_posix(), 0, 'ReconPlay pipe failures must lock pipeValid false in both frame-header and payload paths'))
    if 'std::ferror(outputPipe) || pclose(outputPipe)' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden ReconPlay short-circuit pclose regression'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ReconPlay pipe fail state')
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

    print('ReconPlay pipe fail-state guard validated')


if __name__ == '__main__':
    main()
