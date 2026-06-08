#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'if (tok && sscanf(tok, "%lf", &value) == 1)',
    'tok = strtok_r(buf, " ,", &toksave);',
)
REQUIRED_SNIPPETS = (
    'bool parseLambdaFile(x265_param* param)',
    'FILE *lfn = x265_fopen(param->rc.lambdaFileName, "r");',
    'char line[2048];',
    'char *tok = nullptr, *buf = nullptr;',
    'char *scan = nullptr;',
    "char *hash = strchr(line, '#');",
    'buf = line;',
    'scan = buf;',
    'tok = nullptr;',
    'while (scan && *scan)',
    "while (*scan == ',' || std::isspace((unsigned char)*scan))",
    'tok = scan;',
    "while (*scan && *scan != ',' && !std::isspace((unsigned char)*scan))",
    'bool bValueError = false;',
    'value = x265_atof(tok, bValueError);',
    'if (!bValueError)',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\\n");',
)
FUNCTION_REGION_START = 'bool parseLambdaFile(x265_param* param)'
FUNCTION_REGION_END = 'bool parseMaskingStrength(x265_param* p, const char* value)'
LINE_SETUP_REGION_START = 'if (!tok)'
LINE_SETUP_REGION_END = 'tok = nullptr;'
TOKEN_REGION_START = 'tok = nullptr;'
TOKEN_REGION_END = 'if (tok)'
VALUE_REGION_START = 'if (tok)'
VALUE_REGION_END = 'while (1);'
OVERSIZE_REGION_START = 'if (t == 2)'
OVERSIZE_REGION_END = 'table[i] = value;'
FINALIZE_REGION_START = 'bool closeFailed = ferror(lfn) != 0;'
FINALIZE_REGION_END = 'return false;'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


def get_last_region(text, start_marker, end_marker):
    start = text.rfind(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end + len(end_marker)]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    function_region = get_region(text, FUNCTION_REGION_START, FUNCTION_REGION_END)
    line_setup_region = get_region(function_region, LINE_SETUP_REGION_START, LINE_SETUP_REGION_END)
    token_region = get_region(function_region, TOKEN_REGION_START, TOKEN_REGION_END)
    value_region = get_region(function_region, VALUE_REGION_START, VALUE_REGION_END)
    oversize_region = get_region(function_region, OVERSIZE_REGION_START, OVERSIZE_REGION_END)
    finalize_region = get_last_region(function_region, FINALIZE_REGION_START, FINALIZE_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in function_region:
            failures.append((TARGET.as_posix(), 0, f'forbidden lambda-file parse regression: {snippet}'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in function_region:
            failures.append((TARGET.as_posix(), 0, f'missing lambda-file parse guardrail: {snippet}'))
    if all(snippet in function_region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            function_region,
            (
                'FILE *lfn = x265_fopen(param->rc.lambdaFileName, "r");',
                'if (!lfn)',
                'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                'return true;',
                'else if (ferror(lfn))',
                'bool closeFailed = ferror(lfn) != 0;',
                'if (fclose(lfn))',
                'closeFailed = true;',
                'if (closeFailed)',
                'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\\n");',
                'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                'char line[2048];',
                'char *tok = nullptr, *buf = nullptr;',
                'char *scan = nullptr;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseLambdaFile must keep the open-failure close/log guard ahead of scanner setup'))
        if not has_in_order(
            line_setup_region,
            (
                'if (!fgets(line, sizeof(line), lfn))',
                'if (ferror(lfn))',
                'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
                'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                'if (t < 2)',
                'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after incomplete parse\\n");',
                'x265_log(param, X265_LOG_ERROR, "lambda file is incomplete\\n");',
                'else',
                'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after truncated parse\\n");',
                'return false;',
                '/* truncate at first hash */',
                "char *hash = strchr(line, '#');",
                'if (hash) *hash = 0;',
                'buf = line;',
                'scan = buf;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseLambdaFile must preserve the reviewed line-fetch close branches before hash truncation and scan initialization'))
        if not has_in_order(
            token_region,
            (
                'tok = nullptr;',
                'while (scan && *scan)',
                "while (*scan == ',' || std::isspace((unsigned char)*scan))",
                'if (!*scan)',
                'scan = nullptr;',
                'tok = scan;',
                "while (*scan && *scan != ',' && !std::isspace((unsigned char)*scan))",
                'if (*scan)',
                "*scan++ = '\\0';",
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseLambdaFile must reinitialize tok and walk delimiter-skipping token boundaries in the reviewed order'))
        if not has_in_order(
            value_region,
            (
                'if (tok)',
                'bool bValueError = false;',
                'value = x265_atof(tok, bValueError);',
                'if (!bValueError)',
                'break;',
                'x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
                'bool closeFailed = ferror(lfn) != 0;',
                'if (fclose(lfn))',
                'closeFailed = true;',
                'if (closeFailed)',
                'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseLambdaFile must parse token text with x265_atof and run the guarded invalid-value close path before returning an error'))
        if not has_in_order(
            oversize_region,
            (
                'if (t == 2)',
                'x265_log(param, X265_LOG_ERROR, "lambda file contains too many values\\n");',
                'bool closeFailed = ferror(lfn) != 0;',
                'if (fclose(lfn))',
                'closeFailed = true;',
                'if (closeFailed)',
                'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\\n");',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseLambdaFile must keep the oversized-table close path ahead of the error return'))
        if not has_in_order(
            finalize_region,
            (
                'bool closeFailed = ferror(lfn) != 0;',
                'if (fclose(lfn))',
                'closeFailed = true;',
                'if (closeFailed)',
                'x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\\n");',
                'return true;',
                'return false;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseLambdaFile must preserve the reviewed final close/finalize ordering before reporting success'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check lambda-file parsing guardrails in param.cpp')
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

    print('Lambda-file parse usage validated')


if __name__ == '__main__':
    main()
