#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_bitcost_alloc_guards.py')

# Coverage probes used by the scan for BitCost allocation guardrails.
NORMALIZED_PROBES = (
    'BitCost must guard log-table and MV-cost allocations before pointer offsetting or dereference',
    'forbidden BitCost allocation regression: ',
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


def valid_bitcost_text():
    return '\n'.join((
        'void BitCost::setQP(unsigned int qp)',
        '{',
        '    CalculateLogs();',
        '    if (!s_bitsizes)',
        '        return;',
        '    uint16_t* costs = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1);',
        '    if (!costs)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "BitCost s_costs buffer allocation failure\\n");',
        '        return;',
        '    }',
        '    s_costs[qp] = costs + 2 * BC_MAX_MV;',
        '    uint16_t* fpelMvCosts = X265_MALLOC(uint16_t, BC_MAX_MV + 1);',
        '    if (!fpelMvCosts)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "BitCost s_fpelMvCosts buffer allocation failure\\n");',
        '        return;',
        '    }',
        '    s_fpelMvCosts[qp][j] = fpelMvCosts + (BC_MAX_MV >> 1);',
        '}',
        'void BitCost::CalculateLogs()',
        '{',
        '    float* bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1);',
        '    if (!bitsizes)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "BitCost s_bitsizes buffer allocation failure\\n");',
        '        return;',
        '    }',
        '    s_bitsizes = bitsizes + 2 * BC_MAX_MV;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/bitcost.cpp': valid_bitcost_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/bitcost.cpp': valid_bitcost_text().replace(
                    'uint16_t* costs = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1);\n',
                    's_costs[qp] = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1) + 2 * BC_MAX_MV;\n',
                    1,
                ),
            },
        )
        expect_fail(
            run_checker(root),
            'missing BitCost allocation guardrail: uint16_t* costs = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1);',
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/bitcost.cpp': valid_bitcost_text().replace('if (!s_bitsizes)\n        return;\n', '', 1),
            },
        )
        expect_fail(run_checker(root), 'missing BitCost allocation guardrail: if (!s_bitsizes)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/bitcost.cpp': valid_bitcost_text().replace(
                    'float* bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1);\n',
                    's_bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1) + 2 * BC_MAX_MV;\n',
                    1,
                ),
            },
        )
        expect_fail(
            run_checker(root),
            'missing BitCost allocation guardrail: float* bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1);',
        )

    print('BitCost allocation guard tests passed')


if __name__ == '__main__':
    main()
