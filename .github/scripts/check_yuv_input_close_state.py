#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/input/yuv.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(ifs) || std::fclose(ifs)',
)
REQUIRED_SNIPPETS = (
    'if (ifs && ifs != stdin)',
    'bool closeFailed = std::ferror(ifs) != 0;',
    'if (std::fclose(ifs))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to close input file after open failure\\n");',
    'x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to finalize input file state\\n");',
    'YUVInput::~YUVInput()',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden yuv input short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing yuv input close guardrail: {snippet}'))
    if text.count('if (ifs && ifs != stdin)') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected yuv input close guards to skip stdin in both constructor-failure and destructor paths'))
    if text.count('bool closeFailed = std::ferror(ifs) != 0;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded yuv input close paths'))
    if text.count('if (std::fclose(ifs))') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded yuv input fclose calls'))

    open_close = text.find('bool closeFailed = std::ferror(ifs) != 0;')
    open_warning = text.find('x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to close input file after open failure\\n");')
    null_reset = text.find('ifs = nullptr;', open_warning)
    destructor = text.find('YUVInput::~YUVInput()')
    final_close = text.find('bool closeFailed = std::ferror(ifs) != 0;', open_close + 1)
    final_warning = text.find('x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to finalize input file state\\n");')
    if -1 not in (open_close, open_warning, null_reset, destructor, final_close, final_warning):
        if not (open_close < open_warning < null_reset < destructor < final_close < final_warning):
            failures.append((TARGET.as_posix(), 0, 'yuv input close guards must preserve constructor-failure cleanup before destructor finalization'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check YUV input close state')
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

    print('YUV input close guard validated')


if __name__ == '__main__':
    main()
