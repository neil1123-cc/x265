#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_recon_output_write_guard.py')

# Coverage probes used by the scan for recon output write guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing recon output write guardrail: ',
    'writePicture must return accumulated failure state instead of unconditional success',
)


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
                'source/output/yuv.cpp': 'bool YUVOutput::writePicture(const x265_picture& pic)\n{\n    failed |= std::fwrite(buf, 1, 1, ofs) != 1;\n    return !failed;\n}\n',
                'source/output/y4m.cpp': 'bool Y4MOutput::writePicture(const x265_picture& pic)\n{\n    failed |= std::fwrite("FRAME\\n", 1, 6, ofs) != 6;\n    return !failed;\n}\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/yuv.cpp': 'bool YUVOutput::writePicture(const x265_picture& pic)\n{\n    return true;\n}\n',
                'source/output/y4m.cpp': 'bool Y4MOutput::writePicture(const x265_picture& pic)\n{\n    return true;\n}\n',
            },
        )
        expect_fail(run_checker(root), 'missing recon output write guardrail')

    print('Recon output write guard tests passed')


if __name__ == '__main__':
    main()
