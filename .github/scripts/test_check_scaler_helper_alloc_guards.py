#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scaler_helper_alloc_guards.py')

# Coverage probes used by the scan for scaler helper allocation guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'forbidden ',
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


def valid_header_text():
    return '\n'.join((
        '#include <new>',
        'virtual bool hasScalingHelper() const { return true; }',
        'ScalerHLumFilter(int bitDepth) : m_hFilterScaler(nullptr)',
        '{',
        '    if (bitDepth == 8)',
        '        m_hFilterScaler = new (std::nothrow) HFilterScaler8Bit;',
        '    else if (bitDepth == 10)',
        '        m_hFilterScaler = new (std::nothrow) HFilterScaler10Bit;',
        '}',
        'bool hasScalingHelper() const { return m_hFilterScaler != nullptr; }',
        'ScalerHCrFilter(int bitDepth) : m_hFilterScaler(nullptr)',
        '{',
        '    if (bitDepth == 8)',
        '        m_hFilterScaler = new (std::nothrow) HFilterScaler8Bit;',
        '    else if (bitDepth == 10)',
        '        m_hFilterScaler = new (std::nothrow) HFilterScaler10Bit;',
        '}',
        'ScalerVLumFilter(int bitDepth) : m_vFilterScaler(nullptr)',
        '{',
        '    if (bitDepth == 8)',
        '        m_vFilterScaler = new (std::nothrow) VFilterScaler8Bit;',
        '    else if (bitDepth == 10)',
        '        m_vFilterScaler = new (std::nothrow) VFilterScaler10Bit;',
        '}',
        'bool hasScalingHelper() const { return m_vFilterScaler != nullptr; }',
        'ScalerVCrFilter(int bitDepth) : m_vFilterScaler(nullptr)',
        '{',
        '    if (bitDepth == 8)',
        '        m_vFilterScaler = new (std::nothrow) VFilterScaler8Bit;',
        '    else if (bitDepth == 10)',
        '        m_vFilterScaler = new (std::nothrow) VFilterScaler10Bit;',
        '}',
    )) + '\n'


def valid_cpp_text():
    return '\n'.join((
        'if (!m_ScalerFilters[0] || !m_ScalerFilters[0]->hasScalingHelper() ||',
        '    m_ScalerFilters[0]->initCoeff(...) < 0)',
        '{',
        '    resetState();',
        '    return -1;',
        '}',
        'if (!m_ScalerFilters[1] || !m_ScalerFilters[1]->hasScalingHelper() ||',
        '    m_ScalerFilters[1]->initCoeff(...) < 0)',
        '{',
        '    resetState();',
        '    return -1;',
        '}',
        'if (!m_ScalerFilters[2] || !m_ScalerFilters[2]->hasScalingHelper() ||',
        '    m_ScalerFilters[2]->initCoeff(...) < 0)',
        '{',
        '    resetState();',
        '    return -1;',
        '}',
        'if (!m_ScalerFilters[3] || !m_ScalerFilters[3]->hasScalingHelper() ||',
        '    m_ScalerFilters[3]->initCoeff(...) < 0)',
        '{',
        '    resetState();',
        '    return -1;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/common/scaler.h': valid_header_text(),
            'source/common/scaler.cpp': valid_cpp_text(),
        })
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/common/scaler.h': valid_header_text().replace('ScalerHCrFilter(int bitDepth) : m_hFilterScaler(nullptr)', '', 1),
            'source/common/scaler.cpp': valid_cpp_text(),
        })
        expect_fail(run_checker(root), 'missing scaler helper allocation guardrail: ScalerHCrFilter(int bitDepth) : m_hFilterScaler(nullptr)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/common/scaler.h': valid_header_text().replace('virtual bool hasScalingHelper() const { return true; }', '', 1),
            'source/common/scaler.cpp': valid_cpp_text(),
        })
        expect_fail(run_checker(root), 'missing scaler helper allocation guardrail: virtual bool hasScalingHelper() const { return true; }')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/common/scaler.h': valid_header_text(),
            'source/common/scaler.cpp': valid_cpp_text().replace('if (!m_ScalerFilters[2] || !m_ScalerFilters[2]->hasScalingHelper() ||', 'if (!m_ScalerFilters[2] ||', 1),
        })
        expect_fail(run_checker(root), 'missing scaler init helper guardrail: !m_ScalerFilters[2] || !m_ScalerFilters[2]->hasScalingHelper() ||')

    print('Scaler helper allocation guard tests passed')


if __name__ == '__main__':
    main()
