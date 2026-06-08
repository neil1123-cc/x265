#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265.cpp')
SHARED_TARGET = Path('source/x265cli.h')
FORBIDDEN_SNIPPETS = (
    'char *header = std::strtok(argLine, "[]");',
    'char *id = std::strtok(header, ":");',
    'char* token = std::strtok(start, " ");',
    'token = std::strtok(nullptr, " ");',
    'if (stagedCliopt[i].parse(argc++, argv))\n        {\n            destroyCliOptionsArray(stagedCliopt, i + 1);\n            delete[] stagedCliopt;\n            std::exit(1);\n        }',
)
REQUIRED_SNIPPETS = (
    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
    'static inline bool validateConfigFileLine(FILE* file, const char* context, int lineNumber, const char* line, size_t lineCapacity)',
    'static inline bool hasCliExitRequest(int argc, char** argv)',
    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
    'x265_log(nullptr, X265_LOG_ERROR, "%s at line %d cannot request CLI help or version output\\n", context, lineNumber);',
    'static bool parseAbrHeader(char* header, char** head, int lineNumber)',
    'char* headerEnd = std::strchr(header, \']\');',
    'static bool measureAbrConfigArgs(const char* start, int& extraArgc, size_t& strPoolSize, int lineNumber)',
    'return walkConfigTokens(start,',
    'static bool copyAbrConfigArgs(char* start, char** argv, int maxArgs, char* strPool, size_t strPoolSize, int& argc, int lineNumber)',
    'static void destroyCliOptionsArray(CLIOptions cliopt[], uint32_t count)',
    'static bool failAbrConfigParse(CLIOptions stagedCliopt[], uint32_t count)',
    'destroyCliOptionsArray(stagedCliopt, count);',
    'delete[] stagedCliopt;',
    'CLIOptions* stagedCliopt = new CLIOptions[numEncodes];',
    'stagedCliopt[i].encId = i;',
    'stagedCliopt[i].isAbrLadderConfig = true;',
    'if (!parseAbrHeader(argLine, head, lineNumber))',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing ABR CLI arguments at line %d\\n", lineNumber);',
    'return failAbrConfigParse(stagedCliopt, i + 1);',
    'delete[] stagedCliopt;',
    'if (!measureAbrConfigArgs(start, extraArgc, strPoolSize, lineNumber))',
    'if (!copyAbrConfigArgs(start, argv, extraArgc + 2, strPool, strPoolSize, argc, lineNumber))',
    'validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line))',
    'clearerr(abrConfig);',
    'if (std::fseek(abrConfig, 0, SEEK_SET))',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to rewind ABR ladder config\\n");',
    'if (rejectCliExitRequest(argc, argv, "ABR CLI arguments", lineNumber))',
    'if (stagedCliopt[i].parse(argc++, argv))',
    'if (stagedCliopt[i].parseExitCode >= 0)',
    'x265_log(nullptr, X265_LOG_ERROR, "ABR CLI arguments at line %d cannot trigger CLI exit handling\\n", lineNumber);',
    'return false;',
    'std::swap(cliopt[i], stagedCliopt[i]);',
    'struct AbrRefContextState',
    'AbrRefContextState* stagedState = new AbrRefContextState[numEncodes];',
    'stagedState[curEnc].refId = refEnc;',
    'stagedState[refEnc].numRefs++;',
    'stagedState[refEnc].saveLevel = X265_MAX(stagedState[refEnc].saveLevel, cliopt[curEnc].loadLevel);',
)
FORBIDDEN_SNIPPETS += (
    'cliopt[i].encId = i;',
    'cliopt[i].isAbrLadderConfig = true;',
    'if (cliopt[i].parse(argc++, argv))',
    'cliopt[curEnc].refId = refEnc;',
    'cliopt[refEnc].numRefs++;',
    'cliopt[refEnc].saveLevel = X265_MAX(cliopt[refEnc].saveLevel, cliopt[curEnc].loadLevel);',
)


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
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR config parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text and snippet not in shared_text:
            target = SHARED_TARGET.as_posix() if 'walkConfigTokens' in snippet or snippet.startswith('template <typename Char') else TARGET.as_posix()
            failures.append((target, 0, f'missing ABR config parse guardrail: {snippet}'))
    if text.count('validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line))') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing ABR config parse guardrail: validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line))'))

    count_pos = text.find('numEncodes++;')
    clearerr_pos = text.find('clearerr(abrConfig);', count_pos if count_pos != -1 else 0)
    rewind_pos = text.find('if (std::fseek(abrConfig, 0, SEEK_SET))', clearerr_pos if clearerr_pos != -1 else 0)
    rewind_log_pos = text.find('x265_log(nullptr, X265_LOG_ERROR, "Unable to rewind ABR ladder config\\n");', rewind_pos if rewind_pos != -1 else 0)
    if -1 in (count_pos, clearerr_pos, rewind_pos, rewind_log_pos) or not (
        count_pos < clearerr_pos < rewind_pos < rewind_log_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'ABR ladder entry counting must clear EOF state and check fseek() before rewinding the config file'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed ABR config parsing guardrails in x265.cpp')
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

    print('ABR config parse usage validated')


if __name__ == '__main__':
    main()
