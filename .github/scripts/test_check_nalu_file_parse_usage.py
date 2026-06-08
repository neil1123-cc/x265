#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_nalu_file_parse_usage.py')

# Coverage probes used by the scan for nalu-file parse guardrails.
NORMALIZED_PROBES = (
    'nalu-file parse must rewind the stream immediately after future-POC detection',
    'forbidden nalu-file parse regression: ',
    'missing nalu-file parse guardrail: ',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'enum UserSeiLineReadResult',
                    'UserSeiLineReadResult readUserSeiInputLine(FILE* file, char* line, size_t lineCapacity, x265_param* param)',
                    'x265_log(param, X265_LOG_WARNING, "User SEI file contains a line exceeding supported length; skipping\\n");',
                    'struct UserSeiLineFields',
                    'bool parseUserSeiLine(char* line, UserSeiLineFields& fields)',
                    'bool parseUserSeiIntToken(const char* token, int& value)',
                    "while (*scan && *scan != '/' && !std::isspace((unsigned char)*scan))",
                    'char* lineEnd = fields.base64Payload + std::strlen(fields.base64Payload);',
                    'long filePos = std::ftell(m_naluFile);',
                    'UserSeiLineReadResult lineState = readUserSeiInputLine(m_naluFile, line, sizeof(line), m_param);',
                    'if (lineState == USER_SEI_LINE_SKIPPED)',
                    'UserSeiLineFields fields;',
                    'if (!parseUserSeiLine(line, fields))',
                    'if (!parseUserSeiIntToken(fields.pocToken, poc) ||',
                    '!parseUserSeiIntToken(fields.nalTypeToken, nalType) ||',
                    '!parseUserSeiIntToken(fields.payloadTypeToken, payloadType))',
                    'if (poc > curPoc)',
                    'if (std::fseek(m_naluFile, filePos, SEEK_SET))',
                    'if (poc < curPoc)',
                    'char* base64Encode = fields.base64Payload;',
                    'if (nalType == NAL_UNIT_PREFIX_SEI && (!std::strcmp(fields.prefixToken, "PREFIX")))',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': 'char* pocToken = std::strtok(line, " ");\n'})
        expect_fail(run_checker(root), 'forbidden nalu-file parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'enum UserSeiLineReadResult',
                    'UserSeiLineReadResult readUserSeiInputLine(FILE* file, char* line, size_t lineCapacity, x265_param* param)',
                    'x265_log(param, X265_LOG_WARNING, "User SEI file contains a line exceeding supported length; skipping\\n");',
                    'struct UserSeiLineFields',
                    'bool parseUserSeiLine(char* line, UserSeiLineFields& fields)',
                    'bool parseUserSeiIntToken(const char* token, int& value)',
                    "while (*scan && *scan != '/' && !std::isspace((unsigned char)*scan))",
                    'char* lineEnd = fields.base64Payload + std::strlen(fields.base64Payload);',
                    'long filePos = std::ftell(m_naluFile);',
                    'UserSeiLineReadResult lineState = readUserSeiInputLine(m_naluFile, line, sizeof(line), m_param);',
                    'if (lineState == USER_SEI_LINE_SKIPPED)',
                    'UserSeiLineFields fields;',
                    'if (!parseUserSeiLine(line, fields))',
                    'if (!parseUserSeiIntToken(fields.pocToken, poc) ||',
                    '!parseUserSeiIntToken(fields.nalTypeToken, nalType) ||',
                    '!parseUserSeiIntToken(fields.payloadTypeToken, payloadType))',
                    'if (poc > curPoc)',
                    'if (std::fseek(m_naluFile, filePos, SEEK_SET))',
                    'char* base64Encode = fields.base64Payload;',
                    'if (poc < curPoc)',
                    'if (nalType == NAL_UNIT_PREFIX_SEI && (!std::strcmp(fields.prefixToken, "PREFIX")))',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'nalu-file parse must skip stale POC lines before decoding payload data')

    print('Nalu-file parse guard tests passed')


if __name__ == '__main__':
    main()
