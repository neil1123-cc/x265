#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scaler_init_rollback.py')

# Coverage probes used by the scan for scaler init rollback guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing scaler init rollback guardrail: ',
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
                'source/common/scaler.h': '\n'.join((
                    '~ScalerSlice() { destroy(); }',
                    'void resetState();',
                    '~ScalerFilterManager() {',
                    'resetState();',
                    '}',
                )) + '\n',
                'source/common/scaler.cpp': '\n'.join((
                    'void ScalerFilterManager::resetState()',
                    'delete m_slices[i];',
                    'delete m_ScalerFilters[i];',
                    'resetState();\n        return -1;',
                    'if (initScalerSlice() < 0)\n    {\n        resetState();\n        return -1;\n    }',
                    'm_slices[i] = new (std::nothrow) ScalerSlice;',
                    'if (!m_slices[i])\n        {\n            x265_log(nullptr, X265_LOG_ERROR, "alloc_slice m_slice[%d] failed\\n", i);\n            resetState();\n            return -1;\n        }',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scaler.h': 'class ScalerFilterManager {};\n',
                'source/common/scaler.cpp': 'int ScalerFilterManager::init(int algorithmFlags, VideoDesc *srcVideoDesc, VideoDesc *dstVideoDesc)\n',
            },
        )
        expect_fail(run_checker(root), 'missing scaler init rollback guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scaler.h': '\n'.join((
                    '~ScalerSlice() { destroy(); }',
                    'void resetState();',
                    '~ScalerFilterManager() {',
                    'resetState();',
                    '}',
                )) + '\n',
                'source/common/scaler.cpp': '\n'.join((
                    'void ScalerFilterManager::resetState()',
                    'delete m_slices[i];',
                    'delete m_ScalerFilters[i];',
                    'resetState();\n        return -1;',
                    'if (initScalerSlice() < 0)\n    {\n        resetState();\n        return -1;\n    }',
                    'm_slices[i] = new ScalerSlice;',
                    'if (!m_slices[i])\n        {\n            x265_log(nullptr, X265_LOG_ERROR, "alloc_slice m_slice[%d] failed\\n", i);\n            resetState();\n            return -1;\n        }',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scaler init rollback regression: m_slices[i] = new ScalerSlice;')

    print('Scaler init rollback tests passed')


if __name__ == '__main__':
    main()
