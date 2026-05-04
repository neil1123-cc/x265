#!/usr/bin/env python3
import argparse
import json
import shlex
from pathlib import Path

ACCEPTED_STANDARD_FLAGS = ('-std=gnu++20', '--std=gnu++20', '/std:c++20')
GNU_DIALECT_DRIFT_FLAGS = ('-std=c++20', '--std=c++20')
OLD_STANDARD_FLAGS = (
    '-std=c++11', '-std=gnu++11', '--std=c++11', '--std=gnu++11',
    '-std=c++14', '-std=gnu++14', '--std=c++14', '--std=gnu++14',
    '-std=c++17', '-std=gnu++17', '--std=c++17', '--std=gnu++17',
    '-std=c++1z', '-std=gnu++1z', '--std=c++1z', '--std=gnu++1z',
    '-std=c++2a', '-std=gnu++2a', '--std=c++2a', '--std=gnu++2a',
    '/std:c++14', '/std:c++17', '/std:c++latest',
)
STANDARD_PREFIXES = ('-std=', '--std=', '/std:')
DEPTH_DEFINE_PREFIX = '-DX265_DEPTH='
CXX_SUFFIXES = ('.cpp', '.cc', '.cxx')


def command_excerpt(command, limit=260):
    text = ' '.join(command.split())
    if len(text) <= limit:
        return text
    return text[:limit - 3] + '...'


def annotation_path(path):
    return Path(path).as_posix()


def entry_file_path(entry):
    return str(entry['file']).replace('\\', '/')


def strip_quotes(token):
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        return token[1:-1]
    return token


def split_shell_words(text):
    return shlex.split(text, posix=True)


def expand_response_files(tokens, directory=None, seen=None):
    if seen is None:
        seen = set()

    expanded = []
    for token in tokens:
        normalized = strip_quotes(str(token))
        if normalized.startswith('@') and len(normalized) > 1:
            response_path = Path(strip_quotes(normalized[1:]))
            if not response_path.is_absolute() and directory is not None:
                response_path = Path(directory) / response_path
            if response_path.is_file():
                resolved = response_path.resolve()
                if resolved in seen:
                    expanded.append(normalized)
                    continue
                seen.add(resolved)
                response_tokens = split_shell_words(response_path.read_text())
                expanded.extend(expand_response_files(response_tokens, response_path.parent, seen))
                seen.remove(resolved)
                continue
        expanded.append(normalized)
    return expanded


def command_tokens(command, directory=None):
    return expand_response_files(split_shell_words(command), directory)


def entry_command_text(entry):
    if 'command' in entry and 'arguments' in entry:
        return f"command={entry['command']} arguments={' '.join(str(arg) for arg in entry['arguments'])}"
    if 'command' in entry:
        return entry['command']
    return ' '.join(str(arg) for arg in entry.get('arguments', []))


def entry_token_groups(entry):
    groups = []
    directory = entry.get('directory')
    if 'arguments' in entry:
        groups.append(expand_response_files(entry['arguments'], directory))
    if 'command' in entry:
        groups.append(command_tokens(entry['command'], directory))
    if not groups:
        groups.append([])
    return groups


def entry_tokens(entry):
    merged = []
    for group in entry_token_groups(entry):
        for token in group:
            if token not in merged:
                merged.append(token)
    return merged


def standard_flags(tokens):
    return [token for token in tokens if token.startswith(STANDARD_PREFIXES)]


def depth_flags(tokens):
    return [token for token in tokens if token.startswith(DEPTH_DEFINE_PREFIX)]


def entry_standard_flags(entry):
    groups = [standard_flags(tokens) for tokens in entry_token_groups(entry)]
    merged = []
    for flags in groups:
        if len(flags) != 1:
            return flags
        for flag in flags:
            if flag not in merged:
                merged.append(flag)
    return merged


def entry_missing_required_flag(entry, flag):
    return any(flag not in tokens for tokens in entry_token_groups(entry))


def entry_missing_required_flag_prefix(entry, flag_prefix):
    return any(not any(token.startswith(flag_prefix) for token in tokens) for tokens in entry_token_groups(entry))


def entry_has_flag(entry, flag):
    return any(flag in tokens for tokens in entry_token_groups(entry))


def entry_has_flag_substring(entry, flag_substring):
    return any(any(flag_substring in token for token in tokens) for tokens in entry_token_groups(entry))


def entry_missing_depth_define(entry, depth_define):
    return any(depth_define not in depth_flags(tokens) for tokens in entry_token_groups(entry))


def detected_standard_text(flags):
    return ','.join(flags) if flags else '<none>'


def parse_file_flag_rules(values):
    rules = []
    for value in values:
        if '=' not in value:
            fail(f'invalid file flag rule {value!r}; expected FILE_SUBSTRING=FLAG')
        file_substring, flag = value.split('=', 1)
        if not file_substring or not flag:
            fail(f'invalid file flag rule {value!r}; expected FILE_SUBSTRING=FLAG')
        rules.append((file_substring, flag))
    return rules


def format_file_flag_rules(rules):
    return ','.join(f'{file_substring}={flag}' for file_substring, flag in rules) if rules else '<none>'


def fail(message, file_path=None, command=None):
    if file_path:
        print(f'::error file={annotation_path(file_path)}::{message}')
        detail = f'{message}: {file_path}'
    else:
        print(f'::error::{message}')
        detail = message
    if command:
        detail += f' command="{command_excerpt(command)}"'
    raise SystemExit(detail)


def main():
    parser = argparse.ArgumentParser(description='Check compile_commands.json C++ standard flags')
    parser.add_argument('build_dir', type=Path)
    parser.add_argument('--required-flag', action='append', default=[])
    parser.add_argument('--required-flag-prefix', action='append', default=[])
    parser.add_argument('--required-depth-define')
    parser.add_argument('--depth-exclude-path', action='append', default=[])
    parser.add_argument('--forbidden-flag-substring', action='append', default=[])
    parser.add_argument('--forbidden-flag', action='append', default=[])
    parser.add_argument('--required-file-substring', action='append', default=[])
    parser.add_argument('--forbidden-file-substring', action='append', default=[])
    parser.add_argument('--required-file-flag', action='append', default=[], metavar='FILE_SUBSTRING=FLAG')
    parser.add_argument('--forbidden-file-flag', action='append', default=[], metavar='FILE_SUBSTRING=FLAG')
    parser.add_argument('--min-cpp-commands', type=int)
    args = parser.parse_args()

    commands_path = args.build_dir / 'compile_commands.json'
    if not commands_path.is_file():
        fail(f'missing compile_commands.json: {commands_path}')

    try:
        commands = json.loads(commands_path.read_text())
    except json.JSONDecodeError as exc:
        fail(f'invalid compile_commands.json: {exc.msg}', commands_path)
    if not isinstance(commands, list):
        fail(f'compile_commands.json must contain a list: {commands_path}', commands_path)
    for index, entry in enumerate(commands, 1):
        if not isinstance(entry, dict):
            fail(f'compile command entry #{index} must be an object', commands_path)
        if 'file' not in entry:
            fail(f'compile command entry #{index} is missing file field', commands_path)
    cpp = [entry for entry in commands if entry_file_path(entry).lower().endswith(CXX_SUFFIXES)]
    if not cpp:
        fail(f'no C++ compile commands: {commands_path}')

    entry_token_map = {id(entry): entry_tokens(entry) for entry in cpp}
    required_file_flags = parse_file_flag_rules(args.required_file_flag)
    forbidden_file_flag_rules = parse_file_flag_rules(args.forbidden_file_flag)

    old_std = []
    gnu_dialect_drift = []
    missing_std = []
    duplicate_std = []
    for entry in cpp:
        tokens = entry_token_map[id(entry)]
        standards = entry_standard_flags(entry)
        old_flags = [flag for flag in standards if flag in OLD_STANDARD_FLAGS]
        drift_flags = [flag for flag in standards if flag in GNU_DIALECT_DRIFT_FLAGS]
        accepted_flags = [flag for flag in standards if flag in ACCEPTED_STANDARD_FLAGS]
        if len(standards) > 1:
            duplicate_std.append((entry, standards))
            continue
        if old_flags:
            old_std.append((entry, old_flags))
            continue
        if drift_flags:
            gnu_dialect_drift.append((entry, drift_flags))
            continue
        if not accepted_flags:
            missing_std.append((entry, standards))

    missing_flags = [(entry, flag) for entry in cpp for flag in args.required_flag if entry_missing_required_flag(entry, flag)]
    missing_flag_prefixes = [
        (entry, flag_prefix)
        for entry in cpp
        for flag_prefix in args.required_flag_prefix
        if entry_missing_required_flag_prefix(entry, flag_prefix)
    ]
    missing_file_substrings = [substring for substring in args.required_file_substring if not any(substring in entry_file_path(entry) for entry in cpp)]
    forbidden_file_substrings = [
        (entry, substring)
        for entry in cpp
        for substring in args.forbidden_file_substring
        if substring in entry_file_path(entry)
    ]
    missing_file_flag_matches = []
    missing_file_flags = []
    for file_substring, flag in required_file_flags:
        matches = [entry for entry in cpp if file_substring in entry_file_path(entry)]
        if not matches:
            missing_file_flag_matches.append((file_substring, flag))
            continue
        for entry in matches:
            if entry_missing_required_flag(entry, flag):
                missing_file_flags.append((entry, file_substring, flag))
    forbidden_file_flags = []
    for file_substring, flag in forbidden_file_flag_rules:
        for entry in cpp:
            if file_substring in entry_file_path(entry) and entry_has_flag(entry, flag):
                forbidden_file_flags.append((entry, file_substring, flag))
    forbidden_exact_flags = [
        (entry, flag)
        for entry in cpp
        for flag in args.forbidden_flag
        if entry_has_flag(entry, flag)
    ]
    forbidden_flags = [
        (entry, flag)
        for entry in cpp
        for flag in args.forbidden_flag_substring
        if entry_has_flag_substring(entry, flag)
    ]

    depth_checked = 0
    missing_depth = []
    mixed_depth = []
    if args.required_depth_define:
        for entry in cpp:
            path = entry_file_path(entry)
            if any(excluded in path for excluded in args.depth_exclude_path):
                continue
            depth_checked += 1
            unexpected_depth_flags = []
            for tokens in entry_token_groups(entry):
                for flag in depth_flags(tokens):
                    if flag != args.required_depth_define and flag not in unexpected_depth_flags:
                        unexpected_depth_flags.append(flag)
            if entry_missing_depth_define(entry, args.required_depth_define):
                missing_depth.append(entry)
            elif unexpected_depth_flags:
                mixed_depth.append((entry, unexpected_depth_flags))

    required_flags = ','.join(args.required_flag) if args.required_flag else '<none>'
    required_flag_prefixes = ','.join(args.required_flag_prefix) if args.required_flag_prefix else '<none>'
    required_file_substrings = ','.join(args.required_file_substring) if args.required_file_substring else '<none>'
    forbidden_file_substrings_text = ','.join(args.forbidden_file_substring) if args.forbidden_file_substring else '<none>'
    required_file_flag_rules = format_file_flag_rules(required_file_flags)
    forbidden_file_flag_rules_text = format_file_flag_rules(forbidden_file_flag_rules)
    forbidden_flags_text = ','.join(args.forbidden_flag) if args.forbidden_flag else '<none>'
    forbidden_flag_substrings = ','.join(args.forbidden_flag_substring) if args.forbidden_flag_substring else '<none>'
    depth_rule = args.required_depth_define or '<none>'
    depth_excludes = ','.join(args.depth_exclude_path) if args.depth_exclude_path else '<none>'
    min_cpp_commands = args.min_cpp_commands if args.min_cpp_commands is not None else '<none>'
    accepted_standards = ','.join(ACCEPTED_STANDARD_FLAGS)
    print(f'{args.build_dir}: accepted_standards={accepted_standards} checked_cpp_commands={len(cpp)} min_cpp_commands={min_cpp_commands} required_flags={required_flags} required_flag_prefixes={required_flag_prefixes} required_file_substrings={required_file_substrings} forbidden_file_substrings={forbidden_file_substrings_text} required_file_flags={required_file_flag_rules} forbidden_file_flags={forbidden_file_flag_rules_text} forbidden_flags={forbidden_flags_text} forbidden_flag_substrings={forbidden_flag_substrings} required_depth_define={depth_rule} depth_checked_commands={depth_checked} depth_exclude_paths={depth_excludes}')
    if args.min_cpp_commands is not None and len(cpp) < args.min_cpp_commands:
        fail(f'{args.build_dir}: expected at least {args.min_cpp_commands} C++ compile commands, found {len(cpp)}')
    if duplicate_std:
        entry, flags = duplicate_std[0]
        fail(f'{args.build_dir}: duplicate standard flags {detected_standard_text(flags)} ({len(duplicate_std)} files, showing first)', entry['file'], entry_command_text(entry))
    if old_std:
        entry, flags = old_std[0]
        fail(f'{args.build_dir}: old standard flag {detected_standard_text(flags)} ({len(old_std)} files, showing first)', entry['file'], entry_command_text(entry))
    if gnu_dialect_drift:
        entry, flags = gnu_dialect_drift[0]
        fail(f'{args.build_dir}: non-GNU C++20 dialect flag {detected_standard_text(flags)} ({len(gnu_dialect_drift)} files, showing first)', entry['file'], entry_command_text(entry))
    if missing_std:
        entry, flags = missing_std[0]
        fail(f'{args.build_dir}: missing GNU++20 dialect ({len(missing_std)} files, showing first; detected standard: {detected_standard_text(flags)})', entry['file'], entry_command_text(entry))
    if missing_flags:
        entry, flag = missing_flags[0]
        fail(f'{args.build_dir}: missing required flag {flag} ({len(missing_flags)} matches, showing first; detected standard: {detected_standard_text(standard_flags(entry_token_map[id(entry)]))})', entry['file'], entry_command_text(entry))
    if missing_flag_prefixes:
        entry, flag_prefix = missing_flag_prefixes[0]
        fail(f'{args.build_dir}: missing required flag prefix {flag_prefix} ({len(missing_flag_prefixes)} matches, showing first; detected standard: {detected_standard_text(standard_flags(entry_token_map[id(entry)]))})', entry['file'], entry_command_text(entry))
    if missing_file_substrings:
        fail(f'{args.build_dir}: missing compile command for file substring {missing_file_substrings[0]}')
    if forbidden_file_substrings:
        entry, substring = forbidden_file_substrings[0]
        fail(f'{args.build_dir}: forbidden compile command for file substring {substring} ({len(forbidden_file_substrings)} matches, showing first)', entry['file'], entry_command_text(entry))
    if missing_file_flag_matches:
        file_substring, flag = missing_file_flag_matches[0]
        fail(f'{args.build_dir}: missing compile command for file substring {file_substring} required by file flag {flag}')
    if missing_file_flags:
        entry, file_substring, flag = missing_file_flags[0]
        fail(f'{args.build_dir}: missing required flag {flag} for file substring {file_substring} ({len(missing_file_flags)} matches, showing first; detected standard: {detected_standard_text(standard_flags(entry_token_map[id(entry)]))})', entry['file'], entry_command_text(entry))
    if forbidden_file_flags:
        entry, file_substring, flag = forbidden_file_flags[0]
        fail(f'{args.build_dir}: forbidden flag {flag} for file substring {file_substring} ({len(forbidden_file_flags)} matches, showing first)', entry['file'], entry_command_text(entry))
    if forbidden_exact_flags:
        entry, flag = forbidden_exact_flags[0]
        fail(f'{args.build_dir}: forbidden flag {flag} ({len(forbidden_exact_flags)} matches, showing first)', entry['file'], entry_command_text(entry))
    if forbidden_flags:
        entry, flag = forbidden_flags[0]
        fail(f'{args.build_dir}: forbidden flag substring {flag} ({len(forbidden_flags)} matches, showing first)', entry['file'], entry_command_text(entry))
    if missing_depth:
        entry = missing_depth[0]
        fail(f'{args.build_dir}: missing {args.required_depth_define} ({len(missing_depth)} files, showing first)', entry['file'], entry_command_text(entry))
    if mixed_depth:
        entry, flags = mixed_depth[0]
        fail(f'{args.build_dir}: mixed depth defines {detected_standard_text(flags)} ({len(mixed_depth)} files, showing first)', entry['file'], entry_command_text(entry))


if __name__ == '__main__':
    main()
