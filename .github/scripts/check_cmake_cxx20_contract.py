#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

REQUIRED_TOP_LEVEL_LINES = (
    'set(CMAKE_CXX_STANDARD 20)',
    'set(CMAKE_CXX_STANDARD_REQUIRED ON)',
    'set(CMAKE_CXX_EXTENSIONS ON)',
)
MANUAL_STANDARD_MARKERS = ('-std=c++', '-std=gnu++', '--std=c++', '--std=gnu++', '/std:c++')
SCRIPT_STANDARD_MARKERS = (*MANUAL_STANDARD_MARKERS, 'CXX_STANDARD=', 'CXX_STANDARD_REQUIRED=', 'CXX_EXTENSIONS=')
REQUIRED_TOP_LEVEL_CONTRACT = {
    'CMAKE_CXX_STANDARD': '20',
    'CMAKE_CXX_STANDARD_REQUIRED': 'ON',
    'CMAKE_CXX_EXTENSIONS': 'ON',
}
TARGET_PROPERTY_MARKERS = {'CXX_STANDARD', 'CXX_STANDARD_REQUIRED', 'CXX_EXTENSIONS'}
COMPILE_FLAG_COMMANDS = {'add_compile_options', 'target_compile_options', 'add_definitions'}
COMPILE_FLAG_PROPERTY_COMMANDS = {'set_property', 'set_source_files_properties', 'set_target_properties', 'set_directory_properties'}
COMPILE_FLAG_PROPERTIES = {'COMPILE_FLAGS', 'COMPILE_OPTIONS', 'INTERFACE_COMPILE_OPTIONS'}
LIST_COMPILE_FLAG_SUBCOMMANDS = {'append', 'prepend', 'insert'}
STRING_COMPILE_FLAG_SUBCOMMANDS = {'append', 'prepend', 'concat'}
COMPILE_FLAG_VARIABLE_MARKERS = ('COMPILE_FLAGS', 'COMPILE_OPTIONS', 'CXX_FLAGS', 'CXX_OPTIONS')
WRAPPED_FLAG_COMMAND_MARKERS = ('compile', 'cxx', 'flag', 'option', 'definition')
WRAPPED_FLAG_COMMAND_ALLOWLIST = {
    'add_subdirectory', 'cmake_minimum_required', 'else', 'elseif', 'endforeach',
    'endfunction', 'endif', 'endmacro', 'foreach', 'function', 'if', 'include',
    'list', 'macro', 'message', 'option', 'project', 'set', 'string', 'while',
}
CXX_FLAG_VARIABLE_RE = re.compile(r'^CMAKE_CXX_FLAGS($|_)')
BRACKET_COMMENT_RE = re.compile(r'#\[(=*)\[')
CMAKE_TOKEN_RE = re.compile(r'\[=*\[[\s\S]*?\]=*\]|"(?:[^"\\]|\\.)*"|\$<[^>]*>|[^\s()]+')
SCRIPT_SCAN_GLOBS = (
    '.github/workflows/*.yml',
    '.github/workflows/*.yaml',
    '.github/actions/*/action.yml',
    '.github/scripts/*.sh',
    '.github/scripts/*.py',
)
SCRIPT_STANDARD_ALLOWLIST = (
    '-DCMAKE_CXX_STANDARD=17',
    '--forbidden-flag-substring=-std=gnu++17',
    '--forbidden-flag-substring=-std=c++17',
    '--forbidden-flag=-DX265_DEPTH=',
    'MANUAL_STANDARD_MARKERS = (',
    'SCRIPT_STANDARD_MARKERS = (*MANUAL_STANDARD_MARKERS,',
    'def cmake_commands(path):',
    'def parse_cmake_set(command):',
    'SCRIPT_STANDARD_ALLOWLIST = (',
    'allowed_script_standard_line(stripped)',
    'if any(marker in stripped for marker in MANUAL_STANDARD_MARKERS):',
    'if any(marker in stripped for marker in SCRIPT_STANDARD_MARKERS):',
    'OLD_STANDARD_FLAGS = (',
    "'-std=c++11', '-std=gnu++11',",
    "'-std=c++14', '-std=gnu++14',",
    "'-std=c++17', '-std=gnu++17',",
    "'-std=c++1z', '-std=gnu++1z',",
    "'-std=c++2a', '-std=gnu++2a',",
    "'/std:c++14', '/std:c++17', '/std:c++latest',",
    "STANDARD_PREFIXES = ('-std=', '/std:')",
    "ACCEPTED_STANDARD_FLAGS = ('-std=gnu++20', '--std=gnu++20', '/std:c++20')",
    "GNU_DIALECT_DRIFT_FLAGS = ('-std=c++20', '--std=c++20')",
    "'--std=gnu++20',",
    '--std=gnu++20',
    'if flag in GNU_DIALECT_DRIFT_FLAGS:',
    "STANDARD_PREFIXES = ('-std=', '--std=', '/std:')",
)


def strip_script_comment(line):
    stripped = []
    in_single_quote = False
    in_double_quote = False
    escaped = False
    for char in line:
        if escaped:
            stripped.append(char)
            escaped = False
            continue
        if char == '\\' and in_double_quote:
            stripped.append(char)
            escaped = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            stripped.append(char)
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            stripped.append(char)
            continue
        if char == '#' and not in_single_quote and not in_double_quote:
            break
        stripped.append(char)
    return ''.join(stripped).strip()


def allowed_script_standard_line(stripped):
    return any(allowed in stripped for allowed in SCRIPT_STANDARD_ALLOWLIST)


def strip_cmake_comment(line, bracket_comment_end=None):
    stripped = []
    in_quote = False
    escaped = False
    index = 0
    while index < len(line):
        if bracket_comment_end is not None:
            end = line.find(bracket_comment_end, index)
            if end == -1:
                return ''.join(stripped).strip(), bracket_comment_end
            index = end + len(bracket_comment_end)
            bracket_comment_end = None
            continue

        char = line[index]
        if escaped:
            stripped.append(char)
            escaped = False
        elif char == '\\':
            stripped.append(char)
            escaped = in_quote
        elif char == '"':
            stripped.append(char)
            in_quote = not in_quote
        elif not in_quote and char == '#':
            match = BRACKET_COMMENT_RE.match(line, index)
            if not match:
                break
            bracket_comment_end = ']' + match.group(1) + ']'
            index += len(match.group(0))
            continue
        else:
            stripped.append(char)
        index += 1
    return ''.join(stripped).strip(), bracket_comment_end


def unquote_cmake_token(token):
    if len(token) >= 2 and token[0] == token[-1] == '"':
        return token[1:-1]
    match = re.fullmatch(r'\[(=*)\[([\s\S]*)\]\1\]', token)
    if match:
        return match.group(2)
    return token


def tokenize_cmake_body(command):
    body = cmake_command_body(command)
    if body is None:
        return None
    return [unquote_cmake_token(token) for token in CMAKE_TOKEN_RE.findall(' '.join(body))]


def cmake_command_name(command):
    return command.split('(', 1)[0].strip().lower()


def cmake_command_body(command):
    if '(' not in command or not command.endswith(')'):
        return None
    return command.split('(', 1)[1][:-1].split()


def update_paren_balance(line, balance):
    in_quote = False
    escaped = False
    index = 0
    while index < len(line):
        char = line[index]
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = in_quote
        elif char == '"':
            in_quote = not in_quote
        elif not in_quote:
            if line.startswith('$<', index):
                end = line.find('>', index + 2)
                if end != -1:
                    index = end
            elif char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
        index += 1
    return balance


def cmake_commands(path):
    pending = []
    start_line = None
    balance = 0
    bracket_comment_end = None
    for index, line in enumerate(path.read_text().splitlines(), 1):
        stripped, bracket_comment_end = strip_cmake_comment(line, bracket_comment_end)
        if not stripped:
            continue
        if not pending:
            start_line = index
        pending.append(stripped)
        balance = update_paren_balance(stripped, balance)
        if balance <= 0:
            command = ' '.join(pending).strip()
            if command:
                yield start_line, command
            pending = []
            start_line = None
            balance = 0
    if pending:
        yield start_line, ' '.join(pending).strip()


def parse_cmake_set(command):
    if cmake_command_name(command) != 'set':
        return None
    parts = tokenize_cmake_body(command)
    if parts is None or len(parts) < 2:
        return None
    return parts[0], parts[1]


def normalize_contract_value(name, value):
    if name == 'CMAKE_CXX_STANDARD':
        return value
    return value.upper()


def has_target_property_override(command):
    name = cmake_command_name(command)
    parts = tokenize_cmake_body(command)
    if parts is None:
        return False
    upper_parts = [part.upper() for part in parts]
    if name == 'set_target_properties':
        if 'PROPERTIES' not in upper_parts:
            return False
        properties_index = upper_parts.index('PROPERTIES') + 1
        return any(upper_parts[index] in TARGET_PROPERTY_MARKERS for index in range(properties_index, len(upper_parts), 2))
    if name == 'set_property':
        if 'TARGET' not in upper_parts:
            return False
        property_indices = [index for index, part in enumerate(upper_parts) if part == 'PROPERTY']
        return any(index + 1 < len(upper_parts) and upper_parts[index + 1] in TARGET_PROPERTY_MARKERS for index in property_indices)
    return False


def is_compile_flag_variable(variable):
    if CXX_FLAG_VARIABLE_RE.search(variable):
        return True
    variable_tokens = {token for token in re.split(r'[^A-Z0-9]+', variable.upper()) if token}
    if {'DOC', 'DOCS', 'DOCUMENTATION', 'HELP', 'COMMENT', 'COMMENTS', 'DESCRIPTION', 'DESCRIPTIONS', 'EXAMPLE', 'EXAMPLES'} & variable_tokens:
        return False
    for marker in COMPILE_FLAG_VARIABLE_MARKERS:
        marker_tokens = marker.split('_')
        if len(marker_tokens) <= len(variable_tokens) and all(token in variable_tokens for token in marker_tokens):
            return True
    return False


def contains_manual_standard_flag(parts):
    return any(marker in part for part in parts for marker in MANUAL_STANDARD_MARKERS)


def references_variable(parts, variable):
    return any(f'${{{variable}}}' in part for part in parts)


def variable_references(parts):
    variables = set()
    for part in parts:
        variables.update(re.findall(r'\$\{([^}]+)\}', part))
    return variables


def wrapper_parameter_references(parts, parameters):
    references = set()
    for variable in variable_references(parts):
        if variable in parameters or variable in {'ARGN', 'ARGV'} or re.fullmatch(r'ARGV[0-9]+', variable):
            references.add(variable)
    return references


def wrapper_parameter_source_references(parts, parameters, variable_sources=None):
    references = set()
    for variable in variable_references(parts):
        if variable in parameters or variable in {'ARGN', 'ARGV'} or re.fullmatch(r'ARGV[0-9]+', variable):
            references.add(variable)
        elif variable_sources and variable in variable_sources:
            references.update(variable_sources[variable])
    return references


def wrapper_sink_argument_parts(parts, parameters, sink_parameters):
    selected_parts = []
    parameter_positions = {parameter: index for index, parameter in enumerate(parameters)}
    for sink_parameter in sink_parameters:
        if sink_parameter == 'ARGV':
            selected_parts.extend(parts)
            continue
        if sink_parameter == 'ARGN':
            selected_parts.extend(parts[len(parameters):])
            continue
        match = re.fullmatch(r'ARGV([0-9]+)', sink_parameter)
        if match:
            index = int(match.group(1))
            if index < len(parts):
                selected_parts.append(parts[index])
            continue
        if sink_parameter in parameter_positions:
            index = parameter_positions[sink_parameter]
            if index < len(parts):
                selected_parts.append(parts[index])
    return selected_parts




def collect_wrapper_definitions(source_commands):
    definitions = {}
    for _path, commands in source_commands:
        current_name = None
        current_end = None
        current_parameters = ()
        current_body = []
        for _index, command in commands:
            name = cmake_command_name(command)
            parts = tokenize_cmake_body(command)
            if current_name is not None:
                if name == current_end:
                    definitions.setdefault(current_name, []).append((current_parameters, tuple(current_body)))
                    current_name = None
                    current_end = None
                    current_parameters = ()
                    current_body = []
                    continue
                current_body.append(command)
                continue
            if name in ('function', 'macro') and parts:
                current_name = parts[0].lower()
                current_end = f'end{name}'
                current_parameters = tuple(parts[1:])
                current_body = []
    return definitions


def referenced_wrapper_sink_parameters(command, parameters, wrapper_sink_parameters):
    name = cmake_command_name(command)
    parts = tokenize_cmake_body(command)
    if parts is None:
        return set()
    if name == 'set' and parts:
        variable = parts[0]
        if is_compile_flag_variable(variable):
            return wrapper_parameter_references(parts[1:], parameters)
    if name == 'list' and len(parts) >= 3 and parts[0].lower() in LIST_COMPILE_FLAG_SUBCOMMANDS:
        variable = parts[1]
        if is_compile_flag_variable(variable):
            return wrapper_parameter_references(parts[2:], parameters)
    if name == 'string' and len(parts) >= 3 and parts[0].lower() in STRING_COMPILE_FLAG_SUBCOMMANDS:
        variable = parts[1]
        if is_compile_flag_variable(variable):
            return wrapper_parameter_references(parts[2:], parameters)
    if name in COMPILE_FLAG_COMMANDS:
        return wrapper_parameter_references(parts, parameters)
    if name in COMPILE_FLAG_PROPERTY_COMMANDS:
        upper_parts = [part.upper() for part in parts]
        property_indices = [index for index, part in enumerate(upper_parts) if part in ('PROPERTIES', 'PROPERTY')]
        references = set()
        for property_index in property_indices:
            index = property_index + 1
            while index < len(parts):
                if upper_parts[index] in COMPILE_FLAG_PROPERTIES:
                    value_start = index + 1
                    if value_start >= len(parts):
                        return references
                    if upper_parts[property_index] == 'PROPERTY':
                        references.update(wrapper_parameter_references(parts[value_start:], parameters))
                    else:
                        references.update(wrapper_parameter_references([parts[value_start]], parameters))
                    index += 2
                else:
                    index += 2
        return references
    if name in wrapper_sink_parameters:
        references = set()
        for wrapper_parameters, sink_parameters in wrapper_sink_parameters[name]:
            argument_parts = wrapper_sink_argument_parts(parts, wrapper_parameters, sink_parameters)
            references.update(wrapper_parameter_references(argument_parts, parameters))
        return references
    if name not in WRAPPED_FLAG_COMMAND_ALLOWLIST and any(marker in name for marker in WRAPPED_FLAG_COMMAND_MARKERS):
        return wrapper_parameter_references(parts, parameters)
    return set()


def collect_wrapper_sink_parameters(source_commands):
    wrapper_definitions = collect_wrapper_definitions(source_commands)
    wrapper_sink_parameters = {
        name: [(parameters, set()) for parameters, _body in definitions]
        for name, definitions in wrapper_definitions.items()
    }
    changed = True
    while changed:
        changed = False
        for name, definitions in wrapper_definitions.items():
            for definition_index, (parameters, body) in enumerate(definitions):
                sink_parameters = wrapper_sink_parameters[name][definition_index][1]
                references = set()
                for command in body:
                    references.update(referenced_wrapper_sink_parameters(command, parameters, wrapper_sink_parameters))
                if not references.issubset(sink_parameters):
                    sink_parameters.update(references)
                    changed = True
    return {
        name: [(parameters, frozenset(sink_parameters)) for parameters, sink_parameters in definitions]
        for name, definitions in wrapper_sink_parameters.items()
    }


def referenced_wrapper_target_feature_parameters(command, parameters, wrapper_target_feature_parameters, variable_sources=None):
    name = cmake_command_name(command)
    parts = tokenize_cmake_body(command)
    if parts is None:
        return set()
    if name == 'target_compile_features':
        return wrapper_parameter_source_references(parts, parameters, variable_sources)
    if name in wrapper_target_feature_parameters:
        references = set()
        for wrapper_parameters, target_feature_parameters in wrapper_target_feature_parameters[name]:
            argument_parts = wrapper_sink_argument_parts(parts, wrapper_parameters, target_feature_parameters)
            references.update(wrapper_parameter_source_references(argument_parts, parameters, variable_sources))
        return references
    return set()


def collect_wrapper_target_feature_parameters(source_commands):
    wrapper_definitions = collect_wrapper_definitions(source_commands)
    wrapper_target_feature_parameters = {
        name: [(parameters, set()) for parameters, _body in definitions]
        for name, definitions in wrapper_definitions.items()
    }
    changed = True
    while changed:
        changed = False
        for name, definitions in wrapper_definitions.items():
            for definition_index, (parameters, body) in enumerate(definitions):
                target_feature_parameters = wrapper_target_feature_parameters[name][definition_index][1]
                references = set()
                local_variable_sources = {}
                for command in body:
                    command_name = cmake_command_name(command)
                    parts = tokenize_cmake_body(command)
                    if parts is None:
                        continue
                    local_variable = None
                    values = ()
                    if command_name == 'set' and len(parts) >= 2 and not is_compile_flag_variable(parts[0]):
                        local_variable = parts[0]
                        values = parts[1:]
                    elif command_name == 'list' and len(parts) >= 3 and parts[0].lower() in LIST_COMPILE_FLAG_SUBCOMMANDS and not is_compile_flag_variable(parts[1]):
                        local_variable = parts[1]
                        values = parts[2:]
                    elif command_name == 'string' and len(parts) >= 3 and parts[0].lower() in STRING_COMPILE_FLAG_SUBCOMMANDS and not is_compile_flag_variable(parts[1]):
                        local_variable = parts[1]
                        values = parts[2:]
                    if local_variable:
                        local_sources = wrapper_parameter_source_references(values, parameters, local_variable_sources)
                        if local_sources:
                            existing_sources = local_variable_sources.setdefault(local_variable, set())
                            existing_sources.update(local_sources)
                    references.update(referenced_wrapper_target_feature_parameters(command, parameters, wrapper_target_feature_parameters, local_variable_sources))
                if not references.issubset(target_feature_parameters):
                    target_feature_parameters.update(references)
                    changed = True
    return {
        name: [(parameters, frozenset(target_feature_parameters)) for parameters, target_feature_parameters in definitions]
        for name, definitions in wrapper_target_feature_parameters.items()
    }


def contains_manual_standard_variable(parts, manual_standard_variables):
    return bool(variable_references(parts) & manual_standard_variables)


def contains_target_feature_override_values(parts, target_feature_variables=None):
    target_feature_variables = target_feature_variables or set()
    return any(re.search(r'(?<![A-Za-z0-9_])cxx_std_[0-9]+(?![A-Za-z0-9_])', part) for part in parts) or bool(variable_references(parts) & target_feature_variables)


def has_manual_standard_wrapper_call(command, manual_standard_variables, wrapper_sink_parameters):
    name = cmake_command_name(command)
    parts = tokenize_cmake_body(command)
    if parts is None or name not in wrapper_sink_parameters:
        return False
    for parameters, sink_parameters in wrapper_sink_parameters[name]:
        argument_parts = wrapper_sink_argument_parts(parts, parameters, sink_parameters)
        if contains_manual_standard_flag(argument_parts) or contains_manual_standard_variable(argument_parts, manual_standard_variables):
            return True
    return False


def has_target_feature_wrapper_call(command, target_feature_variables, wrapper_target_feature_parameters):
    name = cmake_command_name(command)
    parts = tokenize_cmake_body(command)
    if parts is None or name not in wrapper_target_feature_parameters:
        return False
    for parameters, target_feature_parameters in wrapper_target_feature_parameters[name]:
        argument_parts = wrapper_sink_argument_parts(parts, parameters, target_feature_parameters)
        if contains_target_feature_override_values(argument_parts, target_feature_variables):
            return True
    return False


def foreach_values_contain_manual_standard(values, manual_standard_variables):
    if contains_manual_standard_flag(values) or contains_manual_standard_variable(values, manual_standard_variables):
        return True
    upper_values = [value.upper() for value in values]
    if len(values) >= 3 and upper_values[0] == 'IN' and upper_values[1] == 'LISTS':
        return any(value in manual_standard_variables for value in values[2:])
    return False


def foreach_values_contain_target_feature(values, target_feature_variables):
    if contains_target_feature_override_values(values, target_feature_variables):
        return True
    upper_values = [value.upper() for value in values]
    if len(values) >= 3 and upper_values[0] == 'IN' and upper_values[1] == 'LISTS':
        return any(value in target_feature_variables for value in values[2:])
    return False


def has_manual_standard_flag(command, manual_standard_variables=None):
    manual_standard_variables = manual_standard_variables or set()
    name = cmake_command_name(command)
    parts = tokenize_cmake_body(command)
    if parts is None:
        return False
    if name == 'set' and parts:
        variable = parts[0]
        if is_compile_flag_variable(variable):
            return contains_manual_standard_flag(parts[1:]) or contains_manual_standard_variable(parts[1:], manual_standard_variables)
    if name == 'list' and len(parts) >= 3 and parts[0].lower() in LIST_COMPILE_FLAG_SUBCOMMANDS:
        variable = parts[1]
        if is_compile_flag_variable(variable):
            return contains_manual_standard_flag(parts[2:]) or contains_manual_standard_variable(parts[2:], manual_standard_variables)
    if name == 'string' and len(parts) >= 3 and parts[0].lower() in STRING_COMPILE_FLAG_SUBCOMMANDS:
        variable = parts[1]
        if is_compile_flag_variable(variable):
            return contains_manual_standard_flag(parts[2:]) or contains_manual_standard_variable(parts[2:], manual_standard_variables)
    if name in COMPILE_FLAG_COMMANDS:
        return contains_manual_standard_flag(parts) or contains_manual_standard_variable(parts, manual_standard_variables)
    if name in COMPILE_FLAG_PROPERTY_COMMANDS:
        upper_parts = [part.upper() for part in parts]
        property_indices = [index for index, part in enumerate(upper_parts) if part in ('PROPERTIES', 'PROPERTY')]
        for property_index in property_indices:
            index = property_index + 1
            while index < len(parts):
                if upper_parts[index] in COMPILE_FLAG_PROPERTIES:
                    value_start = index + 1
                    if value_start >= len(parts):
                        return False
                    if upper_parts[property_index] == 'PROPERTY':
                        return contains_manual_standard_flag(parts[value_start:]) or contains_manual_standard_variable(parts[value_start:], manual_standard_variables)
                    if contains_manual_standard_flag([parts[value_start]]) or contains_manual_standard_variable([parts[value_start]], manual_standard_variables):
                        return True
                    index += 2
                else:
                    index += 2
    if name not in WRAPPED_FLAG_COMMAND_ALLOWLIST and any(marker in name for marker in WRAPPED_FLAG_COMMAND_MARKERS):
        return contains_manual_standard_flag(parts) or contains_manual_standard_variable(parts, manual_standard_variables)
    return False


def has_target_feature_override(command, target_feature_variables=None):
    if cmake_command_name(command) != 'target_compile_features':
        return False
    parts = tokenize_cmake_body(command)
    if parts is None:
        return False
    return contains_target_feature_override_values(parts, target_feature_variables)


def iter_source_cmake_files(root):
    yield from root.rglob('CMakeLists.txt')
    yield from root.rglob('*.cmake')


def iter_script_scan_files(repo_root):
    for pattern in SCRIPT_SCAN_GLOBS:
        for path in repo_root.glob(pattern):
            if path.name.startswith('test_'):
                continue
            yield path


def annotation_path(path):
    return Path(path).as_posix()


def fail(message, path=None, line=None):
    if path is not None:
        location = annotation_path(path)
        if line is not None:
            print(f'::error file={location},line={line}::{message}')
            raise SystemExit(f'{message}: {location}:{line}')
        print(f'::error file={location}::{message}')
        raise SystemExit(f'{message}: {location}')
    print(f'::error::{message}')
    raise SystemExit(message)


def check_contract(source_dir):
    root = Path(source_dir)
    top = root / 'CMakeLists.txt'
    if not top.is_file():
        fail('missing top-level CMakeLists.txt', top)

    top_settings = {}
    for index, command in cmake_commands(top):
        parsed = parse_cmake_set(command)
        if parsed and parsed[0] in REQUIRED_TOP_LEVEL_CONTRACT:
            top_settings[parsed[0]] = (normalize_contract_value(parsed[0], parsed[1]), index)
    missing = [name for name in REQUIRED_TOP_LEVEL_CONTRACT if name not in top_settings]
    if missing:
        fail('missing top-level GNU++20 contract: ' + ', '.join(REQUIRED_TOP_LEVEL_LINES), top)
    for name, expected in REQUIRED_TOP_LEVEL_CONTRACT.items():
        value, index = top_settings[name]
        if value != expected:
            fail(f'top-level GNU++20 contract drift: set({name} {value})', top, index)

    manual_standard_variables = set()
    target_feature_variables = set()
    source_commands = [(path, tuple(cmake_commands(path))) for path in iter_source_cmake_files(root)]
    wrapper_sink_parameters = collect_wrapper_sink_parameters(source_commands)
    wrapper_target_feature_parameters = collect_wrapper_target_feature_parameters(source_commands)
    changed = True
    while changed:
        changed = False
        for path, commands in source_commands:
            for index, command in commands:
                name = cmake_command_name(command)
                parts = tokenize_cmake_body(command)
                if parts is None:
                    continue
                manual_variable = None
                values = ()
                if name == 'set' and len(parts) >= 2 and not is_compile_flag_variable(parts[0]):
                    manual_variable = parts[0]
                    values = parts[1:]
                elif name == 'list' and len(parts) >= 3 and parts[0].lower() in LIST_COMPILE_FLAG_SUBCOMMANDS and not is_compile_flag_variable(parts[1]):
                    manual_variable = parts[1]
                    values = parts[2:]
                elif name == 'string' and len(parts) >= 3 and parts[0].lower() in STRING_COMPILE_FLAG_SUBCOMMANDS and not is_compile_flag_variable(parts[1]):
                    manual_variable = parts[1]
                    values = parts[2:]
                if manual_variable and manual_variable not in manual_standard_variables:
                    if contains_manual_standard_flag(values) or contains_manual_standard_variable(values, manual_standard_variables):
                        manual_standard_variables.add(manual_variable)
                        changed = True
                if manual_variable and manual_variable not in target_feature_variables:
                    if contains_target_feature_override_values(values, target_feature_variables):
                        target_feature_variables.add(manual_variable)
                        changed = True
                if name in ('function', 'macro') and len(parts) >= 2:
                    tainted_parameters = variable_references(parts[1:]) & manual_standard_variables
                    new_parameters = {parameter for parameter in parts[1:] if parameter in tainted_parameters}
                    if not new_parameters.issubset(manual_standard_variables):
                        manual_standard_variables.update(new_parameters)
                        changed = True
                    target_feature_parameters = variable_references(parts[1:]) & target_feature_variables
                    new_target_feature_parameters = {parameter for parameter in parts[1:] if parameter in target_feature_parameters}
                    if not new_target_feature_parameters.issubset(target_feature_variables):
                        target_feature_variables.update(new_target_feature_parameters)
                        changed = True
                if name in wrapper_sink_parameters and parts:
                    wrapper_name = name
                    call_arguments = parts
                    for parameters, sink_parameters in wrapper_sink_parameters[wrapper_name]:
                        argument_parts = wrapper_sink_argument_parts(call_arguments, parameters, sink_parameters)
                        newly_tainted = variable_references(argument_parts) & manual_standard_variables
                        if not newly_tainted.issubset(manual_standard_variables):
                            manual_standard_variables.update(newly_tainted)
                            changed = True
                if name == 'foreach' and len(parts) >= 2:
                    loop_variable = parts[0]
                    if loop_variable not in manual_standard_variables:
                        values = parts[1:]
                        if foreach_values_contain_manual_standard(values, manual_standard_variables):
                            manual_standard_variables.add(loop_variable)
                            changed = True
                    if loop_variable not in target_feature_variables:
                        values = parts[1:]
                        if foreach_values_contain_target_feature(values, target_feature_variables):
                            target_feature_variables.add(loop_variable)
                            changed = True

    target_overrides = []
    manual_standard_flags = []
    extension_overrides = []
    target_feature_overrides = []
    for path in iter_source_cmake_files(root):
        for index, command in cmake_commands(path):
            name = cmake_command_name(command)
            parsed = parse_cmake_set(command)
            if name in ('set_target_properties', 'set_property') and has_target_property_override(command):
                target_overrides.append((path, index, command))
            if has_target_feature_override(command, target_feature_variables) or has_target_feature_wrapper_call(command, target_feature_variables, wrapper_target_feature_parameters):
                target_feature_overrides.append((path, index, command))
            if parsed and parsed[0] in REQUIRED_TOP_LEVEL_CONTRACT:
                parsed_value = normalize_contract_value(parsed[0], parsed[1])
                if parsed_value != REQUIRED_TOP_LEVEL_CONTRACT[parsed[0]] or path != top:
                    extension_overrides.append((path, index, command))
            if has_manual_standard_flag(command, manual_standard_variables) or has_manual_standard_wrapper_call(command, manual_standard_variables, wrapper_sink_parameters):
                manual_standard_flags.append((path, index, command))

    repo_root = root.parent
    script_standard_flags = []
    for path in iter_script_scan_files(repo_root):
        for index, line in enumerate(path.read_text().splitlines(), 1):
            stripped = strip_script_comment(line)
            if not stripped or allowed_script_standard_line(stripped):
                continue
            if any(marker in stripped for marker in SCRIPT_STANDARD_MARKERS):
                script_standard_flags.append((path, index, stripped))

    if target_overrides:
        path, index, stripped = target_overrides[0]
        fail(f'target-level C++ standard override: {stripped}', path, index)
    if target_feature_overrides:
        path, index, stripped = target_feature_overrides[0]
        fail(f'target-level C++ compile feature override: {stripped}', path, index)
    if extension_overrides:
        path, index, stripped = extension_overrides[0]
        fail(f'CMake GNU++20 contract drift: {stripped}', path, index)
    if manual_standard_flags:
        path, index, stripped = manual_standard_flags[0]
        fail(f'manual C++ standard flag in CMake: {stripped}', path, index)
    if script_standard_flags:
        path, index, stripped = script_standard_flags[0]
        fail(f'manual C++ standard flag in workflow/helper: {stripped}', path, index)


def main():
    parser = argparse.ArgumentParser(description='Check the project-wide GNU++20 CMake contract')
    parser.add_argument('source_dir', nargs='?', default='source')
    args = parser.parse_args()
    check_contract(args.source_dir)
    print('CMake GNU++20 contract validated')


if __name__ == '__main__':
    main()
