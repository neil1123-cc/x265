/*****************************************************************************
 * Copyright (C) 2013-2020 MulticoreWare, Inc
 *
 * Authors: Steve Borho <steve@borho.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02111, USA.
 *
 * This program is also available under a commercial proprietary license.
 * For more information, contact us at license @ x265.com.
 *****************************************************************************/

#if _MSC_VER
#pragma warning(disable: 4127) // conditional expression is constant, yes I know
#endif

#include "x265.h"
#include "x265cli.h"
#include "abrEncApp.h"
#include "param.h"

#if HAVE_VLD
/* Visual Leak Detector */
#include <vld.h>
#endif

#include <csignal>
#include <cerrno>
#include <utility>
#include <fcntl.h>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <string>
#include <ostream>
#include <fstream>
#include <queue>

using namespace X265_NS;

#define X265_HEAD_ENTRIES 3
#define CONSOLE_TITLE_SIZE 200

#ifdef _WIN32
#define strdup _strdup
static char orgConsoleTitle[CONSOLE_TITLE_SIZE] = "";
#endif

#ifdef _WIN32
/* Copy of x264 code, which allows for Unicode characters in the command line.
 * Retrieve command line arguments as UTF-8. */
static int get_argv_utf8(int *argc_ptr, char ***argv_ptr)
{
    int ret = 0;
    wchar_t **argv_utf16 = CommandLineToArgvW(GetCommandLineW(), argc_ptr);
    if (argv_utf16)
    {
        int argc = *argc_ptr;
        int offset = (argc + 1) * sizeof(char*);
        int size = offset;

        for (int i = 0; i < argc; i++)
            size += WideCharToMultiByte(CP_UTF8, 0, argv_utf16[i], -1, nullptr, 0, nullptr, nullptr);

        char **argv = *argv_ptr = (char**)std::malloc(size);
        if (argv)
        {
            for (int i = 0; i < argc; i++)
            {
                argv[i] = (char*)argv + offset;
                offset += WideCharToMultiByte(CP_UTF8, 0, argv_utf16[i], -1, argv[i], size - offset, nullptr, nullptr);
            }
            argv[argc] = nullptr;
            ret = 1;
        }
        LocalFree(argv_utf16);
    }
    return ret;
}
#endif

/* Checks for abr-ladder config file in the command line.
 * Returns true if abr-config file is present. Returns 
 * false otherwise */

static bool checkAbrLadder(int argc, char **argv, FILE **abrConfig)
{
    for (optind = 0;;)
    {
        int long_options_index = -1;
        int c = getopt_long(argc, argv, short_options, long_options, &long_options_index);
        if (c == -1)
            break;
        if (long_options_index < 0 && c > 0)
        {
            for (size_t i = 0; i < sizeof(long_options) / sizeof(long_options[0]); i++)
            {
                if (long_options[i].val == c)
                {
                    long_options_index = (int)i;
                    break;
                }
            }

            if (long_options_index < 0)
            {
                /* getopt_long might have already printed an error message */
                if (c != 63)
                    x265_log(nullptr, X265_LOG_WARNING, "internal error: short option '%c' has no long option\n", c);
                return false;
            }
        }
        if (long_options_index < 0)
        {
            x265_log(nullptr, X265_LOG_WARNING, "short option '%c' unrecognized\n", c);
            return false;
        }
        if (!std::strcmp(long_options[long_options_index].name, "abr-ladder"))
        {
            *abrConfig = x265_fopen(optarg, "rb");
            if (!*abrConfig)
            {
                x265_log_file(nullptr, X265_LOG_ERROR, "%s abr-ladder config file not found or error in opening config file\n", optarg);
                return true;
            }
            else if (std::ferror(*abrConfig))
            {
                bool closeFailed = std::ferror(*abrConfig) != 0;
                if (std::fclose(*abrConfig))
                    closeFailed = true;
                if (closeFailed)
                    x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file after open failure\n");
                *abrConfig = nullptr;
                x265_log_file(nullptr, X265_LOG_ERROR, "%s abr-ladder config file not found or error in opening config file\n", optarg);
                return true;
            }
            return true;
        }
    }
    return false;
}

static bool getNumAbrEncodes(FILE* abrConfig, uint32_t& numEncodes)
{
    char line[1024];
    numEncodes = 0;
    int lineNumber = 0;

    while (std::fgets(line, sizeof(line), abrConfig))
    {
        lineNumber++;
        if (!validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line)))
            return false;
        char* entry = line;
        while (std::isspace((unsigned char)*entry))
            entry++;
        if (*entry == '#' || *entry == '\0' || (std::strcmp(entry, "\r\n") == 0) || (std::strcmp(entry, "\n") == 0))
            continue;
        numEncodes++;
    }
    clearerr(abrConfig);
    if (std::fseek(abrConfig, 0, SEEK_SET))
    {
        x265_log(nullptr, X265_LOG_ERROR, "Unable to rewind ABR ladder config\n");
        return false;
    }
    return true;
}

static bool parseAbrHeader(char* header, char** head, int lineNumber)
{
    if (!header || header[0] != '[')
    {
        x265_log(nullptr, X265_LOG_ERROR, "Missing ABR CLI header at line %d\n", lineNumber);
        return false;
    }

    char* headerEnd = std::strchr(header, ']');
    if (!headerEnd || headerEnd == header + 1 || headerEnd[1] != '\0')
    {
        x265_log(nullptr, X265_LOG_ERROR, "Malformed ABR CLI header at line %d\n", lineNumber);
        return false;
    }

    *headerEnd = '\0';
    char* field = header + 1;
    for (int index = 0; index < X265_HEAD_ENTRIES; index++)
    {
        char* separator = (index + 1 < X265_HEAD_ENTRIES) ? std::strchr(field, ':') : nullptr;
        if (index + 1 < X265_HEAD_ENTRIES)
        {
            if (!separator || separator == field)
            {
                x265_log(nullptr, X265_LOG_ERROR, "Incorrect number of arguments in ABR CLI header at line %d\n", lineNumber);
                return false;
            }
            *separator = '\0';
        }
        else if (!*field || std::strchr(field, ':'))
        {
            x265_log(nullptr, X265_LOG_ERROR, "Incorrect number of arguments in ABR CLI header at line %d\n", lineNumber);
            return false;
        }

        head[index] = field;
        field = separator ? separator + 1 : nullptr;
    }

    return true;
}

template <typename BeginToken, typename EmitChar, typename EndToken>
static bool walkAbrConfigArgs(const char* start, int lineNumber, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken)
{
    return walkConfigTokens(start,
        [&]() -> bool
        {
            x265_log(nullptr, X265_LOG_ERROR, "Missing ABR CLI arguments at line %d\n", lineNumber);
            return false;
        },
        [&](const char*) -> bool
        {
            return beginToken();
        },
        [&](const char*, char ch, size_t) -> bool
        {
            return emitChar(ch);
        },
        [&](const char*, size_t tokenLength) -> bool
        {
            return endToken(tokenLength);
        },
        [&]() -> bool
        {
            x265_log(nullptr, X265_LOG_ERROR, "Malformed ABR CLI arguments at line %d\n", lineNumber);
            return false;
        },
        [&]() -> bool
        {
            x265_log(nullptr, X265_LOG_ERROR, "Malformed ABR CLI arguments at line %d\n", lineNumber);
            return false;
        });
}

static bool measureAbrConfigArgs(const char* start, int& extraArgc, size_t& strPoolSize, int lineNumber)
{
    return walkAbrConfigArgs(start, lineNumber,
        [&]() -> bool
        {
            extraArgc++;
            return true;
        },
        [&](char) -> bool
        {
            return true;
        },
        [&](size_t tokenLength) -> bool
        {
            strPoolSize += tokenLength + 1;
            return true;
        });
}

static bool copyAbrConfigArgs(char* start, char** argv, int maxArgs, char* strPool, size_t strPoolSize, int& argc, int lineNumber)
{
    if (!start || !argv || !strPool || maxArgs < 2)
    {
        x265_log(nullptr, X265_LOG_ERROR, "Malformed ABR CLI arguments at line %d\n", lineNumber);
        return false;
    }

    char* tokenStart = nullptr;
    return walkAbrConfigArgs(start, lineNumber,
        [&]() -> bool
        {
            if (argc + 1 >= maxArgs)
            {
                x265_log(nullptr, X265_LOG_ERROR, "ABR CLI argument count exceeds supported limit at line %d\n", lineNumber);
                return false;
            }
            tokenStart = strPool;
            return true;
        },
        [&](char ch) -> bool
        {
            if (!strPoolSize)
            {
                x265_log(nullptr, X265_LOG_ERROR, "ABR CLI argument buffer exhausted at line %d\n", lineNumber);
                return false;
            }
            *strPool++ = ch;
            strPoolSize--;
            return true;
        },
        [&](size_t) -> bool
        {
            if (tokenStart == strPool || !strPoolSize)
            {
                x265_log(nullptr, X265_LOG_ERROR, "Malformed ABR CLI arguments at line %d\n", lineNumber);
                return false;
            }
            *strPool++ = '\0';
            strPoolSize--;
            argv[argc++] = tokenStart;
            return true;
        }) && (argv[argc] = nullptr, true);
}

static void destroyCliOptionsArray(CLIOptions cliopt[], uint32_t count)
{
    if (!cliopt)
        return;

    for (uint32_t i = 0; i < count; i++)
        cliopt[i].destroy();
}

static bool failAbrConfigParse(CLIOptions stagedCliopt[], uint32_t count)
{
    destroyCliOptionsArray(stagedCliopt, count);
    delete[] stagedCliopt;
    return false;
}

static bool parseAbrIntValue(const char* token, int& value)
{
    bool bError = false;
    int parsedValue = x265_atoi(token, bError);
    if (bError || parsedValue < 0)
        return false;

    value = parsedValue;
    return true;
}

struct AbrRefContextState
{
    int refId;
    uint32_t numRefs;
    uint32_t saveLevel;
    bool enableScaler;
};

static bool hasAbrReferenceEncode(const CLIOptions& cliopt)
{
    return std::strcmp(cliopt.reuseName, "nil") != 0;
}

static bool shouldEnableAbrScaler(const CLIOptions& prevCliopt, const CLIOptions& curCliopt)
{
    x265_param* prevParam = prevCliopt.param;
    x265_param* curParam = curCliopt.param;
    const bool sameInput = prevParam && curParam &&
        prevCliopt.inputfn[0] && curCliopt.inputfn[0] &&
        prevCliopt.inputfn[0][0] && curCliopt.inputfn[0][0] &&
        !std::strcmp(prevCliopt.inputfn[0], curCliopt.inputfn[0]);

    return sameInput &&
        (prevParam->sourceWidth != curParam->sourceWidth ||
         prevParam->sourceHeight != curParam->sourceHeight);
}

static bool parseAbrConfig(FILE* abrConfig, CLIOptions cliopt[], uint32_t numEncodes)
{
    char line[1024];
    char* argLine;
    int lineNumber = 0;
    CLIOptions* stagedCliopt = new CLIOptions[numEncodes];
    if (!stagedCliopt)
    {
        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate staged ABR config state\n");
        return false;
    }
    for (uint32_t i = 0; i < numEncodes; )
    {
        stagedCliopt[i].stringPool = nullptr;
        stagedCliopt[i].argString = nullptr;
        stagedCliopt[i].orgArgv = nullptr;
        if (std::fgets(line, sizeof(line), abrConfig) == nullptr)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Error reading ABR ladder configuration at line %d\n", lineNumber + 1);
            return failAbrConfigParse(stagedCliopt, i);
        }
        lineNumber++;
        if (!validateConfigFileLine(abrConfig, "ABR ladder config", lineNumber, line, sizeof(line)))
            return failAbrConfigParse(stagedCliopt, i);
        char* entry = line;
        while (std::isspace((unsigned char)*entry))
            entry++;
        if (*entry == '#' || *entry == '\0' || (std::strcmp(entry, "\r\n") == 0) || (std::strcmp(entry, "\n") == 0))
            continue;
        int index = (int)std::strcspn(line, "\r\n");
        line[index] = '\0';
        argLine = entry;
        char* start = argLine;
        while (*start && !std::isspace((unsigned char)*start))
            start++;
        if (!*start)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Missing ABR CLI arguments at line %d\n", lineNumber);
            return failAbrConfigParse(stagedCliopt, i + 1);
        }
        *start++ = '\0';

        /* Parse CLI header to identify the ID of the load encode and the reuse level */
        char *head[X265_HEAD_ENTRIES];
        stagedCliopt[i].encId = i;
        stagedCliopt[i].isAbrLadderConfig = true;
        if (!parseAbrHeader(argLine, head, lineNumber))
            return failAbrConfigParse(stagedCliopt, i + 1);

        bool bError = false;
        std::snprintf(stagedCliopt[i].encName, X265_MAX_STRING_SIZE, "%s", head[0]);
        int loadLevel = 0;
        bError = !parseAbrIntValue(head[1], loadLevel);
        std::snprintf(stagedCliopt[i].reuseName, X265_MAX_STRING_SIZE, "%s", head[2]);
        if (bError)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Invalid ABR CLI load level '%s' at line %d\n", head[1], lineNumber);
            return failAbrConfigParse(stagedCliopt, i + 1);
        }
        stagedCliopt[i].loadLevel = loadLevel;

        int extraArgc = 0;
        size_t strPoolSize = 0;
        if (!measureAbrConfigArgs(start, extraArgc, strPoolSize, lineNumber))
            return failAbrConfigParse(stagedCliopt, i + 1);

        const size_t argvCapacity = static_cast<size_t>(extraArgc) + 2;
        const size_t strPoolCapacity = strPoolSize != 0 ? strPoolSize : 1;
        char** argv = static_cast<char**>(std::malloc(argvCapacity * sizeof(char*)));
        char* strPool = static_cast<char*>(std::malloc(strPoolCapacity));
        if (!argv || !strPool)
        {
            std::free(argv);
            std::free(strPool);
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate ABR config argument buffers at line %d\n", lineNumber);
            return failAbrConfigParse(stagedCliopt, i + 1);
        }

        stagedCliopt[i].stringPool = strPool;
        stagedCliopt[i].argString = argv;

        char programName[] = "x265";
        int argc = 0;
        argv[argc++] = programName;
        if (!copyAbrConfigArgs(start, argv, extraArgc + 2, strPool, strPoolSize, argc, lineNumber))
            return failAbrConfigParse(stagedCliopt, i + 1);
        if (rejectCliExitRequest(argc, argv, "ABR CLI arguments", lineNumber))
            return failAbrConfigParse(stagedCliopt, i + 1);
        if (stagedCliopt[i].parse(argc++, argv))
            return failAbrConfigParse(stagedCliopt, i + 1);
        if (stagedCliopt[i].parseExitCode >= 0)
        {
            x265_log(nullptr, X265_LOG_ERROR, "ABR CLI arguments at line %d cannot trigger CLI exit handling\n", lineNumber);
            return failAbrConfigParse(stagedCliopt, i + 1);
        }
        i++;
    }
    for (uint32_t i = 0; i < numEncodes; i++)
        std::swap(cliopt[i], stagedCliopt[i]);
    delete[] stagedCliopt;
    return true;
}

static bool setRefContext(CLIOptions cliopt[], uint32_t numEncodes)
{
    AbrRefContextState* stagedState = new AbrRefContextState[numEncodes];
    if (!stagedState)
    {
        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate staged ABR reference state\n");
        return false;
    }

    for (uint32_t i = 0; i < numEncodes; i++)
    {
        stagedState[i].refId = cliopt[i].refId;
        stagedState[i].numRefs = cliopt[i].numRefs;
        stagedState[i].saveLevel = cliopt[i].saveLevel;
        stagedState[i].enableScaler = false;
    }

    /* Identify reference encode IDs and set save/load reuse levels */
    for (uint32_t curEnc = 0; curEnc < numEncodes; curEnc++)
    {
        bool isRefFound = false;
        if (hasAbrReferenceEncode(cliopt[curEnc]))
        {
            for (uint32_t refEnc = 0; refEnc < numEncodes; refEnc++)
            {
                if (!std::strcmp(cliopt[curEnc].reuseName, cliopt[refEnc].encName))
                {
                    stagedState[curEnc].refId = refEnc;
                    stagedState[refEnc].numRefs++;
                    stagedState[refEnc].saveLevel = X265_MAX(stagedState[refEnc].saveLevel, cliopt[curEnc].loadLevel);
                    isRefFound = true;
                    break;
                }
            }
            if (!isRefFound)
            {
                x265_log(nullptr, X265_LOG_ERROR, "Reference encode (%s) not found for %s\n", cliopt[curEnc].reuseName,
                    cliopt[curEnc].encName);
                delete[] stagedState;
                return false;
            }
        }
    }
    for (uint32_t i = 0; i < numEncodes; i++)
    {
        if (i)
            stagedState[i].enableScaler = shouldEnableAbrScaler(cliopt[i - 1], cliopt[i]);

        cliopt[i].refId = stagedState[i].refId;
        cliopt[i].numRefs = stagedState[i].numRefs;
        cliopt[i].saveLevel = stagedState[i].saveLevel;
        cliopt[i].enableScaler = stagedState[i].enableScaler;
    }
    delete[] stagedState;
    return true;
}
/* CLI return codes:
 *
 * 0 - encode successful
 * 1 - unable to parse command line
 * 2 - unable to open encoder
 * 3 - unable to generate stream headers
 * 4 - encoder abort */

int main(int argc, char **argv)
{
    int ret = 0;
#if HAVE_VLD
    // This uses Microsoft's proprietary WCHAR type, but this only builds on Windows to start with
    VLDSetReportOptions(VLD_OPT_REPORT_TO_DEBUGGER | VLD_OPT_REPORT_TO_FILE, L"x265_leaks.txt");
#endif
    PROFILE_INIT();
    THREAD_NAME("API", 0);

    GetConsoleTitle(orgConsoleTitle, CONSOLE_TITLE_SIZE);
    SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED);
#if _WIN32
    char** orgArgv = argv;
    get_argv_utf8(&argc, &argv);
#endif

    uint32_t numEncodes = 1;
    FILE *abrConfig = nullptr;
    bool isCliExitRequest = hasCliExitRequest(argc, argv);
    bool isAbrLadder = !isCliExitRequest && checkAbrLadder(argc, argv, &abrConfig);
    CLIOptions* cliopt = nullptr;
    AbrEncoder* abrEnc = nullptr;

    if (isAbrLadder && !abrConfig)
    {
        ret = 1;
        goto cleanup;
    }

    if (isAbrLadder)
    {
        if (!getNumAbrEncodes(abrConfig, numEncodes))
        {
            ret = 1;
            goto cleanup;
        }
        if (!numEncodes)
        {
            x265_log(nullptr, X265_LOG_ERROR, "ABR ladder config contains no valid encode entries\n");
            ret = 1;
            goto cleanup;
        }
    }

    cliopt = new CLIOptions[numEncodes];
    cliopt[0].orgArgv = argv;
    cliopt[0].argString = argv;

    if (isAbrLadder)
    {
        if (!parseAbrConfig(abrConfig, cliopt, numEncodes))
        {
            ret = 1;
            goto cleanup;
        }
        if (!setRefContext(cliopt, numEncodes))
        {
            ret = 1;
            goto cleanup;
        }
    }
    else if (cliopt[0].parse(argc, argv))
    {
        ret = 1;
        goto cleanup;
    }
    else if (cliopt[0].parseExitCode >= 0)
    {
        ret = cliopt[0].parseExitCode;
        goto cleanup;
    }

    if (cliopt[0].scenecutAwareQpConfig)
    {
        if (!cliopt[0].parseScenecutAwareQpConfig())
        {
            x265_log(nullptr, X265_LOG_ERROR, "Unable to parse scenecut aware qp config file \n");
            ret = 1;
            bool closeFailed = std::ferror(cliopt[0].scenecutAwareQpConfig) != 0;
            if (std::fclose(cliopt[0].scenecutAwareQpConfig))
                closeFailed = true;
            if (closeFailed)
                x265_log(nullptr, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after parse failure\n");
            cliopt[0].scenecutAwareQpConfig = nullptr;
        }
    }

    if (!ret)
    {
        abrEnc = new AbrEncoder(cliopt, numEncodes, ret);
        int threadsActive = abrEnc->m_numActiveEncodes.get();
        while (threadsActive)
        {
            threadsActive = abrEnc->m_numActiveEncodes.waitForChange(threadsActive);
            for (uint32_t idx = 0; idx < numEncodes; idx++)
            {
                if (!abrEnc->m_passEnc[idx])
                {
                    if (isAbrLadder)
                        x265_log(nullptr, X265_LOG_INFO, "Error generating ABR-ladder \n");
                    ret = 4;
                    threadsActive = 0;
                    break;
                }
                if (abrEnc->m_passEnc[idx]->m_ret)
                {
                    if (isAbrLadder)
                        x265_log(nullptr, X265_LOG_INFO, "Error generating ABR-ladder \n");
                    ret = abrEnc->m_passEnc[idx]->m_ret;
                    threadsActive = 0;
                    break;
                }
            }
        }
    }

cleanup:
    if (abrConfig)
    {
        bool closeFailed = std::ferror(abrConfig) != 0;
        if (std::fclose(abrConfig))
            closeFailed = true;
        if (closeFailed)
            x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file during main cleanup\n");
        abrConfig = nullptr;
    }

    if (abrEnc)
    {
        abrEnc->destroy();
        delete abrEnc;
    }

    bool destroyFailed = false;
    if (cliopt)
    {
        for (uint32_t idx = 0; idx < numEncodes; idx++)
            destroyFailed |= cliopt[idx].destroy();
    }

    if (!ret && destroyFailed)
        ret = 3;

    delete[] cliopt;

    SetConsoleTitle(orgConsoleTitle);
    SetThreadExecutionState(ES_CONTINUOUS);

#if _WIN32
    if (argv != orgArgv)
    {
        std::free(argv);
        argv = orgArgv;
    }
#endif

#if HAVE_VLD
    assert(VLDReportLeaks() == 0);
#endif

    return ret;
}
