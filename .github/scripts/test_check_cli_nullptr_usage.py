#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_nullptr_usage.py')


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'int main() { return 0; }\n',
                'source/x265cli.cpp': 'const char* ptr = nullptr;\n',
                'source/x265cli.h': 'static const int ok = 1;\n',
                'source/input/yuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/input/avs.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/gop.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/matroska_ebml.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/reconplay.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/y4m.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/common.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/yuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/shortyuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/bitstream.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/aarch64/cpu.h': 'static const void* p = nullptr;\n',
                'source/common/cpu.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/primitives.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/temporalfilter.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/threading.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/threadpool.cpp': 'void ok() { void* p = nullptr; const char* text = "NULL"; }\n',
                'source/common/wavefront.h': 'static const void* p = nullptr;\n',
                'source/common/piclist.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/frame.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/frame.h': 'static const void* p = nullptr;\n',
                'source/common/framedata.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/slice.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/slice.h': 'static const void* p = nullptr;\n',
                'source/common/quant.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/deblock.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/scalinglist.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/scaler.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/ringmem.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/param.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/cudata.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/cudata.h': 'static const void* p = nullptr;\n',
                'source/common/predict.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/picyuv.h': 'static const void* p = nullptr;\n',
                'source/common/pixel.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/riscv64/cpu.h': 'static const void* p = nullptr;\n',
                'source/common/riscv64/pixel-prim.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/winxp.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/aarch64/pixel-prim.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/bitcost.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/bitcost.h': 'static const void* p = nullptr;\n',
                'source/encoder/api.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/analysis.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/analysis.h': 'static const void* p = nullptr;\n',
                'source/encoder/dpb.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/dpb.h': 'static const void* p = nullptr;\n',
                'source/encoder/frameencoder.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/encoder.h': 'static const void* p = nullptr;\n',
                'source/encoder/framefilter.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/motion.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/nal.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/ratecontrol.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/reference.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/sao.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/search.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/search.h': 'static const void* p = nullptr;\n',
                'source/encoder/sei.h': 'static const void* p = nullptr;\n',
                'source/encoder/slicetype.h': 'static const void* p = nullptr;\n',
                'source/encoder/slicetype.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/weightPrediction.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/filters/zimgfilter.cpp': 'void ok() { void* p = nullptr; }\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        expect_fail(run_checker(root), 'missing file')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'void* ptr = NULL;\n',
                'source/x265cli.cpp': 'const char* ptr = nullptr;\n',
                'source/x265cli.h': 'static const int ok = 1;\n',
                'source/input/yuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/input/avs.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/gop.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/matroska_ebml.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/reconplay.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/output/y4m.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/common.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/yuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/shortyuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/bitstream.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/aarch64/cpu.h': 'static const void* p = nullptr;\n',
                'source/common/cpu.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/primitives.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/temporalfilter.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/threading.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/threadpool.cpp': 'void ok() { void* p = nullptr; const char* text = "NULL"; }\n',
                'source/common/wavefront.h': 'static const void* p = nullptr;\n',
                'source/common/piclist.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/frame.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/frame.h': 'static const void* p = nullptr;\n',
                'source/common/framedata.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/slice.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/slice.h': 'static const void* p = nullptr;\n',
                'source/common/quant.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/deblock.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/scalinglist.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/scaler.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/ringmem.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/param.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/cudata.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/cudata.h': 'static const void* p = nullptr;\n',
                'source/common/predict.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/picyuv.h': 'static const void* p = nullptr;\n',
                'source/common/pixel.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/riscv64/cpu.h': 'static const void* p = nullptr;\n',
                'source/common/riscv64/pixel-prim.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/winxp.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/aarch64/pixel-prim.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/bitcost.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/bitcost.h': 'static const void* p = nullptr;\n',
                'source/encoder/api.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/analysis.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/analysis.h': 'static const void* p = nullptr;\n',
                'source/encoder/dpb.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/dpb.h': 'static const void* p = nullptr;\n',
                'source/encoder/frameencoder.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/encoder.h': 'static const void* p = nullptr;\n',
                'source/encoder/framefilter.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/motion.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/nal.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/ratecontrol.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/reference.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/sao.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/search.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/search.h': 'static const void* p = nullptr;\n',
                'source/encoder/sei.h': 'static const void* p = nullptr;\n',
                'source/encoder/slicetype.h': 'static const void* p = nullptr;\n',
                'source/encoder/slicetype.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/encoder/weightPrediction.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/filters/zimgfilter.cpp': 'void ok() { void* p = nullptr; }\n',
            },
        )
        expect_fail(run_checker(root), 'use nullptr instead of NULL in CLI entrypoint C++ sources')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'const char* text = "NULL";\n',
                'source/x265cli.cpp': '// NULL in comment is fine\n',
                'source/x265cli.h': '/* NULL in block comment is fine */\n',
                'source/input/yuv.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/input/avs.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/output/gop.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/output/matroska_ebml.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/output/reconplay.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/output/y4m.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/common.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/common/yuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/shortyuv.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/bitstream.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/aarch64/cpu.h': 'static const char* text = "NULL";\n',
                'source/common/cpu.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/primitives.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/common/temporalfilter.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/threading.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/threadpool.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/common/wavefront.h': 'static const char* text = "NULL";\n',
                'source/common/piclist.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/common/frame.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/common/frame.h': 'static const char* text = "NULL";\n',
                'source/common/framedata.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/common/slice.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/slice.h': 'static const void* p = nullptr;\n',
                'source/common/quant.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/common/deblock.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/common/scalinglist.cpp': 'void ok() { void* p = nullptr; }\n',
                'source/common/scaler.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/common/ringmem.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/common/param.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/common/cudata.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/common/cudata.h': 'static const char* text = "NULL";\n',
                'source/common/predict.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/common/picyuv.h': 'static const char* text = "NULL";\n',
                'source/common/pixel.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/common/riscv64/cpu.h': 'static const char* text = "NULL";\n',
                'source/common/riscv64/pixel-prim.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/common/winxp.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/common/aarch64/pixel-prim.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/encoder/bitcost.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/encoder/bitcost.h': 'static const char* text = "NULL";\n',
                'source/encoder/api.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/encoder/analysis.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/encoder/analysis.h': 'static const char* text = "NULL";\n',
                'source/encoder/dpb.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/encoder/dpb.h': 'static const char* text = "NULL";\n',
                'source/encoder/frameencoder.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/encoder/encoder.h': 'static const char* text = "NULL";\n',
                'source/encoder/framefilter.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/encoder/motion.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/encoder/nal.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/encoder/ratecontrol.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/encoder/reference.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/encoder/sao.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/encoder/search.cpp': 'void ok() { const char* text = "NULL"; }\n',
                'source/encoder/search.h': 'static const char* text = "NULL";\n',
                'source/encoder/sei.h': 'static const char* text = "NULL";\n',
                'source/encoder/slicetype.h': 'static const char* text = "NULL";\n',
                'source/encoder/slicetype.cpp': 'void ok() { /* NULL in block comment */ }\n',
                'source/encoder/weightPrediction.cpp': 'void ok() { // NULL in comment\n}\n',
                'source/filters/zimgfilter.cpp': 'void ok() { /* NULL in block comment */ }\n',
            },
        )
        expect_pass(run_checker(root))

    print('CLI nullptr guard tests passed')


if __name__ == '__main__':
    main()
