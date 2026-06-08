#!/usr/bin/env python3
import argparse
from pathlib import Path


HEADER_TARGET = Path('source/common/scaler.h')
CPP_TARGET = Path('source/common/scaler.cpp')


def require_snippets(text, target, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet not in text:
            failures.append((target.as_posix(), 0, f'missing {label}: {snippet}'))
    return failures


def forbid_snippets(text, target, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet in text:
            failures.append((target.as_posix(), 0, f'forbidden {label}: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    header_path = repo_root / HEADER_TARGET
    if not header_path.is_file():
        failures.append((HEADER_TARGET.as_posix(), 0, 'missing file'))
    else:
        text = header_path.read_text(encoding='utf-8', errors='ignore')
        failures.extend(require_snippets(
            text,
            HEADER_TARGET,
            (
                '#include <new>',
                'virtual bool hasScalingHelper() const { return true; }',
                'ScalerHLumFilter(int bitDepth) : m_hFilterScaler(nullptr)',
                'm_hFilterScaler = new (std::nothrow) HFilterScaler8Bit;',
                'm_hFilterScaler = new (std::nothrow) HFilterScaler10Bit;',
                'bool hasScalingHelper() const { return m_hFilterScaler != nullptr; }',
                'ScalerHCrFilter(int bitDepth) : m_hFilterScaler(nullptr)',
                'ScalerVLumFilter(int bitDepth) : m_vFilterScaler(nullptr)',
                'm_vFilterScaler = new (std::nothrow) VFilterScaler8Bit;',
                'm_vFilterScaler = new (std::nothrow) VFilterScaler10Bit;',
                'bool hasScalingHelper() const { return m_vFilterScaler != nullptr; }',
                'ScalerVCrFilter(int bitDepth) : m_vFilterScaler(nullptr)',
            ),
            'scaler helper allocation guardrail',
        ))
        failures.extend(forbid_snippets(
            text,
            HEADER_TARGET,
            (
                'ScalerHLumFilter(int bitDepth) { bitDepth == 8 ? m_hFilterScaler = new HFilterScaler8Bit : bitDepth == 10 ? m_hFilterScaler = new HFilterScaler10Bit : nullptr;}',
                'ScalerHCrFilter(int bitDepth) { bitDepth == 8 ? m_hFilterScaler = new HFilterScaler8Bit : bitDepth == 10 ? m_hFilterScaler = new HFilterScaler10Bit : nullptr;}',
                'ScalerVLumFilter(int bitDepth) { bitDepth == 8 ? m_vFilterScaler = new VFilterScaler8Bit : bitDepth == 10 ? m_vFilterScaler = new VFilterScaler10Bit : nullptr;}',
                'ScalerVCrFilter(int bitDepth) { bitDepth == 8 ? m_vFilterScaler = new VFilterScaler8Bit : bitDepth == 10 ? m_vFilterScaler = new VFilterScaler10Bit : nullptr;}',
            ),
            'scaler helper allocation regression',
        ))

    cpp_path = repo_root / CPP_TARGET
    if not cpp_path.is_file():
        failures.append((CPP_TARGET.as_posix(), 0, 'missing file'))
    else:
        text = cpp_path.read_text(encoding='utf-8', errors='ignore')
        failures.extend(require_snippets(
            text,
            CPP_TARGET,
            (
                '!m_ScalerFilters[0] || !m_ScalerFilters[0]->hasScalingHelper() ||',
                '!m_ScalerFilters[1] || !m_ScalerFilters[1]->hasScalingHelper() ||',
                '!m_ScalerFilters[2] || !m_ScalerFilters[2]->hasScalingHelper() ||',
                '!m_ScalerFilters[3] || !m_ScalerFilters[3]->hasScalingHelper() ||',
            ),
            'scaler init helper guardrail',
        ))
        failures.extend(forbid_snippets(
            text,
            CPP_TARGET,
            (
                'if (!m_ScalerFilters[0] || m_ScalerFilters[0]->initCoeff(',
                'if (!m_ScalerFilters[2] || m_ScalerFilters[2]->initCoeff(',
            ),
            'scaler init helper regression',
        ))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scaler helper allocation guards')
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

    print('Scaler helper allocation guards validated')


if __name__ == '__main__':
    main()
