#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
HEADER = Path('source/abrEncApp.h')
REQUIRED_CPP_SNIPPETS = (
    'm_numActiveEncodes.set(0);',
    'if (!m_passEnc[pass])',
    'if (m_passEnc[pass]->m_ret)',
    'if (usesAbrScalerMode(m_passEnc[pass]->m_cliopt, pass))',
    'PassEncoder *srcPass = m_passEnc[pass - 1];',
    'm_numActiveEncodes.decr();',
    'if (!m_passEnc[pass]->m_ret && !m_passEnc[pass]->startThreads() && !ret)',
    'auto handleInputWorkerStartFailure = [&](const char* threadName, std::atomic<bool>& workerActive)',
    'if (!start())',
    'm_inputOver.store(true);',
    'm_parent->m_numActiveEncodes.decr();',
    'm_parent->m_picWriteCnt[m_id].poke();',
    'return false;',
)
REQUIRED_H_SNIPPETS = (
    'bool startThreads();',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    cpp_path = repo_root / TARGET
    if not cpp_path.is_file():
        failures.append((TARGET.as_posix(), 0, 'missing file'))
    else:
        text = cpp_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in REQUIRED_CPP_SNIPPETS:
            if snippet not in text:
                failures.append((TARGET.as_posix(), 0, f'missing ABR startThreads failure propagation guardrail: {snippet}'))

        alloc_fail_pos = text.find('if (!allocBuffers())')
        alloc_set_pos = text.find('m_numActiveEncodes.set(0);', alloc_fail_pos if alloc_fail_pos != -1 else 0)
        alloc_ret_pos = text.find('ret = 4;', alloc_set_pos if alloc_set_pos != -1 else 0)
        alloc_return_pos = text.find('return;', alloc_ret_pos if alloc_ret_pos != -1 else 0)
        if -1 in (alloc_fail_pos, alloc_set_pos, alloc_ret_pos, alloc_return_pos) or not (alloc_fail_pos < alloc_set_pos < alloc_ret_pos < alloc_return_pos):
            failures.append((TARGET.as_posix(), 0, 'AbrEncoder ctor must zero active encode count and return immediately after allocBuffers() failure'))

        start_loop_guard_pos = text.find('if (!m_passEnc[pass])')
        start_loop_ret_guard_pos = text.find('if (m_passEnc[pass]->m_ret)', start_loop_guard_pos if start_loop_guard_pos != -1 else 0)
        start_loop_dep_guard_pos = text.find('if (usesAbrScalerMode(m_passEnc[pass]->m_cliopt, pass))', start_loop_ret_guard_pos if start_loop_ret_guard_pos != -1 else 0)
        start_loop_call_pos = text.find('if (!m_passEnc[pass]->m_ret && !m_passEnc[pass]->startThreads() && !ret)', start_loop_dep_guard_pos if start_loop_dep_guard_pos != -1 else 0)
        if -1 in (start_loop_guard_pos, start_loop_ret_guard_pos, start_loop_dep_guard_pos, start_loop_call_pos) or not (start_loop_guard_pos < start_loop_ret_guard_pos < start_loop_dep_guard_pos < start_loop_call_pos):
            failures.append((TARGET.as_posix(), 0, 'AbrEncoder ctor must guard missing/failed dependency passes before starting later ABR threads'))

        pass_start_pos = text.find('if (!start())')
        pass_decr_pos = text.find('m_parent->m_numActiveEncodes.decr();', pass_start_pos if pass_start_pos != -1 else 0)
        reader_start_pos = text.find('if (!m_reader->start())', pass_decr_pos if pass_decr_pos != -1 else 0)
        scaler_start_pos = text.find('if (!m_scaler->start())', reader_start_pos if reader_start_pos != -1 else 0)
        if -1 in (pass_start_pos, pass_decr_pos, reader_start_pos, scaler_start_pos) or not (pass_start_pos < pass_decr_pos < reader_start_pos < scaler_start_pos):
            failures.append((TARGET.as_posix(), 0, 'PassEncoder::startThreads must handle pass, reader, and scaler start failures in order'))

    header_path = repo_root / HEADER
    if not header_path.is_file():
        failures.append((HEADER.as_posix(), 0, 'missing file'))
    else:
        header_text = header_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in REQUIRED_H_SNIPPETS:
            if snippet not in header_text:
                failures.append((HEADER.as_posix(), 0, f'missing ABR startThreads declaration guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR startThreads failure propagation guardrails')
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

    print('ABR startThreads failure propagation validated')


if __name__ == '__main__':
    main()
