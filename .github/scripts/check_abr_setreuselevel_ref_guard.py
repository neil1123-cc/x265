#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
BRANCH = 'if (m_cliopt.loadLevel)'
REQUIRED_SNIPPETS = (
    'if (m_parent->m_numEncodes > 1)',
    'setReuseLevel();',
    'if (m_ret)',
    'if (!result)',
    'result = m_ret;',
    'return -1;',
    BRANCH,
    'PassEncoder *refPass = m_parent->m_passEnc[m_cliopt.refId];',
    'if (!refPass || !refPass->m_param)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing reference analysis parameters for encoder %u\\n", m_id);',
    'm_ret = 4;',
    'x265_param *refParam = refPass->m_param;',
    'else if (srcH > 0 && srcW > 0)',
    'double scaleFactorH = double(m_param->sourceHeight) / srcH;',
    'double scaleFactorW = double(m_param->sourceWidth) / srcW;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR setReuseLevel ref guardrail: {snippet}'))

    def extract_braced_block(signature):
        start = text.find(signature)
        if start == -1:
            return text
        brace_start = text.find('{', start)
        if brace_start == -1:
            return text[start:]
        depth = 0
        for idx in range(brace_start, len(text)):
            char = text[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        return text[start:]

    init_text = extract_braced_block('int PassEncoder::init(int &result)')
    set_reuse_text = extract_braced_block('void PassEncoder::setReuseLevel()')

    branch_pos = set_reuse_text.find(BRANCH)
    ref_pass_pos = set_reuse_text.find('PassEncoder *refPass = m_parent->m_passEnc[m_cliopt.refId];', branch_pos if branch_pos != -1 else 0)
    guard_pos = set_reuse_text.find('if (!refPass || !refPass->m_param)', ref_pass_pos if ref_pass_pos != -1 else 0)
    ret_pos = set_reuse_text.find('m_ret = 4;', guard_pos if guard_pos != -1 else 0)
    ref_param_pos = set_reuse_text.find('x265_param *refParam = refPass->m_param;', ret_pos if ret_pos != -1 else 0)
    src_guard_pos = set_reuse_text.find('else if (srcH > 0 && srcW > 0)', ref_param_pos if ref_param_pos != -1 else 0)
    scale_h_pos = set_reuse_text.find('double scaleFactorH = double(m_param->sourceHeight) / srcH;', src_guard_pos if src_guard_pos != -1 else 0)
    scale_w_pos = set_reuse_text.find('double scaleFactorW = double(m_param->sourceWidth) / srcW;', scale_h_pos if scale_h_pos != -1 else 0)
    if -1 in (branch_pos, ref_pass_pos, guard_pos, ret_pos, ref_param_pos, src_guard_pos, scale_h_pos, scale_w_pos) or not (branch_pos < ref_pass_pos < guard_pos < ret_pos < ref_param_pos < src_guard_pos < scale_h_pos < scale_w_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::setReuseLevel must guard refPass/refParam and positive scaled dimensions before reuse math'))

    init_guard_pos = init_text.find('if (m_parent->m_numEncodes > 1)')
    init_call_pos = init_text.find('setReuseLevel();', init_guard_pos if init_guard_pos >= 0 else 0)
    init_ret_guard_pos = init_text.find('if (m_ret)', init_call_pos if init_call_pos >= 0 else 0)
    result_guard_pos = init_text.find('if (!result)', init_ret_guard_pos if init_ret_guard_pos >= 0 else 0)
    result_assign_pos = init_text.find('result = m_ret;', result_guard_pos if result_guard_pos >= 0 else 0)
    init_return_pos = init_text.find('return -1;', result_assign_pos if result_assign_pos >= 0 else 0)
    if -1 in (init_guard_pos, init_call_pos, init_ret_guard_pos, result_guard_pos, result_assign_pos, init_return_pos) or not (init_guard_pos < init_call_pos < init_ret_guard_pos < result_guard_pos < result_assign_pos < init_return_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::init must stop immediately when setReuseLevel reports failure'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::setReuseLevel reference guards')
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

    print('ABR setReuseLevel reference guards validated')


if __name__ == '__main__':
    main()
