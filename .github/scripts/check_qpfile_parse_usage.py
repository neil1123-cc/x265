#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
FORBIDDEN_SNIPPETS = (
    'ret = fscanf(qpfile, "%d %c%*[ \\t]%d\\n", &num, &type, &qp);',
    'int ret = std::sscanf(line, "%d %c %d%n", &num, &type, &qp, &consumed);',
)
REQUIRED_SNIPPETS = (
    'static bool parseCliInt32Token(const char* token, int32_t& value)',
    'static bool parseQpFileLine(char* line, int32_t& num, char& type, int32_t& qp)',
    'static bool isQpFileSkippableLine(const char* line)',
    'validateConfigFileLine(qpfile, "QP file", 0, line, sizeof(line))',
    'char* frameToken = scan;',
    'char parsedType = *scan++;',
    'if (!parseCliInt32Token(frameToken, parsedNum))',
    'if (!parseCliInt32Token(qpToken, parsedQp))',
    "if (*scan == '#')",
    'num = parsedNum;',
    'type = parsedType;',
    'qp = parsedQp;',
    'if (filePos < 0)',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to query qpfile position before parsing frame %d\\n", pic_org.poc);',
    'if (!std::fgets(line, sizeof(line), qpfile))',
    'if (isQpFileSkippableLine(line))',
    'bool hasValidLine = parseQpFileLine(line, num, type, qp);',
    'if (num > pic_org.poc || !hasValidLine)',
    'if (std::fseek(qpfile, filePos, SEEK_SET))',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to restore qpfile position for frame %d\\n", pic_org.poc);',
    'if (qp < -1 || qp > QP_MAX_MAX)',
    'int nextForceQp = 0;',
    'int nextSliceType = X265_TYPE_AUTO;',
    'pic_org.forceqp = nextForceQp;',
    'pic_org.sliceType = nextSliceType;',
)
FORBIDDEN_SNIPPETS += (
    'type = *scan++;',
    'num = x265_atoi(frameToken, bError);',
    'qp = x265_atoi(qpToken, bError);',
    'std::fseek(qpfile, filePos, SEEK_SET);',
    'if (qp >= 0)\n                pic_org.forceqp = qp + 1;',
    'if (qp < -1 || qp > 51)',
    "if (type == 'I') pic_org.sliceType = X265_TYPE_IDR;",
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden qpfile parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing qpfile parse guardrail: {snippet}'))

    ftell_pos = text.find('filePos = std::ftell(qpfile);')
    ftell_guard_pos = text.find('if (filePos < 0)', ftell_pos if ftell_pos != -1 else 0)
    ftell_log_pos = text.find('x265_log(nullptr, X265_LOG_ERROR, "Unable to query qpfile position before parsing frame %d\\n", pic_org.poc);', ftell_guard_pos if ftell_guard_pos != -1 else 0)
    fgets_pos = text.find('if (!std::fgets(line, sizeof(line), qpfile))', ftell_log_pos if ftell_log_pos != -1 else 0)
    parse_pos = text.find('bool hasValidLine = parseQpFileLine(line, num, type, qp);', fgets_pos if fgets_pos != -1 else 0)
    rewind_guard_pos = text.find('if (num > pic_org.poc || !hasValidLine)', parse_pos if parse_pos != -1 else 0)
    rewind_seek_pos = text.find('if (std::fseek(qpfile, filePos, SEEK_SET))', rewind_guard_pos if rewind_guard_pos != -1 else 0)
    rewind_log_pos = text.find('x265_log(nullptr, X265_LOG_ERROR, "Unable to restore qpfile position for frame %d\\n", pic_org.poc);', rewind_seek_pos if rewind_seek_pos != -1 else 0)
    rewind_return_pos = text.find('return false;', rewind_log_pos if rewind_log_pos != -1 else 0)
    rewind_break_pos = text.find('break;', rewind_return_pos if rewind_return_pos != -1 else 0)
    if -1 in (
        ftell_pos,
        ftell_guard_pos,
        ftell_log_pos,
        fgets_pos,
        parse_pos,
        rewind_guard_pos,
        rewind_seek_pos,
        rewind_log_pos,
        rewind_return_pos,
        rewind_break_pos,
    ) or not (
        ftell_pos < ftell_guard_pos < ftell_log_pos < fgets_pos < parse_pos < rewind_guard_pos <
        rewind_seek_pos < rewind_log_pos < rewind_return_pos < rewind_break_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'qpfile parsing must fail fast when ftell/fseek cannot preserve parser position'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check qpfile parsing guardrails in x265cli.cpp')
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

    print('QPFile parse usage validated')


if __name__ == '__main__':
    main()
