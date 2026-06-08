#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lavf_buffer_replace_safety.py')

# Coverage probes used by the scan for LAVF buffer replacement guardrails.
NORMALIZED_PROBES = (
    'forbidden LAVF buffer replace regression: ',
    'missing LAVF buffer replace guardrail: ',
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
                'source/input/lavf.cpp': '\n'.join((
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': 'X265_FREE(frame_buffer);\n        frame_buffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden LAVF buffer replace regression')

    print('LAVF buffer replace safety tests passed')


if __name__ == '__main__':
    main()
