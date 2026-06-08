#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_recon_finalize_state.py')

# Coverage probes used by the scan for recon finalize-state guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing recon finalize-state guardrail: ',
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
                'source/output/output.h': 'virtual bool finalize() = 0;\n',
                'source/output/yuv.h': 'bool finalized;\nbool finalize();\n',
                'source/output/y4m.h': 'bool finalized;\nbool finalize();\n',
                'source/output/yuv.cpp': '\n'.join((
                    'finalized(false)',
                    'finalize();',
                    'bool YUVOutput::finalize()',
                    '{',
                    '    if (finalized)',
                    '        return !failed;',
                    '    failed |= std::ferror(ofs) != 0;',
                    '    failed |= std::fflush(ofs) != 0;',
                    '    failed |= std::fclose(ofs) != 0;',
                    '    ofs = nullptr;',
                    '    return !failed;',
                    '}',
                )) + '\n',
                'source/output/y4m.cpp': '\n'.join((
                    'finalized(false)',
                    'finalize();',
                    'bool Y4MOutput::finalize()',
                    '{',
                    '    if (finalized)',
                    '        return !failed;',
                    '    failed |= std::ferror(ofs) != 0;',
                    '    failed |= std::fflush(ofs) != 0;',
                    '    failed |= std::fclose(ofs) != 0;',
                    '    ofs = nullptr;',
                    '    return !failed;',
                    '}',
                )) + '\n',
                'source/x265cli.h': 'bool destroy();\n',
                'source/x265cli.cpp': 'closeFailed |= !recon[i]->finalize();\nreturn closeFailed;\n',
                'source/x265.cpp': 'bool destroyFailed = false;\ndestroyFailed |= cliopt[idx].destroy();\nif (!ret && destroyFailed)\n    ret = 3;\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/output.h': 'virtual void release() = 0;\n',
            },
        )
        expect_fail(run_checker(root), 'missing recon finalize-state guardrail')

    print('Recon finalize-state guard tests passed')


if __name__ == '__main__':
    main()
