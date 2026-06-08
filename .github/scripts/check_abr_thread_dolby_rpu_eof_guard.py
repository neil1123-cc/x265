#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (bDolbyVisionRPU)',
    'auto failDolbyVisionRpu = [&]()',
    'bool closeFailed = std::ferror(m_cliopt.dolbyVisionRpu) != 0;',
    'if (std::fclose(m_cliopt.dolbyVisionRpu))',
    'x265_log(m_param, X265_LOG_WARNING, "Unable to close Dolby Vision RPU stream after read failure in %s\\n",',
    'm_cliopt.dolbyVisionRpu = nullptr;',
    'm_parent->m_clioptArray[m_id].dolbyVisionRpu = nullptr;',
    'if (m_cliopt.rpuParser(&picField1) > 0)',
    'if (m_cliopt.rpuParser(&picField2) > 0)',
    'if (m_cliopt.rpuParser(pic_in[view]) > 0)',
    'if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))',
    'failDolbyVisionRpu();',
    'm_ret = 4;',
    'if (!m_cliopt.dolbyVisionRpu)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing Dolby Vision RPU stream state in %s\\n",',
    'int nextRpuByte = fgetc(m_cliopt.dolbyVisionRpu);',
    'if (nextRpuByte != EOF)',
    'else if (ferror(m_cliopt.dolbyVisionRpu))',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to finalize Dolby Vision RPU stream state in %s\\n",',
    'x265_log(nullptr, X265_LOG_INFO, "VES muxing with Dolby Vision RPU file successful in %s\\n",',
)
FORBIDDEN_SNIPPETS = (
    'if (fgetc(m_cliopt.dolbyVisionRpu) != EOF)',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR Dolby Vision EOF guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR Dolby Vision EOF regression: {snippet}'))

    dolby_pos = text.find('if (bDolbyVisionRPU)')
    field1_pos = text.find('if (m_cliopt.rpuParser(&picField1) > 0)', dolby_pos)
    field1_ret_pos = text.find('m_ret = 4;', field1_pos)
    field2_pos = text.find('if (m_cliopt.rpuParser(&picField2) > 0)', field1_ret_pos)
    field2_ret_pos = text.find('m_ret = 4;', field2_pos)
    view_pos = text.find('if (m_cliopt.rpuParser(pic_in[view]) > 0)', field2_ret_pos)
    view_ret_pos = text.find('m_ret = 4;', view_pos)
    helper_pos = text.find('auto failDolbyVisionRpu = [&]()')
    close_pos = text.find('if (std::fclose(m_cliopt.dolbyVisionRpu))', helper_pos)
    null_pos_helper = text.find('m_cliopt.dolbyVisionRpu = nullptr;', close_pos)
    parent_null_pos = text.find('m_parent->m_clioptArray[m_id].dolbyVisionRpu = nullptr;', null_pos_helper)
    field1_ferror_guard_pos = text.find('if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))', field1_pos)
    field1_fail_pos = text.find('failDolbyVisionRpu();', field1_ferror_guard_pos)
    field2_ferror_guard_pos = text.find('if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))', field2_pos)
    field2_fail_pos = text.find('failDolbyVisionRpu();', field2_ferror_guard_pos)
    view_ferror_guard_pos = text.find('if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))', view_pos)
    view_fail_pos = text.find('failDolbyVisionRpu();', view_ferror_guard_pos)
    null_pos = text.find('if (!m_cliopt.dolbyVisionRpu)', dolby_pos)
    read_pos = text.find('int nextRpuByte = fgetc(m_cliopt.dolbyVisionRpu);', null_pos)
    ferror_pos = text.find('else if (ferror(m_cliopt.dolbyVisionRpu))', read_pos)
    finalize_fail_pos = text.find('failDolbyVisionRpu();', ferror_pos)
    success_pos = text.find('x265_log(nullptr, X265_LOG_INFO, "VES muxing with Dolby Vision RPU file successful in %s\\n",', ferror_pos)
    if -1 in (helper_pos, close_pos, null_pos_helper, parent_null_pos) or not (helper_pos < close_pos < null_pos_helper < parent_null_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must close the Dolby Vision RPU stream before clearing local and parent pointers after read failure'))
    if -1 in (dolby_pos, field1_pos, field1_ferror_guard_pos, field1_fail_pos, field1_ret_pos, field2_pos, field2_ferror_guard_pos, field2_fail_pos, field2_ret_pos, view_pos, view_ferror_guard_pos, view_fail_pos, view_ret_pos, null_pos, read_pos, ferror_pos, finalize_fail_pos, success_pos) or not (dolby_pos < field1_pos < field1_ferror_guard_pos < field1_fail_pos < field1_ret_pos < field2_pos < field2_ferror_guard_pos < field2_fail_pos < field2_ret_pos < view_pos < view_ferror_guard_pos < view_fail_pos < view_ret_pos < null_pos < read_pos < ferror_pos < finalize_fail_pos < success_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must retire the Dolby Vision RPU stream on read failures before propagating parser errors through m_ret'))
    if -1 in (dolby_pos, null_pos, read_pos, ferror_pos, success_pos) or not (dolby_pos < null_pos < read_pos < ferror_pos < success_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must distinguish Dolby Vision EOF from stream errors before success logging'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread Dolby Vision EOF guard')
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

    print('ABR Dolby Vision EOF guard validated')


if __name__ == '__main__':
    main()
