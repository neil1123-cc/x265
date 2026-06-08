#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/x265.cpp'),
    Path('source/x265cli.cpp'),
    Path('source/x265cli.h'),
    Path('source/input/yuv.cpp'),
    Path('source/input/avs.cpp'),
    Path('source/output/gop.cpp'),
    Path('source/output/matroska_ebml.cpp'),
    Path('source/output/reconplay.cpp'),
    Path('source/output/y4m.cpp'),
    Path('source/common/common.cpp'),
    Path('source/common/yuv.cpp'),
    Path('source/common/shortyuv.cpp'),
    Path('source/common/bitstream.cpp'),
    Path('source/common/aarch64/cpu.h'),
    Path('source/common/cpu.cpp'),
    Path('source/common/primitives.cpp'),
    Path('source/common/temporalfilter.cpp'),
    Path('source/common/threading.cpp'),
    Path('source/common/threadpool.cpp'),
    Path('source/common/wavefront.h'),
    Path('source/common/piclist.cpp'),
    Path('source/common/frame.cpp'),
    Path('source/common/frame.h'),
    Path('source/common/framedata.cpp'),
    Path('source/common/slice.cpp'),
    Path('source/common/slice.h'),
    Path('source/common/quant.cpp'),
    Path('source/common/deblock.cpp'),
    Path('source/common/scalinglist.cpp'),
    Path('source/common/scaler.cpp'),
    Path('source/common/ringmem.cpp'),
    Path('source/common/param.cpp'),
    Path('source/common/cudata.cpp'),
    Path('source/common/cudata.h'),
    Path('source/common/predict.cpp'),
    Path('source/common/picyuv.h'),
    Path('source/common/pixel.cpp'),
    Path('source/common/riscv64/cpu.h'),
    Path('source/common/riscv64/pixel-prim.cpp'),
    Path('source/common/winxp.cpp'),
    Path('source/common/aarch64/pixel-prim.cpp'),
    Path('source/encoder/bitcost.cpp'),
    Path('source/encoder/bitcost.h'),
    Path('source/encoder/api.cpp'),
    Path('source/encoder/analysis.cpp'),
    Path('source/encoder/analysis.h'),
    Path('source/encoder/dpb.cpp'),
    Path('source/encoder/dpb.h'),
    Path('source/encoder/frameencoder.cpp'),
    Path('source/encoder/encoder.h'),
    Path('source/encoder/framefilter.cpp'),
    Path('source/encoder/nal.cpp'),
    Path('source/encoder/motion.cpp'),
    Path('source/encoder/ratecontrol.cpp'),
    Path('source/encoder/reference.cpp'),
    Path('source/encoder/slicetype.cpp'),
    Path('source/encoder/sao.cpp'),
    Path('source/encoder/search.cpp'),
    Path('source/encoder/search.h'),
    Path('source/encoder/sei.h'),
    Path('source/encoder/slicetype.h'),
    Path('source/encoder/weightPrediction.cpp'),
    Path('source/filters/zimgfilter.cpp'),
)


def find_null_tokens(text):
    line = 1
    index = 0
    length = len(text)
    in_line_comment = False
    in_block_comment = False
    in_single_quote = False
    in_double_quote = False
    escaped = False

    while index < length:
        char = text[index]
        nxt = text[index + 1] if index + 1 < length else ''

        if char == '\n':
            line += 1
            in_line_comment = False
            escaped = False
            index += 1
            continue

        if in_line_comment:
            index += 1
            continue

        if in_block_comment:
            if char == '*' and nxt == '/':
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if in_single_quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == "'":
                in_single_quote = False
            index += 1
            continue

        if in_double_quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_double_quote = False
            index += 1
            continue

        if char == '/' and nxt == '/':
            in_line_comment = True
            index += 2
            continue

        if char == '/' and nxt == '*':
            in_block_comment = True
            index += 2
            continue

        if char == "'":
            in_single_quote = True
            index += 1
            continue

        if char == '"':
            in_double_quote = True
            index += 1
            continue

        if text.startswith('NULL', index):
            before = text[index - 1] if index > 0 else ''
            after = text[index + 4] if index + 4 < length else ''
            if (not before or not (before.isalnum() or before == '_')) and (not after or not (after.isalnum() or after == '_')):
                yield line
            index += 4
            continue

        index += 1


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for relative_path in TARGETS:
        path = repo_root / relative_path
        if not path.is_file():
            failures.append((relative_path.as_posix(), 0, 'missing file'))
            continue
        for line in find_null_tokens(path.read_text(encoding='utf-8', errors='ignore')):
            failures.append((relative_path.as_posix(), line, 'use nullptr instead of NULL in CLI entrypoint C++ sources'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI entrypoint C++ sources for NULL regressions')
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

    print('CLI nullptr guard validated')


if __name__ == '__main__':
    main()
