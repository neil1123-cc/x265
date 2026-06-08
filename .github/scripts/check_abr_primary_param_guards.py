#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;',
    'x265_param *primaryParam = primaryPass ? primaryPass->m_param : nullptr;',
    'if (!primaryParam)',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing primary ABR parameters\\n");',
    'm_numInputViews = primaryParam->numViews > 1 ? getConfiguredViewCount(*primaryParam) : 0;',
    'if (!m_param)',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing encoder parameters for encoder %u\\n", m_id);',
    'PassEncoder *srcPass = m_parent->m_passEnc[m_id - 1];',
    'if (!srcPass || !srcPass->m_param)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing scaler source parameters for encoder %u\\n", m_id);',
    'int dstW = srcPass->m_param->sourceWidth;',
    'int dstH = srcPass->m_param->sourceHeight;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR primary/scaler param guardrail: {snippet}'))

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

    abr_init_text = extract_braced_block('void AbrEncoder::encode()')
    pass_init_text = extract_braced_block('int PassEncoder::init(int &result)')

    primary_pass_pos = abr_init_text.find('PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;')
    primary_param_pos = abr_init_text.find('x265_param *primaryParam = primaryPass ? primaryPass->m_param : nullptr;', primary_pass_pos if primary_pass_pos != -1 else 0)
    primary_guard_pos = abr_init_text.find('if (!primaryParam)', primary_param_pos if primary_param_pos != -1 else 0)
    views_pos = abr_init_text.find('m_numInputViews = primaryParam->numViews > 1 ? getConfiguredViewCount(*primaryParam) : 0;', primary_guard_pos if primary_guard_pos != -1 else 0)
    if -1 in (primary_pass_pos, primary_param_pos, primary_guard_pos, views_pos) or not (primary_pass_pos < primary_param_pos < primary_guard_pos < views_pos):
        failures.append((TARGET.as_posix(), 0, 'AbrEncoder::encode must guard primaryParam before deriving m_numInputViews'))

    init_guard_pos = pass_init_text.find('if (!m_param)')
    src_pass_pos = pass_init_text.find('PassEncoder *srcPass = m_parent->m_passEnc[m_id - 1];', init_guard_pos if init_guard_pos != -1 else 0)
    src_guard_pos = pass_init_text.find('if (!srcPass || !srcPass->m_param)', src_pass_pos if src_pass_pos != -1 else 0)
    dst_w_pos = pass_init_text.find('int dstW = srcPass->m_param->sourceWidth;', src_guard_pos if src_guard_pos != -1 else 0)
    dst_h_pos = pass_init_text.find('int dstH = srcPass->m_param->sourceHeight;', dst_w_pos if dst_w_pos != -1 else 0)
    if -1 in (init_guard_pos, src_pass_pos, src_guard_pos, dst_w_pos, dst_h_pos) or not (init_guard_pos < src_pass_pos < src_guard_pos < dst_w_pos < dst_h_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::init must guard scaler source parameters before reading destination dimensions'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR primary/scaler parameter guards')
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

    print('ABR primary/scaler parameter guards validated')


if __name__ == '__main__':
    main()
