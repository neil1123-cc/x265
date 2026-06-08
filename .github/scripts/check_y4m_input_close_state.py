#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/input/y4m.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(ifs) || std::fclose(ifs)',
)
REQUIRED_SNIPPETS = (
    'if (ifs && ifs != stdin)',
    'bool closeFailed = std::ferror(ifs) != 0;',
    'if (std::fclose(ifs))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to close input file after open failure\\n");',
    'x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to finalize input file state\\n");',
    'Y4MInput::~Y4MInput()',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden y4m input short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing y4m input close guardrail: {snippet}'))
    if text.count('if (ifs && ifs != stdin)') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected y4m input close guards to skip stdin in both constructor-failure and destructor paths'))
    if text.count('bool closeFailed = std::ferror(ifs) != 0;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded y4m input close paths'))
    if text.count('if (std::fclose(ifs))') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded y4m input fclose calls'))

    open_close = text.find('bool closeFailed = std::ferror(ifs) != 0;')
    open_warning = text.find('x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to close input file after open failure\\n");')
    null_reset = text.find('ifs = nullptr;', open_warning)
    destructor = text.find('Y4MInput::~Y4MInput()')
    final_close = text.find('bool closeFailed = std::ferror(ifs) != 0;', open_close + 1)
    final_warning = text.find('x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to finalize input file state\\n");')
    if -1 not in (open_close, open_warning, null_reset, destructor, final_close, final_warning):
        if not (open_close < open_warning < null_reset < destructor < final_close < final_warning):
            failures.append((TARGET.as_posix(), 0, 'y4m input close guards must preserve constructor-failure cleanup before destructor finalization'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Y4M input close state')
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

    print('Y4M input close guard validated')


if __name__ == '__main__':
    main()
