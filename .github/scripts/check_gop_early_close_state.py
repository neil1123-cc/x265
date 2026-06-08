#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/gop.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(opt_file) || std::fclose(opt_file)',
    'std::ferror(hdr_file) || std::fclose(hdr_file)',
    'std::ferror(data_file) || std::fclose(data_file)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(opt_file) != 0;',
    'if (std::fclose(opt_file))',
    'bool closeFailed = std::ferror(hdr_file) != 0;',
    'if (std::fclose(hdr_file))',
    'bool closeFailed = std::ferror(data_file) != 0;',
    'if (std::fclose(data_file))',
    'b_fail = true;',
)
OPT_REGION_START = 'FILE* opt_file = open_file_for_write(dir_prefix + filename_prefix + ".options", false);'
OPT_REGION_END = 'std::fprintf(opt_file, "b-frames %d\\n",           p_param->bframes);'
HDR_REGION_START = 'if (std::fprintf(gop_file, "#headers %s.headers\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))'
HDR_REGION_END = 'for(unsigned int i = 0; i < nalcount; i++)'
DATA_REGION_START = 'if (std::fprintf(gop_file, "%s\\n", data_filename.c_str()) < 0 || std::fflush(gop_file))'
DATA_REGION_END = 'else if (!data_file)'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    return text[start:end] if -1 not in (start, end) else text


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    opt_region = get_region(text, OPT_REGION_START, OPT_REGION_END)
    hdr_region = get_region(text, HDR_REGION_START, HDR_REGION_END)
    data_region = get_region(text, DATA_REGION_START, DATA_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden GOP early-close short-circuit regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing GOP early-close guardrail: {snippet}'))

    if not has_in_order(
        opt_region,
        (
            'b_fail = true;',
            'bool closeFailed = std::ferror(opt_file) != 0;',
            'if (std::fclose(opt_file))',
            'closeFailed = true;',
            'if (closeFailed)',
            'b_fail = true;',
            'return;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'GOP setup failure must finalize the options file before returning'))

    if not has_in_order(
        hdr_region,
        (
            'b_fail = true;',
            'bool closeFailed = std::ferror(hdr_file) != 0;',
            'if (std::fclose(hdr_file))',
            'closeFailed = true;',
            'if (closeFailed)',
            'b_fail = true;',
            'return -1;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'GOP header setup failure must finalize the header file before returning'))

    if not has_in_order(
        data_region,
        (
            'b_fail = true;',
            'bool closeFailed = std::ferror(data_file) != 0;',
            'if (std::fclose(data_file))',
            'closeFailed = true;',
            'if (closeFailed)',
            'b_fail = true;',
            'data_file = nullptr;',
            'return -1;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'GOP data setup failure must finalize and clear the data file before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP early close state')
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

    print('GOP early-close guard validated')


if __name__ == '__main__':
    main()
