#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_wavefront_init_rollback.py')

# Coverage probes used by the scan for wavefront init-rollback guardrails.
NORMALIZED_PROBES = (
    'missing ',
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
                'source/common/wavefront.cpp': '\n'.join((
                    'void WaveFront::releaseState()',
                    'releaseState();',
                    'std::atomic<uint32_t>* internalDependencyBitmap = new (std::nothrow) std::atomic<uint32_t>[m_numWords];',
                    'std::atomic<uint32_t>* externalDependencyBitmap = new (std::nothrow) std::atomic<uint32_t>[m_numWords];',
                    'uint32_t* rowToIdx = X265_MALLOC(uint32_t, m_numRows);',
                    'uint32_t* idxToRow = X265_MALLOC(uint32_t, m_numRows);',
                    'if (!internalDependencyBitmap || !externalDependencyBitmap || !rowToIdx || !idxToRow)',
                    'delete[] internalDependencyBitmap;',
                    'delete[] externalDependencyBitmap;',
                    'x265_free((void*)rowToIdx);',
                    'x265_free((void*)idxToRow);',
                    'm_row_to_idx = nullptr;',
                    'm_idx_to_row = nullptr;',
                    'm_internalDependencyBitmap = nullptr;',
                    'm_externalDependencyBitmap = nullptr;',
                    'return true;',
                )) + '\n',
                'source/common/wavefront.h': '\n'.join((
                    'void releaseState();',
                    ', m_numWords(0)',
                    ', m_numRows(0)',
                    ', m_sLayerId(0)',
                    ', m_row_to_idx(nullptr)',
                    ', m_idx_to_row(nullptr)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/wavefront.cpp': 'return m_internalDependencyBitmap && m_externalDependencyBitmap;\n',
                'source/common/wavefront.h': 'void releaseState();\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden WaveFront init rollback regression')

    print('WaveFront init rollback tests passed')


if __name__ == '__main__':
    main()
