#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/bitcost.cpp')
REQUIRED_SNIPPETS = (
    'CalculateLogs();',
    'if (!s_bitsizes)',
    'uint16_t* costs = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1);',
    'if (!costs)',
    'x265_log(nullptr, X265_LOG_ERROR, "BitCost s_costs buffer allocation failure\\n");',
    's_costs[qp] = costs + 2 * BC_MAX_MV;',
    'uint16_t* fpelMvCosts = X265_MALLOC(uint16_t, BC_MAX_MV + 1);',
    'if (!fpelMvCosts)',
    'x265_log(nullptr, X265_LOG_ERROR, "BitCost s_fpelMvCosts buffer allocation failure\\n");',
    's_fpelMvCosts[qp][j] = fpelMvCosts + (BC_MAX_MV >> 1);',
    'float* bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1);',
    'if (!bitsizes)',
    'x265_log(nullptr, X265_LOG_ERROR, "BitCost s_bitsizes buffer allocation failure\\n");',
    's_bitsizes = bitsizes + 2 * BC_MAX_MV;',
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
            failures.append((TARGET.as_posix(), 0, f'missing BitCost allocation guardrail: {snippet}'))

    setqp_pos = text.find('void BitCost::setQP(unsigned int qp)')
    calc_logs_pos = text.find('CalculateLogs();', setqp_pos if setqp_pos != -1 else 0)
    bits_guard_pos = text.find('if (!s_bitsizes)', calc_logs_pos if calc_logs_pos != -1 else 0)
    costs_alloc_pos = text.find('uint16_t* costs = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1);', bits_guard_pos if bits_guard_pos != -1 else 0)
    costs_guard_pos = text.find('if (!costs)', costs_alloc_pos if costs_alloc_pos != -1 else 0)
    costs_assign_pos = text.find('s_costs[qp] = costs + 2 * BC_MAX_MV;', costs_guard_pos if costs_guard_pos != -1 else 0)
    fpel_alloc_pos = text.find('uint16_t* fpelMvCosts = X265_MALLOC(uint16_t, BC_MAX_MV + 1);', costs_assign_pos if costs_assign_pos != -1 else 0)
    fpel_guard_pos = text.find('if (!fpelMvCosts)', fpel_alloc_pos if fpel_alloc_pos != -1 else 0)
    fpel_assign_pos = text.find('s_fpelMvCosts[qp][j] = fpelMvCosts + (BC_MAX_MV >> 1);', fpel_guard_pos if fpel_guard_pos != -1 else 0)

    calc_fn_pos = text.find('void BitCost::CalculateLogs()')
    bits_alloc_pos = text.find('float* bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1);', calc_fn_pos if calc_fn_pos != -1 else 0)
    bits_alloc_guard_pos = text.find('if (!bitsizes)', bits_alloc_pos if bits_alloc_pos != -1 else 0)
    bits_assign_pos = text.find('s_bitsizes = bitsizes + 2 * BC_MAX_MV;', bits_alloc_guard_pos if bits_alloc_guard_pos != -1 else 0)

    if -1 in (
        setqp_pos,
        calc_logs_pos,
        bits_guard_pos,
        costs_alloc_pos,
        costs_guard_pos,
        costs_assign_pos,
        fpel_alloc_pos,
        fpel_guard_pos,
        fpel_assign_pos,
        calc_fn_pos,
        bits_alloc_pos,
        bits_alloc_guard_pos,
        bits_assign_pos,
    ) or not (
        setqp_pos < calc_logs_pos < bits_guard_pos < costs_alloc_pos < costs_guard_pos < costs_assign_pos < fpel_alloc_pos < fpel_guard_pos < fpel_assign_pos and
        calc_fn_pos < bits_alloc_pos < bits_alloc_guard_pos < bits_assign_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'BitCost must guard log-table and MV-cost allocations before pointer offsetting or dereference'))

    forbidden_snippets = (
        's_costs[qp] = X265_MALLOC(uint16_t, 4 * BC_MAX_MV + 1) + 2 * BC_MAX_MV;',
        's_fpelMvCosts[qp][j] = X265_MALLOC(uint16_t, BC_MAX_MV + 1) + (BC_MAX_MV >> 1);',
        's_bitsizes = X265_MALLOC(float, 4 * BC_MAX_MV + 1) + 2 * BC_MAX_MV;',
    )
    for snippet in forbidden_snippets:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden BitCost allocation regression: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check BitCost allocation guardrails')
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

    print('BitCost allocation guards validated')


if __name__ == '__main__':
    main()
