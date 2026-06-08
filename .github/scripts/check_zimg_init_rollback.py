#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/filters/zimgfilter.cpp')
GLOBAL_REQUIRED_SNIPPETS = (
    'void ZimgFilter::release()',
)
REQUIRED_SNIPPETS = (
    'if (!graph) // Init',
    'release();',
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\\n");',
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for resize buffer\\n");',
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane geometry\\n");',
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane frame size\\n");',
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\\n", fail_str);',
    'zimg_get_last_error(fail_str, sizeof(fail_str));',
    'err = zimg_filter_graph_get_tmp_size(graph, &tmp_size);',
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for temp buffer\\n");',
    'bFail = true;',
    'return;',
)
FORBIDDEN_SNIPPETS = (
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for resize buffer\\n");\n            bFail = true;\n            return;',
    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane frame size\\n");\n                bFail = true;\n                return;',
)
REGION_START = 'if (!graph) // Init'
REGION_END = 'zimg_image_buffer_const src_buf = {}'


def get_nth(text, snippet, n):
    pos = -1
    for _ in range(n):
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return -1
    return pos


def check_path(region, anchor, message, occurrence=1):
    pos = get_nth(region, anchor, occurrence)
    if pos == -1:
        return message
    release = region.find('release();', pos)
    fail = region.find('bFail = true;', pos)
    ret = region.find('return;', pos)
    if -1 in (release, fail, ret) or not (pos < release < fail < ret):
        return message
    return None


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in GLOBAL_REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ZIMG init rollback guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden ZIMG init rollback regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing ZIMG init rollback guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        init_release = region.find('release();')
        pixel_size = region.find('int pixelSize = OutputDepth > 8 ? 2 : 1;', init_release)
        if -1 in (init_release, pixel_size) or not (init_release < pixel_size):
            failures.append((TARGET.as_posix(), 0, 'ZIMG init must release stale graph state before deriving new resize buffer geometry'))
        if region.count('general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\\n");') != 2:
            failures.append((TARGET.as_posix(), 0, 'ZIMG init must preserve both resize-buffer geometry guardrails'))
        for occurrence, message in (
            (1, 'ZIMG init must release stale state after the first invalid resize-buffer geometry failure'),
            (2, 'ZIMG init must release stale state after the second invalid resize-buffer geometry failure'),
        ):
            failure = check_path(region, 'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\\n");', message, occurrence)
            if failure:
                failures.append((TARGET.as_posix(), 0, failure))
        for anchor, message in (
            ('general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for resize buffer\\n");',
             'ZIMG init must release stale state after resize-buffer allocation failure'),
            ('general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane geometry\\n");',
             'ZIMG init must release stale state after plane-geometry validation failure'),
            ('general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane frame size\\n");',
             'ZIMG init must release stale state after plane-frame overflow failure'),
            ('general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\\n", fail_str);',
             'ZIMG init must release stale state after zimg graph or tmp-size failures'),
            ('general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for temp buffer\\n");',
             'ZIMG init must release stale state after temp-buffer allocation failure'),
        ):
            failure = check_path(region, anchor, message)
            if failure:
                failures.append((TARGET.as_posix(), 0, failure))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ZIMG init rollback guardrails')
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

    print('ZIMG init rollback validated')


if __name__ == '__main__':
    main()
