#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/frame.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    required = (
        'pixel* stagedEdgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'pixel* stagedGaussianPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'pixel* stagedThetaPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'if (!stagedEdgePic || !stagedGaussianPic || !stagedThetaPic)',
        'X265_FREE(stagedEdgePic);',
        'X265_FREE(stagedGaussianPic);',
        'X265_FREE(stagedThetaPic);',
        'm_edgePic = stagedEdgePic;',
        'm_gaussianPic = stagedGaussianPic;',
        'm_thetaPic = stagedThetaPic;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing frame edge-AQ allocation guardrail: {snippet}'))

    forbidden = (
        'm_edgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'm_gaussianPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'm_thetaPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden frame edge-AQ allocation regression: {snippet}'))

    edge_alloc_pos = text.find('pixel* stagedEdgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));')
    gaussian_alloc_pos = text.find('pixel* stagedGaussianPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));', edge_alloc_pos if edge_alloc_pos != -1 else 0)
    theta_alloc_pos = text.find('pixel* stagedThetaPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));', gaussian_alloc_pos if gaussian_alloc_pos != -1 else 0)
    guard_pos = text.find('if (!stagedEdgePic || !stagedGaussianPic || !stagedThetaPic)', theta_alloc_pos if theta_alloc_pos != -1 else 0)
    free_edge_pos = text.find('X265_FREE(stagedEdgePic);', guard_pos if guard_pos != -1 else 0)
    free_gaussian_pos = text.find('X265_FREE(stagedGaussianPic);', free_edge_pos if free_edge_pos != -1 else 0)
    free_theta_pos = text.find('X265_FREE(stagedThetaPic);', free_gaussian_pos if free_gaussian_pos != -1 else 0)
    publish_edge_pos = text.find('m_edgePic = stagedEdgePic;', free_theta_pos if free_theta_pos != -1 else 0)
    publish_theta_pos = text.find('m_thetaPic = stagedThetaPic;', publish_edge_pos if publish_edge_pos != -1 else 0)
    if -1 in (
        edge_alloc_pos, gaussian_alloc_pos, theta_alloc_pos, guard_pos,
        free_edge_pos, free_gaussian_pos, free_theta_pos, publish_edge_pos, publish_theta_pos,
    ) or not (
        edge_alloc_pos < gaussian_alloc_pos < theta_alloc_pos < guard_pos <
        free_edge_pos < free_gaussian_pos < free_theta_pos < publish_edge_pos < publish_theta_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Frame::create must stage edge-AQ picture buffers, roll back partial allocations on failure, and only publish members after all three allocations succeed'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Frame edge-AQ allocation guards')
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

    print('Frame edge-AQ allocation guards validated')


if __name__ == '__main__':
    main()
