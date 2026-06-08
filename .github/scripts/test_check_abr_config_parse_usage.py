#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_config_parse_usage.py')

# Coverage probes used by the scan for ABR config parse guardrails.
NORMALIZED_PROBES = (
    'missing ABR config parse guardrail: validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line))',
    'ABR ladder entry counting must clear EOF state and check fseek() before rewinding the config file',
    'forbidden ABR config parse regression: ',
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': '\n'.join((
                    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
                    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
                    'static inline bool validateConfigFileLine(FILE* file, const char* context, int lineNumber, const char* line, size_t lineCapacity)',
                    'static inline bool hasCliExitRequest(int argc, char** argv)',
                    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
                    'x265_log(nullptr, X265_LOG_ERROR, "%s at line %d cannot request CLI help or version output\\n", context, lineNumber);',
                )) + '\n',
                'source/x265.cpp': '\n'.join((
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
                    'validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line))',
                    'numEncodes++;',
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
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': '\n'.join((
                    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
                    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
                )) + '\n',
                'source/x265.cpp': 'char *header = std::strtok(argLine, "[]");\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ABR config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': '\n'.join((
                    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
                    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
                    'static inline bool hasCliExitRequest(int argc, char** argv)',
                    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
                    'x265_log(nullptr, X265_LOG_ERROR, "%s at line %d cannot request CLI help or version output\\n", context, lineNumber);',
                )) + '\n',
                'source/x265.cpp': '\n'.join((
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
                    'if (!measureAbrConfigArgs(start, extraArgc, strPoolSize, lineNumber))',
                    'if (!copyAbrConfigArgs(start, argv, extraArgc + 2, strPool, strPoolSize, argc, lineNumber))',
                    'if (rejectCliExitRequest(argc, argv, "ABR CLI arguments", lineNumber))',
                    'if (stagedCliopt[i].parse(argc++, argv))',
                    'if (stagedCliopt[i].parseExitCode >= 0)',
                    'x265_log(nullptr, X265_LOG_ERROR, "ABR CLI arguments at line %d cannot trigger CLI exit handling\\n", lineNumber);',
                    '{',
                    '    return failAbrConfigParse(stagedCliopt, i + 1);',
                    '    std::exit(1);',
                    '}',
                    'std::swap(cliopt[i], stagedCliopt[i]);',
                    'struct AbrRefContextState',
                    'AbrRefContextState* stagedState = new AbrRefContextState[numEncodes];',
                    'stagedState[curEnc].refId = refEnc;',
                    'stagedState[refEnc].numRefs++;',
                    'stagedState[refEnc].saveLevel = X265_MAX(stagedState[refEnc].saveLevel, cliopt[curEnc].loadLevel);',
                )) + '\n',
            },
        )
        result = run_checker(root)
        if result.returncode == 0:
            raise AssertionError('expected failure for internal ABR parse exit regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': '\n'.join((
                    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
                    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
                    'static inline bool validateConfigFileLine(FILE* file, const char* context, int lineNumber, const char* line, size_t lineCapacity)',
                    'static inline bool hasCliExitRequest(int argc, char** argv)',
                    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
                    'x265_log(nullptr, X265_LOG_ERROR, "%s at line %d cannot request CLI help or version output\\n", context, lineNumber);',
                )) + '\n',
                'source/x265.cpp': '\n'.join((
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
                    'validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line))',
                    'numEncodes++;',
                    'std::rewind(abrConfig);',
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
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR config parse guardrail: clearerr(abrConfig);')

    print('ABR config parse guard tests passed')


if __name__ == '__main__':
    main()
