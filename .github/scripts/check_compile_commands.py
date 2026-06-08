#!/usr/bin/env python3
import argparse
import json
import os
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
SOURCE_SUFFIXES = ('.cpp', '.cc', '.cxx', '.c', '.cp', '.c++', '.cxx', '.ixx', '.cppm', '.c++m', '.mm', '.m', '.inc')


def command_excerpt(command, limit=260):
    text = ' '.join(command.split())
    if len(text) <= limit:
        return text
    return text[:limit - 3] + '...'


def annotation_path(path):
    return Path(path).as_posix()


def entry_file_path(entry):
    return str(entry['file']).replace('\\', '/')


def normalize_path_fragment(fragment):
    return str(fragment).replace('\\', '/')


def normalized_entry_file_path(entry):
    return entry_file_path(entry).lower()


def normalized_path_fragment(fragment):
    return normalize_path_fragment(fragment).lower()


def canonicalize_path(path, directory=None):
    candidate = Path(strip_quotes(str(path)))
    if directory is not None and not candidate.is_absolute():
        candidate = Path(directory) / candidate
    try:
        candidate = candidate.resolve(strict=False)
    except OSError:
        pass
    return normalize_path_fragment(candidate).lower()


def lexical_normalize_path(path):
    return normalize_path_fragment(os.path.normpath(normalize_path_fragment(strip_quotes(str(path))))).lower()


def path_suffix_matches(path, suffix):
    normalized_path = lexical_normalize_path(path)
    normalized_suffix = lexical_normalize_path(suffix).lstrip('./')
    return normalized_path == normalized_suffix or normalized_path.endswith(f'/{normalized_suffix}')


def entry_file_matches_source(entry, source):
    expected_path = entry['file']
    directory = entry.get('directory')
    source_path = strip_quotes(str(source))
    if path_suffix_matches(expected_path, source_path):
        return True
    source_candidate = Path(source_path)
    if source_candidate.is_absolute():
        return canonicalize_path(expected_path) == canonicalize_path(source_candidate)
    if directory is not None:
        return canonicalize_path(expected_path) == canonicalize_path(source_candidate, directory)
    return False


def canonical_standard_flag(flag):
    flag = normalize_standard_flag(flag)
    if flag in ACCEPTED_STANDARD_FLAGS[:2]:
        return 'gnu++20'
    if flag in GNU_DIALECT_DRIFT_FLAGS:
        return 'c++20'
    return flag


def normalize_standard_flag(flag):
    if flag.lower().startswith('/std:'):
        return f'/std:{flag[5:].lower()}'
    return flag


def is_split_define_prefix(token):
    return token == '-D' or token.lower() == '/d'


def has_cxx_language_flag(tokens):
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == '-x' and index + 1 < len(tokens):
            if tokens[index + 1].lower() in ('c++', 'c++-header', 'objective-c++'):
                return True
            index += 2
            continue
        if token.startswith('-x') and token[2:].lower() in ('c++', 'c++-header', 'objective-c++'):
            return True
        if token.lower() == '/tp' or token.lower().startswith('/tp'):
            return True
        index += 1
    return False


def has_c_language_override(tokens):
    index = 0
    while index < len(tokens):
        token = tokens[index]
        lower = token.lower()
        if token == '-x' and index + 1 < len(tokens):
            if tokens[index + 1].lower() == 'c':
                return True
            index += 2
            continue
        if lower == '/tc' or lower.startswith('/tc'):
            return True
        index += 1
    return False


def is_cpp_entry(entry):
    token_groups = entry_token_groups(entry)
    if any(has_c_language_override(tokens) for tokens in token_groups):
        return any(has_cxx_language_flag(tokens) for tokens in token_groups)
    return entry_file_path(entry).lower().endswith(CXX_SUFFIXES) or any(has_cxx_language_flag(tokens) for tokens in token_groups)


def unique_source_count(entries):
    return len({normalized_entry_file_path(entry) for entry in entries})


def strip_quotes(token):
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        return token[1:-1]
    return token


def split_shell_words(text):
    # Windows compile_commands often preserve backslash paths in command strings.
    # Keep those backslashes intact so source-file checks can compare the real path.
    return shlex.split(text, posix='\\' not in text)


def should_expand_response_file(path):
    return path.suffix.lower() != '.modmap'


def response_file_candidates(path):
    candidates = [path]
    if not path.is_absolute():
        normalized = Path(normalize_path_fragment(path))
        if normalized != path:
            candidates.append(normalized)
    return candidates


def expand_response_files(tokens, directory=None, seen=None):
    if seen is None:
        seen = set()

    expanded = []
    for token in tokens:
        normalized = strip_quotes(str(token))
        if normalized.startswith('@') and len(normalized) > 1:
            response_path = Path(strip_quotes(normalized[1:]))
            if not should_expand_response_file(response_path):
                expanded.append(normalized)
                continue
            response_candidates = response_file_candidates(response_path)
            if directory is not None:
                response_candidates = [path if path.is_absolute() else Path(directory) / path for path in response_candidates]
            response_path = next((path for path in response_candidates if path.is_file()), response_candidates[0])
            if not response_path.is_file():
                fail(f'missing response file: {response_path}')
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


def define_aliases(token):
    if token.startswith('-D') and len(token) > len('-D'):
        macro = token[len('-D'):]
    elif token[:2].lower() == '/d' and len(token) > len('/D') and token[len('/D')] not in ('/', '\\', ':'):
        macro = token[len('/D'):]
    else:
        return []
    return [f'-D{macro}', f'/D{macro}']


def append_effective_token(tokens, token):
    tokens.append(token)
    for alias in define_aliases(token):
        if alias != token:
            tokens.append(alias)


def split_define_value(tokens, start_index):
    index = start_index
    if index >= len(tokens):
        return None
    candidate = str(tokens[index])
    if candidate == '-Xclang':
        index += 1
        if index >= len(tokens):
            return None
        candidate = str(tokens[index])
    if candidate.startswith(('-', '/', '@')):
        return None
    return candidate


def effective_tokens(tokens):
    expanded = []
    index = 0
    while index < len(tokens):
        token = str(tokens[index])
        append_effective_token(expanded, token)
        lower = token.lower()
        if is_split_define_prefix(token) and index + 1 < len(tokens):
            candidate = split_define_value(tokens, index + 1)
            if candidate is not None:
                append_effective_token(expanded, f'-D{candidate}')
        if lower.startswith('/clang:') and len(token) > len('/clang:'):
            unwrapped = token[len('/clang:'):]
            append_effective_token(expanded, unwrapped)
            if is_split_define_prefix(unwrapped):
                candidate = split_define_value(tokens, index + 1)
                if candidate is not None:
                    append_effective_token(expanded, f'-D{candidate}')
        elif token == '-Xclang' and index + 1 < len(tokens):
            unwrapped = str(tokens[index + 1])
            append_effective_token(expanded, unwrapped)
            if is_split_define_prefix(unwrapped):
                candidate = split_define_value(tokens, index + 2)
                if candidate is not None:
                    append_effective_token(expanded, f'-D{candidate}')
        elif token.startswith('-Xclang=') and len(token) > len('-Xclang='):
            unwrapped = token[len('-Xclang='):]
            append_effective_token(expanded, unwrapped)
            if is_split_define_prefix(unwrapped):
                candidate = split_define_value(tokens, index + 1)
                if candidate is not None:
                    append_effective_token(expanded, f'-D{candidate}')
        index += 1
    return expanded


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


def entry_effective_token_groups(entry):
    return [effective_tokens(tokens) for tokens in entry_token_groups(entry)]


def entry_tokens(entry):
    merged = []
    for group in entry_effective_token_groups(entry):
        for token in group:
            if token not in merged:
                merged.append(token)
    return merged


def looks_like_source_path(token):
    normalized = normalize_path_fragment(strip_quotes(str(token)))
    lower = normalized.lower()
    if lower.endswith(SOURCE_SUFFIXES):
        return True
    return '/' in normalized or '\\' in normalized


def source_tokens(tokens):
    sources = []
    index = 0
    while index < len(tokens):
        token = strip_quotes(str(tokens[index]))
        lower = token.lower()
        if token in ('-c', '/c'):
            if index + 1 < len(tokens):
                candidate = strip_quotes(str(tokens[index + 1]))
                if looks_like_source_path(candidate) and candidate not in sources:
                    sources.append(candidate)
            index += 2
            continue
        if lower in ('/tp', '/tc'):
            index += 1
            continue
        if (lower.startswith('/tp') or lower.startswith('/tc')) and len(token) > 3:
            candidate = token[3:]
            if looks_like_source_path(candidate) and candidate not in sources:
                sources.append(candidate)
        index += 1
    return sources


def entry_source_mismatches(entry):
    mismatches = []
    for tokens in entry_token_groups(entry):
        sources = source_tokens(tokens)
        if not sources:
            continue
        if all(entry_file_matches_source(entry, source) for source in sources):
            continue
        mismatches.append((entry, sources))
    return mismatches


def standard_flags(tokens):
    flags = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in ('-std', '--std'):
            if index + 1 < len(tokens):
                flags.append(normalize_standard_flag(f'{token}={tokens[index + 1]}'))
                index += 2
                continue
            flags.append(normalize_standard_flag(token))
        elif token.startswith(STANDARD_PREFIXES[:2]) or token.lower().startswith(STANDARD_PREFIXES[2]):
            flags.append(normalize_standard_flag(token))
        index += 1
    return flags


def depth_flags(tokens):
    return [token for token in tokens if token.startswith(DEPTH_DEFINE_PREFIX)]


def entry_standard_flags(entry):
    groups = [standard_flags(tokens) for tokens in entry_effective_token_groups(entry)]
    merged = []
    canonical = set()
    for flags in groups:
        if len(flags) != 1:
            return flags
        for flag in flags:
            canonical_flag = canonical_standard_flag(flag)
            if canonical_flag not in canonical:
                canonical.add(canonical_flag)
                merged.append(flag)
    return merged


def entry_missing_required_flag(entry, flag):
    return any(flag not in tokens for tokens in entry_effective_token_groups(entry))


def entry_missing_required_flag_prefix(entry, flag_prefix):
    return any(not any(token.startswith(flag_prefix) for token in tokens) for tokens in entry_effective_token_groups(entry))


def entry_has_flag(entry, flag):
    return any(flag in tokens for tokens in entry_effective_token_groups(entry))


def entry_has_flag_substring(entry, flag_substring):
    return any(any(flag_substring in token for token in tokens) for tokens in entry_effective_token_groups(entry))


def entry_missing_depth_define(entry, depth_define):
    return any(depth_define not in depth_flags(tokens) for tokens in entry_effective_token_groups(entry))


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
        rules.append((normalize_path_fragment(file_substring), flag))
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
        if not isinstance(entry['file'], str):
            fail(f'compile command entry #{index} file field must be a string', commands_path)
        if 'directory' in entry and not isinstance(entry['directory'], str):
            fail(f'compile command entry #{index} directory field must be a string', commands_path)
        if 'command' not in entry and 'arguments' not in entry:
            fail(f'compile command entry #{index} is missing command or arguments field', commands_path)
        if 'command' in entry and not isinstance(entry['command'], str):
            fail(f'compile command entry #{index} command field must be a string', commands_path)
        if 'arguments' in entry and not isinstance(entry['arguments'], list):
            fail(f'compile command entry #{index} arguments field must be a list', commands_path)
        if 'arguments' in entry and not all(isinstance(argument, str) for argument in entry['arguments']):
            fail(f'compile command entry #{index} arguments field must contain only strings', commands_path)
    cpp = [entry for entry in commands if is_cpp_entry(entry)]
    if not cpp:
        fail(f'no C++ compile commands: {commands_path}')

    source_mismatches = []
    for entry in cpp:
        source_mismatches.extend(entry_source_mismatches(entry))

    entry_token_map = {id(entry): entry_tokens(entry) for entry in cpp}
    required_file_flags = parse_file_flag_rules(args.required_file_flag)
    forbidden_file_flag_rules = parse_file_flag_rules(args.forbidden_file_flag)
    required_file_substrings = [normalized_path_fragment(substring) for substring in args.required_file_substring]
    forbidden_file_substrings_arg = [normalized_path_fragment(substring) for substring in args.forbidden_file_substring]
    depth_exclude_paths = [normalized_path_fragment(path) for path in args.depth_exclude_path]

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
    missing_file_substrings = [substring for substring in required_file_substrings if not any(substring in normalized_entry_file_path(entry) for entry in cpp)]
    forbidden_file_substrings = [
        (entry, substring)
        for entry in cpp
        for substring in forbidden_file_substrings_arg
        if substring in normalized_entry_file_path(entry)
    ]
    missing_file_flag_matches = []
    missing_file_flags = []
    for file_substring, flag in required_file_flags:
        normalized_file_substring = normalized_path_fragment(file_substring)
        matches = [entry for entry in cpp if normalized_file_substring in normalized_entry_file_path(entry)]
        if not matches:
            missing_file_flag_matches.append((file_substring, flag))
            continue
        for entry in matches:
            if entry_missing_required_flag(entry, flag):
                missing_file_flags.append((entry, file_substring, flag))
    forbidden_file_flags = []
    for file_substring, flag in forbidden_file_flag_rules:
        normalized_file_substring = normalized_path_fragment(file_substring)
        for entry in cpp:
            if normalized_file_substring in normalized_entry_file_path(entry) and entry_has_flag(entry, flag):
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
            path = normalized_entry_file_path(entry)
            if any(excluded in path for excluded in depth_exclude_paths):
                continue
            depth_checked += 1
            unexpected_depth_flags = []
            for tokens in entry_effective_token_groups(entry):
                for flag in depth_flags(tokens):
                    if flag != args.required_depth_define and flag not in unexpected_depth_flags:
                        unexpected_depth_flags.append(flag)
            if entry_missing_depth_define(entry, args.required_depth_define):
                missing_depth.append(entry)
            elif unexpected_depth_flags:
                mixed_depth.append((entry, unexpected_depth_flags))

    required_flags = ','.join(args.required_flag) if args.required_flag else '<none>'
    required_flag_prefixes = ','.join(args.required_flag_prefix) if args.required_flag_prefix else '<none>'
    required_file_substrings_text = ','.join(required_file_substrings) if required_file_substrings else '<none>'
    forbidden_file_substrings_text = ','.join(forbidden_file_substrings_arg) if forbidden_file_substrings_arg else '<none>'
    required_file_flag_rules = format_file_flag_rules(required_file_flags)
    forbidden_file_flag_rules_text = format_file_flag_rules(forbidden_file_flag_rules)
    forbidden_flags_text = ','.join(args.forbidden_flag) if args.forbidden_flag else '<none>'
    forbidden_flag_substrings = ','.join(args.forbidden_flag_substring) if args.forbidden_flag_substring else '<none>'
    depth_rule = args.required_depth_define or '<none>'
    depth_excludes = ','.join(depth_exclude_paths) if depth_exclude_paths else '<none>'
    min_cpp_commands = args.min_cpp_commands if args.min_cpp_commands is not None else '<none>'
    accepted_standards = ','.join(ACCEPTED_STANDARD_FLAGS)
    checked_sources = unique_source_count(cpp)
    print(f'{args.build_dir}: accepted_standards={accepted_standards} checked_cpp_commands={len(cpp)} checked_cpp_sources={checked_sources} min_cpp_commands={min_cpp_commands} required_flags={required_flags} required_flag_prefixes={required_flag_prefixes} required_file_substrings={required_file_substrings_text} forbidden_file_substrings={forbidden_file_substrings_text} required_file_flags={required_file_flag_rules} forbidden_file_flags={forbidden_file_flag_rules_text} forbidden_flags={forbidden_flags_text} forbidden_flag_substrings={forbidden_flag_substrings} required_depth_define={depth_rule} depth_checked_commands={depth_checked} depth_exclude_paths={depth_excludes}')
    if source_mismatches:
        entry, sources = source_mismatches[0]
        fail(
            f"{args.build_dir}: file field does not match compiled source {','.join(sources)} ({len(source_mismatches)} entries, showing first)",
            entry['file'],
            entry_command_text(entry),
        )
    if args.min_cpp_commands is not None and checked_sources < args.min_cpp_commands:
        fail(f'{args.build_dir}: expected at least {args.min_cpp_commands} unique C++ compile commands, found {checked_sources}')
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
