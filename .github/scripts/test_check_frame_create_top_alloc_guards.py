#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frame_create_top_alloc_guards.py')

# Coverage probes used by the scan for frame top-level allocation guardrails.
NORMALIZED_PROBES = (
    'missing Frame::Frame constructor',
    'missing Frame::create function',
    'missing Frame::destroy function',
    'Frame::destroy must tolerate partial MCSTF setup before deleting the temporal filter',
    'TemporalFilter::init must validate MotionEstimatorTLD buffers and clear m_metld before returning success',
    'missing frame constructor cleanup guardrail: ',
    'missing frame create top alloc guardrail: ',
    'missing temporal filter init guardrail: ',
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


def valid_frame_text():
    return '\n'.join((
        'Frame::Frame()',
        '{',
        '    m_fencPic = nullptr;',
        '    m_fencPicSubsampled2 = nullptr;',
        '    m_fencPicSubsampled4 = nullptr;',
        '    m_mcstffencPic = nullptr;',
        '}',
        'bool Frame::create(x265_param *param, float* quantOffsets)',
        '{',
        '    m_fencPic = new (std::nothrow) PicYuv;',
        '    if (!m_fencPic)',
        '        return false;',
        '    if (m_param->bEnableTemporalFilter)',
        '    {',
        '        m_mcstf = new (std::nothrow) TemporalFilter;',
        '        m_mcstffencPic = new (std::nothrow) PicYuv;',
        '        if (!m_mcstf || !m_mcstffencPic)',
        '            return false;',
        '        if (!m_mcstf->init(param))',
        '            return false;',
        '        m_fencPicSubsampled2 = new (std::nothrow) PicYuv;',
        '        m_fencPicSubsampled4 = new (std::nothrow) PicYuv;',
        '        if (!m_fencPicSubsampled2 || !m_fencPicSubsampled4)',
        '            return false;',
        '    }',
        '    return true;',
        '}',
        'void Frame::destroy()',
        '{',
        '    if (m_param->bEnableTemporalFilter)',
        '    {',
        '        if (m_mcstf)',
        '        {',
        '            delete m_mcstf->m_metld;',
        '            for (int i = 0; i < (m_mcstf->m_range << 1); i++)',
        '                m_mcstf->destroyRefPicInfo(&m_mcstfRefList[i]);',
        '        }',
        '        delete m_mcstf;',
        '        m_mcstf = nullptr;',
        '    }',
        '}',
    )) + '\n'


def valid_temporalfilter_text():
    return '\n'.join((
        'bool TemporalFilter::init(const x265_param* param)',
        '{',
        '    m_metld = new (std::nothrow) MotionEstimatorTLD;',
        '    if (!hasMotionEstimatorTLDBuffers(m_metld))',
        '    {',
        '        delete m_metld;',
        '        m_metld = nullptr;',
        '        return false;',
        '    }',
        '    return true;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/frame.cpp': valid_frame_text(),
                'source/common/temporalfilter.cpp': valid_temporalfilter_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/frame.cpp': valid_frame_text().replace('    m_fencPic = new (std::nothrow) PicYuv;\n', '    m_fencPic = new PicYuv;\n', 1),
                'source/common/temporalfilter.cpp': valid_temporalfilter_text(),
            },
        )
        expect_fail(run_checker(root), 'forbidden frame create top alloc regression: m_fencPic = new PicYuv;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/frame.cpp': valid_frame_text(),
                'source/common/temporalfilter.cpp': valid_temporalfilter_text().replace('    m_metld = new (std::nothrow) MotionEstimatorTLD;\n', '    m_metld = new MotionEstimatorTLD;\n', 1),
            },
        )
        expect_fail(run_checker(root), 'forbidden temporal filter init regression: m_metld = new MotionEstimatorTLD;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/frame.cpp': valid_frame_text().replace('        if (m_mcstf)\n        {\n            delete m_mcstf->m_metld;\n            for (int i = 0; i < (m_mcstf->m_range << 1); i++)\n                m_mcstf->destroyRefPicInfo(&m_mcstfRefList[i]);\n        }\n', '', 1),
                'source/common/temporalfilter.cpp': valid_temporalfilter_text(),
            },
        )
        expect_fail(run_checker(root), 'missing frame destroy MCSTF cleanup guardrail: if (m_mcstf)')

    print('Frame::create top allocation guard tests passed')


if __name__ == '__main__':
    main()
