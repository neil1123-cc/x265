#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/frameencoder.cpp')
REQUIRED_SNIPPETS = (
    'uint32_t* stagedCtuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);',
    'CUGeom* stagedCuGeoms = X265_MALLOC(CUGeom, allocGeoms * CUGeom::MAX_GEOMS);',
    'if (!stagedCuGeoms || !stagedCtuGeomMap)',
    'X265_FREE(stagedCuGeoms);',
    'X265_FREE(stagedCtuGeomMap);',
    'CUData::calcCTUGeoms(maxCUSize, maxCUSize, maxCUSize, minCUSize, stagedCuGeoms);',
    'std::fill_n(stagedCtuGeomMap, m_numRows * m_numCols, uint32_t(0));',
    'stagedCtuGeomMap[ctuAddr] = countGeoms * CUGeom::MAX_GEOMS;',
    'm_ctuGeomMap = stagedCtuGeomMap;',
    'm_cuGeoms = stagedCuGeoms;',
)

FORBIDDEN_SNIPPETS = (
    'm_ctuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);',
    'm_cuGeoms = X265_MALLOC(CUGeom, allocGeoms * CUGeom::MAX_GEOMS);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing frameencoder initializeGeoms staging guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden frameencoder initializeGeoms staging regression: {snippet}'))

    alloc_map_pos = text.find('uint32_t* stagedCtuGeomMap = X265_MALLOC(uint32_t, m_numRows * m_numCols);')
    alloc_geoms_pos = text.find('CUGeom* stagedCuGeoms = X265_MALLOC(CUGeom, allocGeoms * CUGeom::MAX_GEOMS);', alloc_map_pos if alloc_map_pos != -1 else 0)
    body_geom_pos = text.find('CUData::calcCTUGeoms(maxCUSize, maxCUSize, maxCUSize, minCUSize, stagedCuGeoms);', alloc_geoms_pos if alloc_geoms_pos != -1 else 0)
    assign_map_pos = text.find('m_ctuGeomMap = stagedCtuGeomMap;', body_geom_pos if body_geom_pos != -1 else 0)
    assign_geoms_pos = text.find('m_cuGeoms = stagedCuGeoms;', assign_map_pos if assign_map_pos != -1 else 0)
    if -1 in (alloc_map_pos, alloc_geoms_pos, body_geom_pos, assign_map_pos, assign_geoms_pos) or not (alloc_map_pos < alloc_geoms_pos < body_geom_pos < assign_map_pos < assign_geoms_pos):
        failures.append((TARGET.as_posix(), 0, 'FrameEncoder initializeGeoms must fully stage geometry buffers before assigning member state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check FrameEncoder initializeGeoms staging guardrails')
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

    print('FrameEncoder initializeGeoms staging guard validated')


if __name__ == '__main__':
    main()
