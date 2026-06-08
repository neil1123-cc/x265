#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_y4m_recon_seek_guard.py')

# Coverage probes used by the scan for Y4M recon seek guardrails.
NORMALIZED_PROBES = (
    'missing Y4M recon seek guardrail: ',
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


def valid_text():
    return '\n'.join((
        'bool Y4MOutput::writePicture(const x265_picture& pic)',
        '{',
        '    failed |= fseeko(ofs, (int64_t)outPicPos, SEEK_SET) != 0;',
        '    if (failed)',
        '        return false;',
        '    failed |= std::fwrite("FRAME\\n", 1, 6, ofs) != 6;',
        '    if (failed)',
        '        return false;',
        '    return !failed;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/y4m.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/y4m.cpp': valid_text().replace(
                    '    if (failed)\n        return false;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Y4MOutput::writePicture must return on seek failure before writing the FRAME header')

    print('Y4M recon seek guard tests passed')


if __name__ == '__main__':
    main()
