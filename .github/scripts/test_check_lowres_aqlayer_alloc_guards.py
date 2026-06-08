#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lowres_aqlayer_alloc_guards.py')

# Coverage probes used by the scan for lowres AQ-layer allocation guardrails.
NORMALIZED_PROBES = (
    'Lowres HEVC AQ layer allocation and cleanup must guard partial creation before use and during destroy',
    'missing lowres AQ-layer guardrail: ',
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
        'pAQLayer = new (std::nothrow) PicQPAdaptationLayer[4]();',
        'if (!pAQLayer)',
        '    return false;',
        'if (!pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight))',
        '    return false;',
        'if (pAQLayer)',
        '{',
        '    delete[] pAQLayer;',
        '    pAQLayer = nullptr;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/lowres.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/lowres.cpp': valid_text().replace('pAQLayer = new (std::nothrow) PicQPAdaptationLayer[4]();', 'pAQLayer = new PicQPAdaptationLayer[4];', 1)})
        expect_fail(run_checker(root), 'forbidden lowres AQ-layer regression: pAQLayer = new PicQPAdaptationLayer[4];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/lowres.cpp': valid_text().replace('if (!pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight))', 'pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight);', 1)})
        expect_fail(run_checker(root), 'forbidden lowres AQ-layer regression: pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/lowres.cpp': valid_text().replace('if (pAQLayer)', 'if (maxAQDepth > 0)', 1)})
        expect_fail(run_checker(root), 'forbidden lowres AQ-layer regression: if (maxAQDepth > 0)')

    print('Lowres AQ-layer allocation guard tests passed')


if __name__ == '__main__':
    main()
