#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scaler_chroma_dims_guard.py')


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


def valid_scaler_text():
    return '\n'.join((
        'int ScalerFilterManager::init(int algorithmFlags, VideoDesc *srcVideoDesc, VideoDesc *dstVideoDesc)',
        '{',
        '    if (x265_cli_csps[srcCsp].planes <= 1)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "scaler: monochrome ABR ladder scaling is unsupported\\n");',
        '        return -1;',
        '    }',
        '    if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "scaler: chroma plane dimensions must remain positive after subsampling\\n");',
        '        return -1;',
        '    }',
        '    crXInc = (((int64_t)m_crSrcW << 16) + (m_crDstW >> 1)) / m_crDstW;',
        '    crYInc = (((int64_t)m_crSrcH << 16) + (m_crDstH >> 1)) / m_crDstH;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/scaler.cpp': valid_scaler_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scaler.cpp': valid_scaler_text().replace(
                    'if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "scaler: chroma plane dimensions must remain positive after subsampling\\n");\n'
                    '        return -1;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing scaler chroma-dimension guardrail: if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scaler.cpp': valid_scaler_text().replace(
                    '    if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "scaler: chroma plane dimensions must remain positive after subsampling\\n");\n'
                    '        return -1;\n'
                    '    }\n'
                    '    crXInc = (((int64_t)m_crSrcW << 16) + (m_crDstW >> 1)) / m_crDstW;\n'
                    '    crYInc = (((int64_t)m_crSrcH << 16) + (m_crDstH >> 1)) / m_crDstH;\n',
                    '    crXInc = (((int64_t)m_crSrcW << 16) + (m_crDstW >> 1)) / m_crDstW;\n'
                    '    if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "scaler: chroma plane dimensions must remain positive after subsampling\\n");\n'
                    '        return -1;\n'
                    '    }\n'
                    '    crYInc = (((int64_t)m_crSrcH << 16) + (m_crDstH >> 1)) / m_crDstH;\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Scaler init must reject zero-sized chroma planes before chroma increment division')

    print('Scaler chroma-dimension guard tests passed')


if __name__ == '__main__':
    main()
