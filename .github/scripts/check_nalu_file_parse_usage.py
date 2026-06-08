#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
FORBIDDEN_SNIPPETS = (
    'char* pocToken = std::strtok(line, " ");',
    'char* prefix = std::strtok(nullptr, " ");',
    'char* nalTypeToken = std::strtok(nullptr, "/");',
    'char* payloadTypeToken = std::strtok(nullptr, " ");',
    'char* base64Encode = std::strtok(nullptr, "\\n");',
)
REQUIRED_SNIPPETS = (
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
)
FORBIDDEN_SNIPPETS += (
    'int poc = x265_atoi(fields.pocToken, bError);',
    'int nalType = x265_atoi(fields.nalTypeToken, bError);',
    'int payloadType = x265_atoi(fields.payloadTypeToken, bError);',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden nalu-file parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing nalu-file parse guardrail: {snippet}'))

    future_pos = text.find('if (poc > curPoc)')
    seek_pos = text.find('if (std::fseek(m_naluFile, filePos, SEEK_SET))')
    stale_pos = text.find('if (poc < curPoc)')
    payload_pos = text.find('char* base64Encode = fields.base64Payload;')
    if -1 not in (future_pos, seek_pos) and not (future_pos < seek_pos):
        failures.append((TARGET.as_posix(), 0, 'nalu-file parse must rewind the stream immediately after future-POC detection'))
    if -1 not in (stale_pos, payload_pos) and not (stale_pos < payload_pos):
        failures.append((TARGET.as_posix(), 0, 'nalu-file parse must skip stale POC lines before decoding payload data'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed nalu-file parsing guardrails in encoder.cpp')
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

    print('Nalu-file parse usage validated')


if __name__ == '__main__':
    main()
