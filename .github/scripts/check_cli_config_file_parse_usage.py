#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
SHARED_TARGET = Path('source/x265cli.h')
SHARED_REQUIRED_SNIPPETS = (
    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
    'Char* cursor = start;',
    'Char* next = cursor;',
    'bool endedOnWhitespace = *cursor && std::isspace((unsigned char)*cursor);',
    'if (endedOnWhitespace)',
    'next++;',
    'while (*next && std::isspace((unsigned char)*next))',
    'start = next;',
)
TOKENIZE_REQUIRED_SNIPPETS = (
    'static bool tokenizeConfigFileArgs(char* start, char** args, int maxArgs, int& argCount, const char* context)',
    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
    'if (argCount + 1 >= maxArgs)',
    'return walkConfigTokens(start,',
    'x265_log(nullptr, X265_LOG_ERROR, "%s has an unterminated quoted argument\\n", context);',
    'x265_log(nullptr, X265_LOG_ERROR, "%s has an empty argument\\n", context);',
    '}) && (args[argCount] = nullptr, true);',
    'args[argCount++] = (char*)"x265";',
    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
    "token[tokenLength] = '\\0';",
    'argCount++;',
    'args[argCount] = token;',
)
ZONE_REQUIRED_SNIPPETS = (
    'while (std::isspace((unsigned char)*entry)) entry++;',
    "if (!((*entry == '#') || (*entry == '\\0') || (std::strcmp(entry, \"\\r\\n\") == 0) || (std::strcmp(entry, \"\\n\") == 0)))",
    "if (*entry == '#' || *entry == '\\0' || (std::strcmp(entry, \"\\r\\n\") == 0) || (std::strcmp(entry, \"\\n\") == 0))",
    'char* start = argLine;',
    'if (!*start)',
    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
)
SCENECUT_REQUIRED_SNIPPETS = (
    'char* start = std::strchr(argLine, \'-\');',
    'if (!start)',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
)
MULTIVIEW_REQUIRED_SNIPPETS = (
    'char* start = std::strchr(argLine, \'-\');',
    'if (!start)',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
    'args[argCount++] = (char*)"x265";',
    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
    'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
)
FORBIDDEN_SNIPPETS = (
    'char* token = std::strtok(start, " \\t");',
    'token = std::strtok(nullptr, " \\t");',
    'token = std::strtok(token, "\\"");',
    'while (*start)\n        {\n            if (*start == \'#\')\n                break;\n\n            Char* tokenStart = start;',
    '*write = \'\\0\';\n            args[argCount++] = token;\n\n            while (std::isspace((unsigned char)*start))\n                start++;',
    'if (write == token)\n            {\n                return false;\n            }',
    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Zone file entry"))',
    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Scenecut-aware QP config"))',
)
SHARED_REGION_START = 'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>'
SHARED_REGION_END = 'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)'
TOKENIZE_REGION_START = 'static bool tokenizeConfigFileArgs(char* start, char** args, int maxArgs, int& argCount, const char* context)'
TOKENIZE_REGION_END = 'static bool rewindConfigFile(FILE* configFile, const char* context)'
ZONE_REGION_START = 'bool CLIOptions::parseZoneFile()'
ZONE_REGION_END = 'bool CLIOptions::parseScenecutAwareQpConfig()'
SCENECUT_REGION_START = 'bool CLIOptions::parseScenecutAwareQpConfig()'
SCENECUT_REGION_END = 'bool CLIOptions::parseMultiViewConfig(char** fn)'
MULTIVIEW_REGION_START = 'bool CLIOptions::parseMultiViewConfig(char** fn)'
MULTIVIEW_REGION_END = '#ifdef __cplusplus'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


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
    shared_path = repo_root / SHARED_TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]
    if not shared_path.is_file():
        return [(SHARED_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    shared_text = shared_path.read_text(encoding='utf-8', errors='ignore')
    shared_region = get_region(shared_text, SHARED_REGION_START, SHARED_REGION_END)
    tokenize_region = get_region(text, TOKENIZE_REGION_START, TOKENIZE_REGION_END)
    zone_region = get_region(text, ZONE_REGION_START, ZONE_REGION_END)
    scenecut_region = get_region(text, SCENECUT_REGION_START, SCENECUT_REGION_END)
    multiview_region = get_region(text, MULTIVIEW_REGION_START, MULTIVIEW_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in shared_text:
            failures.append((SHARED_TARGET.as_posix(), 0, f'forbidden CLI config parse regression: {snippet}'))
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden CLI config parse regression: {snippet}'))
    for snippet in SHARED_REQUIRED_SNIPPETS:
        if snippet not in shared_region:
            failures.append((SHARED_TARGET.as_posix(), 0, f'missing CLI config parse guardrail: {snippet}'))
    for snippet in TOKENIZE_REQUIRED_SNIPPETS:
        if snippet not in tokenize_region:
            failures.append((TARGET.as_posix(), 0, f'missing CLI config parse guardrail: {snippet}'))
    for snippet in ZONE_REQUIRED_SNIPPETS:
        if snippet not in zone_region:
            failures.append((TARGET.as_posix(), 0, f'missing CLI config parse guardrail: {snippet}'))
    for snippet in SCENECUT_REQUIRED_SNIPPETS:
        if snippet not in scenecut_region:
            failures.append((TARGET.as_posix(), 0, f'missing CLI config parse guardrail: {snippet}'))
    for snippet in MULTIVIEW_REQUIRED_SNIPPETS:
        if snippet not in multiview_region:
            failures.append((TARGET.as_posix(), 0, f'missing CLI config parse guardrail: {snippet}'))
    if all(snippet in shared_region for snippet in SHARED_REQUIRED_SNIPPETS):
        if not has_in_order(
            shared_region,
            (
                'Char* cursor = start;',
                'while (*cursor)',
                'Char* next = cursor;',
                'bool endedOnWhitespace = *cursor && std::isspace((unsigned char)*cursor);',
                'if (endedOnWhitespace)',
                'next++;',
                'while (*next && std::isspace((unsigned char)*next))',
                'start = next;',
            ),
        ):
            failures.append((SHARED_TARGET.as_posix(), 0, 'walkConfigTokens must consume each token, preserve quoted content, and only advance past trailing whitespace after endToken succeeds'))
    if all(snippet in tokenize_region for snippet in TOKENIZE_REQUIRED_SNIPPETS):
        if not has_in_order(
            tokenize_region,
            (
                'return walkConfigTokens(start,',
                'if (argCount + 1 >= maxArgs)',
                'args[argCount] = token;',
                "token[tokenLength] = '\\0';",
                'argCount++;',
                '}) && (args[argCount] = nullptr, true);',
                'args[argCount++] = (char*)"x265";',
                'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                '!rejectCliExitRequest(argCount, args, context, lineNumber);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Config sub-parse argument preparation must tokenize into bounded argv storage, null-terminate it, then prepend the dummy x265 argv[0] before exit-option rejection'))
    if all(snippet in zone_region for snippet in ZONE_REQUIRED_SNIPPETS):
        if not has_in_order(
            zone_region,
            (
                'while (std::isspace((unsigned char)*entry)) entry++;',
                "if (!((*entry == '#') || (*entry == '\\0') || (std::strcmp(entry, \"\\r\\n\") == 0) || (std::strcmp(entry, \"\\n\") == 0)))",
                'char* start = argLine;',
                'if (!*start)',
                'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Zone file parsing must skip blank/comment lines, split the start-frame token first, and only then sub-parse the remaining CLI-style arguments'))
    if all(snippet in scenecut_region for snippet in SCENECUT_REQUIRED_SNIPPETS):
        if not has_in_order(
            scenecut_region,
            (
                'char* start = std::strchr(argLine, \'-\');',
                'if (!start)',
                'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
                'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Scenecut-aware QP config parsing must find the first CLI option token before tokenization and preserve the dedicated missing/invalid diagnostics'))
    if all(snippet in multiview_region for snippet in MULTIVIEW_REQUIRED_SNIPPETS):
        if not has_in_order(
            multiview_region,
            (
                'char* start = std::strchr(argLine, \'-\');',
                'if (!start)',
                'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
                'args[argCount++] = (char*)"x265";',
                'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
                'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))',
                'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Multiview config parsing must stage argv[0], tokenize the option payload, reject exit requests, and only then emit the invalid-config diagnostic'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI config-file parsing guardrails in x265cli.cpp')
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

    print('CLI config-file parse usage validated')


if __name__ == '__main__':
    main()
