#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frameencoder_initialize_geoms_staging.py')

# Coverage probe used by the scan for initializeGeoms staging guardrails.
NORMALIZED_PROBES = (
    'FrameEncoder initializeGeoms must fully stage geometry buffers before assigning member state',
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
        'bool FrameEncoder::initializeGeoms()',
        '{',
        '    uint32_t* stagedCtuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);',
        '    CUGeom* stagedCuGeoms = X265_MALLOC(CUGeom, allocGeoms * CUGeom::MAX_GEOMS);',
        '    if (!stagedCuGeoms || !stagedCtuGeomMap)',
        '    {',
        '        X265_FREE(stagedCuGeoms);',
        '        X265_FREE(stagedCtuGeomMap);',
        '        return false;',
        '    }',
        '    CUData::calcCTUGeoms(maxCUSize, maxCUSize, maxCUSize, minCUSize, stagedCuGeoms);',
        '    std::fill_n(stagedCtuGeomMap, m_numRows * m_numCols, uint32_t(0));',
        '    stagedCtuGeomMap[ctuAddr] = countGeoms * CUGeom::MAX_GEOMS;',
        '    m_ctuGeomMap = stagedCtuGeomMap;',
        '    m_cuGeoms = stagedCuGeoms;',
        '    return true;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/frameencoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_text().replace(
                    'uint32_t* stagedCtuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);',
                    'm_ctuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden frameencoder initializeGeoms staging regression: m_ctuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_text().replace('        X265_FREE(stagedCtuGeomMap);\n', '', 1),
            },
        )
        expect_fail(run_checker(root), 'missing frameencoder initializeGeoms staging guardrail: X265_FREE(stagedCtuGeomMap);')

    print('FrameEncoder initializeGeoms staging guard tests passed')


if __name__ == '__main__':
    main()
