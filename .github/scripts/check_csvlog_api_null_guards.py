#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_function(func_text, label, snippets, ordering_pairs, ordering_message):
    failures = []
    if not func_text:
        failures.append((TARGET.as_posix(), 0, f'missing {label} function'))
        return failures

    for snippet in snippets:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing {label} null guardrail: {snippet}'))

    positions = []
    search_from = 0
    for snippet in ordering_pairs:
        pos = func_text.find(snippet, search_from if search_from else 0)
        positions.append(pos)
        if pos != -1:
            search_from = pos
    if any(pos == -1 for pos in positions) or positions != sorted(positions):
        failures.append((TARGET.as_posix(), 0, ordering_message))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    open_text = extract_braced_block(text, 'FILE* x265_csvlog_open(const x265_param* param)')
    frame_text = extract_braced_block(text, 'void x265_csvlog_frame(const x265_param* param, const x265_picture* pic)')
    encode_text = extract_braced_block(text, 'void x265_csvlog_encode(const x265_param *p, const x265_stats *stats, int padx, int pady, int argc, char** argv)')

    failures = []
    failures.extend(check_function(
        open_text,
        'x265_csvlog_open',
        (
            'if (!param)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_open requires a non-null parameter struct\\n");',
            'return nullptr;',
            'FILE *csvfp = x265_fopen(param->csvfn, "r");',
        ),
        (
            'if (!param)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_open requires a non-null parameter struct\\n");',
            'return nullptr;',
            'FILE *csvfp = x265_fopen(param->csvfn, "r");',
        ),
        'x265_csvlog_open must reject null param before opening the CSV path',
    ))
    failures.extend(check_function(
        frame_text,
        'x265_csvlog_frame',
        (
            'if (!param || !pic)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_frame requires non-null param and picture\\n");',
            'return;',
            'if (!param->csvfpt)',
            'const x265_frame_stats* frameStats = &pic->frameData;',
        ),
        (
            'if (!param || !pic)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_frame requires non-null param and picture\\n");',
            'return;',
            'if (!param->csvfpt)',
            'const x265_frame_stats* frameStats = &pic->frameData;',
        ),
        'x265_csvlog_frame must reject null param/pic before touching csvfpt or frameData',
    ))
    failures.extend(check_function(
        encode_text,
        'x265_csvlog_encode',
        (
            'if (!p || !stats)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_encode requires non-null param and stats\\n");',
            'return;',
            'if (!p->csvfpt)',
            'const x265_api * api = x265_api_get(0);',
            'if (!api)',
            'if (argc > 0 && argv)',
            'fputs(argv[i], p->csvfpt);',
            'stats->elapsedEncodeTime',
            'api->version_str',
        ),
        (
            'if (!p || !stats)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_encode requires non-null param and stats\\n");',
            'return;',
            'if (!p->csvfpt)',
            'const x265_api * api = x265_api_get(0);',
            'if (!api)',
            'if (argc > 0 && argv)',
            'fputs(argv[i], p->csvfpt);',
            'stats->elapsedEncodeTime',
            'api->version_str',
        ),
        'x265_csvlog_encode must reject null param/stats and guard argv/api before logging summary state',
    ))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CSV log API null guards')
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

    print('CSV log API null guards validated')


if __name__ == '__main__':
    main()
