#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_cmake_cxx20_contract.py')

BASE_CMAKELISTS = '''
cmake_minimum_required(VERSION 3.20)
project(x265)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)
'''


def write_source(root, top_text=BASE_CMAKELISTS):
    source = root / 'source'
    source.mkdir(parents=True, exist_ok=True)
    (source / 'CMakeLists.txt').write_text(top_text)
    return source


def run_checker(source_dir):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(source_dir)],
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
        source = write_source(root)
        expect_pass(run_checker(source))

        cache_top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        set(CMAKE_CXX_STANDARD 20 CACHE STRING "" FORCE)
        set(CMAKE_CXX_STANDARD_REQUIRED ON CACHE BOOL "" FORCE)
        set(CMAKE_CXX_EXTENSIONS ON CACHE BOOL "" FORCE)
        '''
        cache_source = write_source(root / 'cache-contract', cache_top_text)
        expect_pass(run_checker(cache_source))

        lowercase_cache_top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        set(CMAKE_CXX_STANDARD 20 CACHE STRING "" FORCE)
        set(CMAKE_CXX_STANDARD_REQUIRED on CACHE BOOL "" FORCE)
        set(CMAKE_CXX_EXTENSIONS on CACHE BOOL "" FORCE)
        '''
        lowercase_cache_source = write_source(root / 'lowercase-cache-contract', lowercase_cache_top_text)
        expect_pass(run_checker(lowercase_cache_source))

        quoted_contract_top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        set(CMAKE_CXX_STANDARD "20")
        set(CMAKE_CXX_STANDARD_REQUIRED [=[ON]=])
        set(CMAKE_CXX_EXTENSIONS "ON")
        '''
        quoted_contract_source = write_source(root / 'quoted-contract-values', quoted_contract_top_text)
        expect_pass(run_checker(quoted_contract_source))

        inline_cache_top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        set(CMAKE_CXX_STANDARD 20 CACHE STRING "project standard" FORCE) # keep cache callers aligned
        set(CMAKE_CXX_STANDARD_REQUIRED ON CACHE BOOL "" FORCE)
        set(CMAKE_CXX_EXTENSIONS ON CACHE BOOL "" FORCE)
        '''
        inline_cache_source = write_source(root / 'inline-cache-contract', inline_cache_top_text)
        expect_pass(run_checker(inline_cache_source))

        cache_internal_docs_source = write_source(root / 'cache-internal-docs-pass')
        cache_internal_docs_nested = cache_internal_docs_source / 'cmake'
        cache_internal_docs_nested.mkdir()
        (cache_internal_docs_nested / 'docs.cmake').write_text('set(MY_CXX_FLAGS_DOC "-std=gnu++17 docs only" CACHE INTERNAL "" FORCE)\n')
        expect_pass(run_checker(cache_internal_docs_source))

        readonly_source = write_source(root / 'readonly-property')
        readonly_nested = readonly_source / 'cmake'
        readonly_nested.mkdir()
        (readonly_nested / 'query.cmake').write_text('get_property(current TARGET cli PROPERTY CXX_STANDARD)\n')
        expect_pass(run_checker(readonly_source))

        imported_alias_readonly_source = write_source(root / 'imported-alias-readonly-properties-pass')
        imported_alias_readonly_nested = imported_alias_readonly_source / 'cmake'
        imported_alias_readonly_nested.mkdir()
        (imported_alias_readonly_nested / 'query.cmake').write_text('''
        add_library(cli_import UNKNOWN IMPORTED)
        add_library(cli_alias ALIAS cli_import)
        get_target_property(alias_target cli_alias ALIASED_TARGET)
        get_property(imported_global TARGET cli_import PROPERTY IMPORTED_GLOBAL)
        get_property(source_compile_options SOURCE probe.cpp PROPERTY COMPILE_OPTIONS)
        get_property(directory_compile_options DIRECTORY PROPERTY COMPILE_OPTIONS)
        ''')
        expect_pass(run_checker(imported_alias_readonly_source))

        comment_whitespace_source = write_source(root / 'comment-whitespace')
        comment_whitespace_nested = comment_whitespace_source / 'cmake'
        comment_whitespace_nested.mkdir()
        (comment_whitespace_nested / 'noisy.cmake').write_text('''
        # set(CMAKE_CXX_STANDARD 17)
           # set(CMAKE_CXX_STANDARD_REQUIRED OFF)
        # target_compile_options(cli PRIVATE "$<$<COMPILE_LANGUAGE:CXX>:-std=gnu++17>")
        # target_compile_features(cli PRIVATE cxx_std_17)

        get_target_property(cli_standard cli CXX_STANDARD)
        get_property(current TARGET cli PROPERTY CXX_STANDARD)
        ''')
        expect_pass(run_checker(comment_whitespace_source))

        bracket_comment_source = write_source(root / 'bracket-comment')
        bracket_comment_nested = bracket_comment_source / 'cmake'
        bracket_comment_nested.mkdir()
        (bracket_comment_nested / 'noisy.cmake').write_text('''
        #[[ set(CMAKE_CXX_STANDARD 17) ]]
        #[=[ set(CMAKE_CXX_EXTENSIONS OFF) ]=]
        #[==[
        target_compile_options(cli PRIVATE -std=gnu++17)
        set_target_properties(cli PROPERTIES CXX_STANDARD 17)
        ]==]
        get_property(current TARGET cli PROPERTY CXX_STANDARD)
        ''')
        expect_pass(run_checker(bracket_comment_source))

        unterminated_bracket_comment_source = write_source(root / 'unterminated-bracket-comment')
        unterminated_bracket_comment_nested = unterminated_bracket_comment_source / 'cmake'
        unterminated_bracket_comment_nested.mkdir()
        (unterminated_bracket_comment_nested / 'noisy.cmake').write_text('''
        #[=[
        set(CMAKE_CXX_STANDARD 17)
        target_compile_options(cli PRIVATE -std=gnu++17)
        ''')
        expect_pass(run_checker(unterminated_bracket_comment_source))

        closed_bracket_comment_then_command_source = write_source(root / 'closed-bracket-comment-then-command')
        closed_bracket_comment_then_command_nested = closed_bracket_comment_then_command_source / 'cmake'
        closed_bracket_comment_then_command_nested.mkdir()
        (closed_bracket_comment_then_command_nested / 'flags.cmake').write_text('#[[ target_compile_options(cli PRIVATE -std=gnu++17) ]] add_compile_options(-std=gnu++17)\n')
        expect_fail(run_checker(closed_bracket_comment_then_command_source), 'manual C++ standard flag in CMake')

        legal_property_source = write_source(root / 'legal-target-properties')
        legal_property_nested = legal_property_source / 'cmake'
        legal_property_nested.mkdir()
        (legal_property_nested / 'properties.cmake').write_text('''
        set_target_properties(cli PROPERTIES
                              OUTPUT_NAME x265
                              RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
        set_property(TARGET cli PROPERTY FOLDER tools) # target_compile_options(cli PRIVATE -std=gnu++17)
        set_property(TARGET cli PROPERTY LABELS keep) #[[ set_property(TARGET cli PROPERTY CXX_STANDARD 17) ]]
        ''')
        expect_pass(run_checker(legal_property_source))

        bracket_argument_source = write_source(root / 'bracket-argument-values')
        bracket_argument_nested = bracket_argument_source / 'cmake'
        bracket_argument_nested.mkdir()
        (bracket_argument_nested / 'properties.cmake').write_text('''
        set_target_properties(cli PROPERTIES
                              OUTPUT_NAME [=[x 265]=]
                              RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
        string(APPEND MY_CXX_FLAGS_DOC [=[ -std=gnu++17 appears in docs ]=])
        ''')
        expect_pass(run_checker(bracket_argument_source))

        block_string_replace_docs_source = write_source(root / 'block-string-replace-docs-pass')
        block_string_replace_docs_nested = block_string_replace_docs_source / 'cmake'
        block_string_replace_docs_nested.mkdir()
        (block_string_replace_docs_nested / 'docs.cmake').write_text('''
        block()
          string(REPLACE "-std=gnu++17" "gnu++17" MY_CXX_FLAGS_DOC "-std=gnu++17 docs only")
        endblock()
        ''')
        expect_pass(run_checker(block_string_replace_docs_source))

        legal_feature_source = write_source(root / 'legal-target-features')
        legal_feature_nested = legal_feature_source / 'cmake'
        legal_feature_nested.mkdir()
        (legal_feature_nested / 'features.cmake').write_text('''
        set(cxx_std_feature cxx_constexpr)
        target_compile_features(cli PRIVATE cxx_constexpr cxx_lambdas ${cxx_std_feature})
        ''')
        expect_pass(run_checker(legal_feature_source))

        public_standard_feature_source = write_source(root / 'public-standard-target-feature')
        public_standard_feature_nested = public_standard_feature_source / 'cmake'
        public_standard_feature_nested.mkdir()
        (public_standard_feature_nested / 'features.cmake').write_text('target_compile_features(cli PUBLIC cxx_std_17)\n')
        expect_fail(run_checker(public_standard_feature_source), 'target-level C++ compile feature override')

        bracket_comment_feature_source = write_source(root / 'bracket-comment-target-feature')
        bracket_comment_feature_nested = bracket_comment_feature_source / 'cmake'
        bracket_comment_feature_nested.mkdir()
        (bracket_comment_feature_nested / 'features.cmake').write_text('''
        #[[
        target_compile_features(cli PUBLIC cxx_std_17)
        target_compile_options(cli PRIVATE "$<$<COMPILE_LANGUAGE:CXX>:-std=c++17>")
        set_directory_properties(PROPERTIES COMPILE_OPTIONS -std=gnu++17)
        ]]
        target_compile_features(cli PRIVATE cxx_constexpr)
        ''')
        expect_pass(run_checker(bracket_comment_feature_source))

        generator_standard_flag_source = write_source(root / 'generator-expression-standard-flag')
        generator_standard_flag_nested = generator_standard_flag_source / 'cmake'
        generator_standard_flag_nested.mkdir()
        (generator_standard_flag_nested / 'flags.cmake').write_text('target_compile_options(cli PRIVATE "$<$<COMPILE_LANGUAGE:CXX>:-std=c++17>")\n')
        expect_fail(run_checker(generator_standard_flag_source), 'manual C++ standard flag in CMake')

        bracket_argument_override_source = write_source(root / 'bracket-argument-standard-override')
        bracket_argument_override_nested = bracket_argument_override_source / 'cmake'
        bracket_argument_override_nested.mkdir()
        (bracket_argument_override_nested / 'properties.cmake').write_text('''
        set_target_properties(cli PROPERTIES
                              OUTPUT_NAME [=[x 265]=]
                              CXX_STANDARD 17)
        ''')
        expect_fail(run_checker(bracket_argument_override_source), 'target-level C++ standard override')

        append_property_override_source = write_source(root / 'append-property-standard-override')
        append_property_override_nested = append_property_override_source / 'cmake'
        append_property_override_nested.mkdir()
        (append_property_override_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND PROPERTY CXX_STANDARD 20)\n')
        expect_fail(run_checker(append_property_override_source), 'target-level C++ standard override')

        append_string_property_override_source = write_source(root / 'append-string-property-standard-override')
        append_string_property_override_nested = append_string_property_override_source / 'cmake'
        append_string_property_override_nested.mkdir()
        (append_string_property_override_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND_STRING PROPERTY CXX_EXTENSIONS ON)\n')
        expect_fail(run_checker(append_string_property_override_source), 'target-level C++ standard override')

        lowercase_property_override_source = write_source(root / 'lowercase-property-standard-override')
        lowercase_property_override_nested = lowercase_property_override_source / 'cmake'
        lowercase_property_override_nested.mkdir()
        (lowercase_property_override_nested / 'properties.cmake').write_text('set_property(target cli append_string property cxx_extensions ON)\n')
        expect_fail(run_checker(lowercase_property_override_source), 'target-level C++ standard override')

        lowercase_compile_property_source = write_source(root / 'lowercase-compile-property-standard-flag')
        lowercase_compile_property_nested = lowercase_compile_property_source / 'cmake'
        lowercase_compile_property_nested.mkdir()
        (lowercase_compile_property_nested / 'flags.cmake').write_text('set_source_files_properties(probe.cpp properties compile_options -std=gnu++17)\n')
        expect_fail(run_checker(lowercase_compile_property_source), 'manual C++ standard flag in CMake')

        property_value_source = write_source(root / 'property-values')
        property_value_nested = property_value_source / 'cmake'
        property_value_nested.mkdir()
        (property_value_nested / 'properties.cmake').write_text('''
        set_target_properties(cli PROPERTIES
                              OUTPUT_NAME CXX_STANDARD
                              RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
        set_property(TARGET cli PROPERTY VS_DEBUGGER_WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/CXX_STANDARD)
        set_property(DIRECTORY PROPERTY CXX_STANDARD documentation-only)
        set_property(GLOBAL PROPERTY CXX_EXTENSIONS documentation-only)
        set_property(SOURCE probe.cpp PROPERTY CXX_STANDARD documentation-only)
        ''')
        expect_pass(run_checker(property_value_source))

        with_script_source = write_source(root / 'script-scan-py-sh-pass')
        scripts = root / '.github' / 'scripts'
        scripts.mkdir(parents=True)
        (scripts / 'helper.py').write_text('print("GNU++20 helper without manual flags")\n')
        (scripts / 'helper.sh').write_text('cmake -S source # docs mention -DCMAKE_CXX_STANDARD_REQUIRED=OFF as forbidden\n')
        expect_pass(run_checker(with_script_source))

        bad_python_root = root / 'script-scan-py-fail'
        bad_python_script_source = write_source(bad_python_root)
        bad_scripts = bad_python_root / '.github' / 'scripts'
        bad_scripts.mkdir(parents=True)
        (bad_scripts / 'helper.py').write_text('flags = "-std=gnu++17"\n')
        expect_fail(run_checker(bad_python_script_source), 'manual C++ standard flag in workflow/helper')

        bad_shell_root = root / 'script-scan-sh-fail'
        bad_shell_script_source = write_source(bad_shell_root)
        bad_scripts = bad_shell_root / '.github' / 'scripts'
        bad_scripts.mkdir(parents=True)
        (bad_scripts / 'helper.sh').write_text('cmake -DCMAKE_CXX_EXTENSIONS=OFF source\n')
        expect_fail(run_checker(bad_shell_script_source), 'manual C++ standard flag in workflow/helper')

        generator_expression_source = write_source(root / 'generator-expression-string')
        generator_expression_nested = generator_expression_source / 'cmake'
        generator_expression_nested.mkdir()
        (generator_expression_nested / 'generator.cmake').write_text('''
        set(cli_feature_probe "$<BOOL:cxx_std_20>")
        set(cli_warning_text "$<$<CONFIG:Debug>:-std=gnu++17 is forbidden>")
        set_property(TARGET cli PROPERTY LABELS "$<IF:$<BOOL:1>,CXX_STANDARD,plain>")
        ''')
        expect_pass(run_checker(generator_expression_source))

        multidirectory_source = write_source(root / 'multidirectory-properties', BASE_CMAKELISTS + 'add_subdirectory(extras)\n')
        multidirectory_nested = multidirectory_source / 'extras'
        multidirectory_nested.mkdir()
        (multidirectory_nested / 'CMakeLists.txt').write_text('set_property(TARGET cli PROPERTY FOLDER extras)\n')
        expect_pass(run_checker(multidirectory_source))

        multidirectory_include_source = write_source(root / 'multidirectory-include', BASE_CMAKELISTS + 'add_subdirectory(extras)\n')
        multidirectory_include_nested = multidirectory_include_source / 'extras'
        multidirectory_include_nested.mkdir()
        (multidirectory_include_nested / 'CMakeLists.txt').write_text('include(local.cmake)\n')
        (multidirectory_include_nested / 'local.cmake').write_text('set_property(TARGET cli PROPERTY FOLDER extras)\n')
        expect_pass(run_checker(multidirectory_include_source))

        included_generator_source = write_source(root / 'included-generator-expression', BASE_CMAKELISTS + 'include(cmake/generator.cmake)\n')
        included_generator_nested = included_generator_source / 'cmake'
        included_generator_nested.mkdir()
        (included_generator_nested / 'generator.cmake').write_text('''
        target_compile_options(cli PRIVATE "$<$<CONFIG:Debug>:-Wextra>")
        set_property(TARGET cli PROPERTY COMPILE_OPTIONS "$<$<CONFIG:Debug>:-Wshadow>")
        ''')
        expect_pass(run_checker(included_generator_source))

        wrapped_flags_pass_source = write_source(root / 'wrapped-flags-pass')
        wrapped_flags_pass_nested = wrapped_flags_pass_source / 'cmake'
        wrapped_flags_pass_nested.mkdir()
        (wrapped_flags_pass_nested / 'flags.cmake').write_text('''
        set(X265_COMPILE_OPTIONS -Wall -Wextra)
        list(APPEND X265_COMPILE_OPTIONS -Wshadow)
        list(APPEND X265_LINK_OPTIONS -static)
        x265_add_option(-Wextra)
        x265_add_definitions(-DENABLE_LAVF)
        custom_note("-std=gnu++17 appears in docs only")
        ''')
        expect_pass(run_checker(wrapped_flags_pass_source))

        string_docs_source = write_source(root / 'string-docs-pass')
        string_docs_nested = string_docs_source / 'cmake'
        string_docs_nested.mkdir()
        (string_docs_nested / 'docs.cmake').write_text('''
        string(APPEND MY_CXX_FLAGS_DOC " -std=gnu++17 appears in docs")
        string(APPEND MY_CXX_FLAGS_COMMENT " -std=gnu++17 appears in comments")
        string(APPEND MY_CXX_FLAGS_DESCRIPTION [=[ -std=gnu++17 appears in descriptions ]=])
        ''')
        expect_pass(run_checker(string_docs_source))

        quoted_paren_source = write_source(root / 'quoted-paren-command')
        quoted_paren_nested = quoted_paren_source / 'cmake'
        quoted_paren_nested.mkdir()
        (quoted_paren_nested / 'flags.cmake').write_text('''
        target_compile_options(cli PRIVATE
                               "$<$<BOOL:1>:-Wmessage=(kept)>")
        set_property(TARGET cli PROPERTY LABELS "literal ) in label")
        add_compile_options(-Wextra)
        ''')
        expect_pass(run_checker(quoted_paren_source))

        quoted_paren_manual_source = write_source(root / 'quoted-paren-manual-standard')
        quoted_paren_manual_nested = quoted_paren_manual_source / 'cmake'
        quoted_paren_manual_nested.mkdir()
        (quoted_paren_manual_nested / 'flags.cmake').write_text('''
        target_compile_options(cli PRIVATE
                               "$<$<BOOL:1>:-Wmessage=(kept)>")
        add_compile_options(-std=gnu++17)
        ''')
        expect_fail(run_checker(quoted_paren_manual_source), 'manual C++ standard flag in CMake')

        indirect_standard_flag_source = write_source(root / 'indirect-standard-flag')
        indirect_standard_flag_nested = indirect_standard_flag_source / 'cmake'
        indirect_standard_flag_nested.mkdir()
        (indirect_standard_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        target_compile_options(cli PRIVATE ${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(indirect_standard_flag_source), 'manual C++ standard flag in CMake')

        indirect_wrapper_flag_source = write_source(root / 'indirect-wrapper-standard-flag')
        indirect_wrapper_flag_nested = indirect_wrapper_flag_source / 'cmake'
        indirect_wrapper_flag_nested.mkdir()
        (indirect_wrapper_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        x265_add_option(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(indirect_wrapper_flag_source), 'manual C++ standard flag in CMake')

        indirect_property_flag_source = write_source(root / 'indirect-property-standard-flag')
        indirect_property_flag_nested = indirect_property_flag_source / 'cmake'
        indirect_property_flag_nested.mkdir()
        (indirect_property_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS ${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(indirect_property_flag_source), 'manual C++ standard flag in CMake')

        chained_indirect_standard_flag_source = write_source(root / 'chained-indirect-standard-flag')
        chained_indirect_standard_flag_nested = chained_indirect_standard_flag_source / 'cmake'
        chained_indirect_standard_flag_nested.mkdir()
        (chained_indirect_standard_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set(LOCAL_CXX_OPTIONS ${LOCAL_STD_FLAG})
        target_compile_options(cli PRIVATE ${LOCAL_CXX_OPTIONS})
        ''')
        expect_fail(run_checker(chained_indirect_standard_flag_source), 'manual C++ standard flag in CMake')

        chained_compile_variable_source = write_source(root / 'chained-compile-variable-standard-flag')
        chained_compile_variable_nested = chained_compile_variable_source / 'cmake'
        chained_compile_variable_nested.mkdir()
        (chained_compile_variable_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set(X265_CXX_FLAGS ${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(chained_compile_variable_source), 'manual C++ standard flag in CMake')

        chained_interface_property_source = write_source(root / 'chained-interface-property-standard-flag')
        chained_interface_property_nested = chained_interface_property_source / 'cmake'
        chained_interface_property_nested.mkdir()
        (chained_interface_property_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set(LOCAL_INTERFACE_FLAGS ${LOCAL_STD_FLAG})
        set_property(TARGET cli APPEND PROPERTY INTERFACE_COMPILE_OPTIONS ${LOCAL_INTERFACE_FLAGS})
        ''')
        expect_fail(run_checker(chained_interface_property_source), 'manual C++ standard flag in CMake')

        chained_target_properties_flag_source = write_source(root / 'chained-target-properties-standard-flag')
        chained_target_properties_flag_nested = chained_target_properties_flag_source / 'cmake'
        chained_target_properties_flag_nested.mkdir()
        (chained_target_properties_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set(LOCAL_COMPILE_FLAGS ${LOCAL_STD_FLAG})
        set_target_properties(cli PROPERTIES COMPILE_FLAGS ${LOCAL_COMPILE_FLAGS})
        ''')
        expect_fail(run_checker(chained_target_properties_flag_source), 'manual C++ standard flag in CMake')

        cached_indirect_standard_flag_source = write_source(root / 'cached-indirect-standard-flag')
        cached_indirect_standard_flag_nested = cached_indirect_standard_flag_source / 'cmake'
        cached_indirect_standard_flag_nested.mkdir()
        (cached_indirect_standard_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set(CACHED_STD_FLAG ${LOCAL_STD_FLAG} CACHE INTERNAL "" FORCE)
        target_compile_options(cli PRIVATE ${CACHED_STD_FLAG})
        ''')
        expect_fail(run_checker(cached_indirect_standard_flag_source), 'manual C++ standard flag in CMake')

        cached_wrapper_standard_flag_source = write_source(root / 'cached-wrapper-standard-flag')
        cached_wrapper_standard_flag_nested = cached_wrapper_standard_flag_source / 'cmake'
        cached_wrapper_standard_flag_nested.mkdir()
        (cached_wrapper_standard_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set(CACHED_STD_FLAG ${LOCAL_STD_FLAG} CACHE STRING "" FORCE)
        x265_add_option(${CACHED_STD_FLAG})
        ''')
        expect_fail(run_checker(cached_wrapper_standard_flag_source), 'manual C++ standard flag in CMake')

        wrapped_compile_option_source = write_source(root / 'wrapped-compile-option')
        wrapped_compile_option_nested = wrapped_compile_option_source / 'cmake'
        wrapped_compile_option_nested.mkdir()
        (wrapped_compile_option_nested / 'flags.cmake').write_text('x265_add_option(-std=gnu++17)\n')
        expect_fail(run_checker(wrapped_compile_option_source), 'manual C++ standard flag in CMake')

        wrapped_compile_definitions_source = write_source(root / 'wrapped-compile-definitions')
        wrapped_compile_definitions_nested = wrapped_compile_definitions_source / 'cmake'
        wrapped_compile_definitions_nested.mkdir()
        (wrapped_compile_definitions_nested / 'flags.cmake').write_text('x265_add_definitions(/std:c++17)\n')
        expect_fail(run_checker(wrapped_compile_definitions_source), 'manual C++ standard flag in CMake')

        list_compile_options_source = write_source(root / 'list-compile-options')
        list_compile_options_nested = list_compile_options_source / 'cmake'
        list_compile_options_nested.mkdir()
        (list_compile_options_nested / 'flags.cmake').write_text('list(APPEND X265_COMPILE_OPTIONS -std=gnu++17)\n')
        expect_fail(run_checker(list_compile_options_source), 'manual C++ standard flag in CMake')

        list_append_indirect_compile_options_source = write_source(root / 'list-append-indirect-compile-options')
        list_append_indirect_compile_options_nested = list_append_indirect_compile_options_source / 'cmake'
        list_append_indirect_compile_options_nested.mkdir()
        (list_append_indirect_compile_options_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        list(APPEND PROJECT_CXX_FLAGS ${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(list_append_indirect_compile_options_source), 'manual C++ standard flag in CMake')

        list_filter_compile_flags_source = write_source(root / 'list-filter-compile-flags-pass')
        list_filter_compile_flags_nested = list_filter_compile_flags_source / 'cmake'
        list_filter_compile_flags_nested.mkdir()
        (list_filter_compile_flags_nested / 'flags.cmake').write_text('''
        set(PROJECT_CXX_FLAGS -Wextra -Wshadow)
        list(FILTER PROJECT_CXX_FLAGS INCLUDE REGEX "^-W")
        list(FILTER PROJECT_CXX_FLAGS EXCLUDE REGEX "-std=gnu\\+\\+17")
        ''')
        expect_pass(run_checker(list_filter_compile_flags_source))

        set_compile_options_source = write_source(root / 'set-compile-options')
        set_compile_options_nested = set_compile_options_source / 'cmake'
        set_compile_options_nested.mkdir()
        (set_compile_options_nested / 'flags.cmake').write_text('set(X265_CXX_FLAGS "${X265_CXX_FLAGS} -std=c++20")\n')
        expect_fail(run_checker(set_compile_options_source), 'manual C++ standard flag in CMake')

        toolchain_list_source = write_source(root / 'toolchain-list-flags')
        toolchain_list_nested = toolchain_list_source / 'cmake'
        toolchain_list_nested.mkdir()
        (toolchain_list_nested / 'toolchain.cmake').write_text('list(PREPEND PROJECT_CXX_FLAGS -std=gnu++17)\n')
        expect_fail(run_checker(toolchain_list_source), 'manual C++ standard flag in CMake')

        string_compile_flags_source = write_source(root / 'string-compile-flags')
        string_compile_flags_nested = string_compile_flags_source / 'cmake'
        string_compile_flags_nested.mkdir()
        (string_compile_flags_nested / 'flags.cmake').write_text('''
        function(add_local_flags)
          string(APPEND CMAKE_CXX_FLAGS " -std=gnu++17")
        endfunction()
        ''')
        expect_fail(run_checker(string_compile_flags_source), 'manual C++ standard flag in CMake')

        macro_toolchain_string_source = write_source(root / 'macro-toolchain-string-flags')
        macro_toolchain_string_nested = macro_toolchain_string_source / 'cmake'
        macro_toolchain_string_nested.mkdir()
        (macro_toolchain_string_nested / 'toolchain.cmake').write_text('''
        macro(add_project_flags)
          string(PREPEND PROJECT_CXX_FLAGS "-std=gnu++17 ")
        endmacro()
        ''')
        expect_fail(run_checker(macro_toolchain_string_source), 'manual C++ standard flag in CMake')

        string_concat_compile_flags_source = write_source(root / 'string-concat-compile-flags')
        string_concat_compile_flags_nested = string_concat_compile_flags_source / 'cmake'
        string_concat_compile_flags_nested.mkdir()
        (string_concat_compile_flags_nested / 'flags.cmake').write_text('string(CONCAT CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS} " -std=gnu++17")\n')
        expect_fail(run_checker(string_concat_compile_flags_source), 'manual C++ standard flag in CMake')

        string_append_indirect_compile_options_source = write_source(root / 'string-append-indirect-compile-options')
        string_append_indirect_compile_options_nested = string_append_indirect_compile_options_source / 'cmake'
        string_append_indirect_compile_options_nested.mkdir()
        (string_append_indirect_compile_options_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        string(APPEND PROJECT_CXX_FLAGS " ${LOCAL_STD_FLAG}")
        ''')
        expect_fail(run_checker(string_append_indirect_compile_options_source), 'manual C++ standard flag in CMake')

        string_replace_compile_flags_source = write_source(root / 'string-replace-compile-flags-pass')
        string_replace_compile_flags_nested = string_replace_compile_flags_source / 'cmake'
        string_replace_compile_flags_nested.mkdir()
        (string_replace_compile_flags_nested / 'flags.cmake').write_text('''
        set(PROJECT_CXX_FLAGS -Wextra)
        string(REPLACE "-std=gnu++17" "-Wextra" PROJECT_CXX_FLAGS "${PROJECT_CXX_FLAGS}")
        ''')
        expect_pass(run_checker(string_replace_compile_flags_source))

        list_insert_indirect_compile_options_source = write_source(root / 'list-insert-indirect-compile-options')
        list_insert_indirect_compile_options_nested = list_insert_indirect_compile_options_source / 'cmake'
        list_insert_indirect_compile_options_nested.mkdir()
        (list_insert_indirect_compile_options_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        list(INSERT PROJECT_CXX_FLAGS 0 ${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(list_insert_indirect_compile_options_source), 'manual C++ standard flag in CMake')

        lowercase_string_concat_indirect_compile_flags_source = write_source(root / 'lowercase-string-concat-indirect-compile-flags')
        lowercase_string_concat_indirect_compile_flags_nested = lowercase_string_concat_indirect_compile_flags_source / 'cmake'
        lowercase_string_concat_indirect_compile_flags_nested.mkdir()
        (lowercase_string_concat_indirect_compile_flags_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        string(concat project_cxx_flags ${LOCAL_STD_FLAG} " -Wextra")
        ''')
        expect_fail(run_checker(lowercase_string_concat_indirect_compile_flags_source), 'manual C++ standard flag in CMake')

        set_target_properties_quoted_compile_options_source = write_source(root / 'set-target-properties-quoted-compile-options')
        set_target_properties_quoted_compile_options_nested = set_target_properties_quoted_compile_options_source / 'cmake'
        set_target_properties_quoted_compile_options_nested.mkdir()
        (set_target_properties_quoted_compile_options_nested / 'flags.cmake').write_text('set_target_properties(cli PROPERTIES COMPILE_OPTIONS "-std=gnu++17")\n')
        expect_fail(run_checker(set_target_properties_quoted_compile_options_source), 'manual C++ standard flag in CMake')

        set_property_quoted_indirect_compile_options_source = write_source(root / 'set-property-quoted-indirect-compile-options')
        set_property_quoted_indirect_compile_options_nested = set_property_quoted_indirect_compile_options_source / 'cmake'
        set_property_quoted_indirect_compile_options_nested.mkdir()
        (set_property_quoted_indirect_compile_options_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set_property(TARGET cli PROPERTY COMPILE_OPTIONS "${LOCAL_STD_FLAG}")
        ''')
        expect_fail(run_checker(set_property_quoted_indirect_compile_options_source), 'manual C++ standard flag in CMake')

        function_parent_scope_source = write_source(root / 'function-parent-scope-flags')
        function_parent_scope_nested = function_parent_scope_source / 'cmake'
        function_parent_scope_nested.mkdir()
        (function_parent_scope_nested / 'flags.cmake').write_text('''
        function(add_parent_flags)
          set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++17" PARENT_SCOPE)
        endfunction()
        ''')
        expect_fail(run_checker(function_parent_scope_source), 'manual C++ standard flag in CMake')

        foreach_list_insert_source = write_source(root / 'foreach-list-insert-flags')
        foreach_list_insert_nested = foreach_list_insert_source / 'cmake'
        foreach_list_insert_nested.mkdir()
        (foreach_list_insert_nested / 'flags.cmake').write_text('''
        foreach(flag -Wall)
          list(INSERT CMAKE_CXX_FLAGS 0 -std=gnu++17)
        endforeach()
        ''')
        expect_fail(run_checker(foreach_list_insert_source), 'manual C++ standard flag in CMake')

        function_parameter_forward_source = write_source(root / 'function-parameter-forward-standard-flag')
        function_parameter_forward_nested = function_parameter_forward_source / 'cmake'
        function_parameter_forward_nested.mkdir()
        (function_parameter_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        function(add_cli_flags flag)
          target_compile_options(cli PRIVATE ${flag})
        endfunction()
        add_cli_flags(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(function_parameter_forward_source), 'manual C++ standard flag in CMake')

        macro_parameter_forward_source = write_source(root / 'macro-parameter-forward-standard-flag')
        macro_parameter_forward_nested = macro_parameter_forward_source / 'cmake'
        macro_parameter_forward_nested.mkdir()
        (macro_parameter_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        macro(add_cli_flags flag)
          set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS ${flag})
        endmacro()
        add_cli_flags(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(macro_parameter_forward_source), 'manual C++ standard flag in CMake')

        neutral_function_parameter_forward_source = write_source(root / 'neutral-function-parameter-forward-standard-flag')
        neutral_function_parameter_forward_nested = neutral_function_parameter_forward_source / 'cmake'
        neutral_function_parameter_forward_nested.mkdir()
        (neutral_function_parameter_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        function(forward_args flag)
          target_compile_options(cli PRIVATE ${flag})
        endfunction()
        forward_args(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(neutral_function_parameter_forward_source), 'manual C++ standard flag in CMake')

        neutral_macro_parameter_forward_source = write_source(root / 'neutral-macro-parameter-forward-standard-flag')
        neutral_macro_parameter_forward_nested = neutral_macro_parameter_forward_source / 'cmake'
        neutral_macro_parameter_forward_nested.mkdir()
        (neutral_macro_parameter_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        macro(forward_args flag)
          set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS ${flag})
        endmacro()
        forward_args(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(neutral_macro_parameter_forward_source), 'manual C++ standard flag in CMake')

        function_argn_forward_source = write_source(root / 'function-argn-forward-standard-flag')
        function_argn_forward_nested = function_argn_forward_source / 'cmake'
        function_argn_forward_nested.mkdir()
        (function_argn_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        function(add_cli_flags)
          target_compile_options(cli PRIVATE ${ARGN})
        endfunction()
        add_cli_flags(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(function_argn_forward_source), 'manual C++ standard flag in CMake')

        function_argv_forward_source = write_source(root / 'function-argv-forward-standard-flag')
        function_argv_forward_nested = function_argv_forward_source / 'cmake'
        function_argv_forward_nested.mkdir()
        (function_argv_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        function(add_cli_flags first second)
          set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS ${ARGV1})
        endfunction()
        add_cli_flags(-Wextra ${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(function_argv_forward_source), 'manual C++ standard flag in CMake')

        macro_argn_forward_source = write_source(root / 'macro-argn-forward-standard-flag')
        macro_argn_forward_nested = macro_argn_forward_source / 'cmake'
        macro_argn_forward_nested.mkdir()
        (macro_argn_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        macro(add_cli_flags)
          target_compile_options(cli PRIVATE ${ARGN})
        endmacro()
        add_cli_flags(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(macro_argn_forward_source), 'manual C++ standard flag in CMake')

        macro_argv_forward_source = write_source(root / 'macro-argv-forward-standard-flag')
        macro_argv_forward_nested = macro_argv_forward_source / 'cmake'
        macro_argv_forward_nested.mkdir()
        (macro_argv_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        macro(add_cli_flags first second)
          set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS ${ARGV1})
        endmacro()
        add_cli_flags(-Wextra ${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(macro_argv_forward_source), 'manual C++ standard flag in CMake')

        neutral_macro_argn_warning_flag_source = write_source(root / 'neutral-macro-argn-warning-flag-pass')
        neutral_macro_argn_warning_flag_nested = neutral_macro_argn_warning_flag_source / 'cmake'
        neutral_macro_argn_warning_flag_nested.mkdir()
        (neutral_macro_argn_warning_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_WARNING_FLAG -Wextra)
        macro(forward_args)
          target_compile_options(cli PRIVATE ${ARGN})
        endmacro()
        forward_args(${LOCAL_WARNING_FLAG})
        ''')
        expect_pass(run_checker(neutral_macro_argn_warning_flag_source))

        nested_function_parameter_forward_source = write_source(root / 'nested-function-parameter-forward-standard-flag')
        nested_function_parameter_forward_nested = nested_function_parameter_forward_source / 'cmake'
        nested_function_parameter_forward_nested.mkdir()
        (nested_function_parameter_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        function(add_cli_flags forwarded)
          target_compile_options(cli PRIVATE ${forwarded})
        endfunction()
        function(forward_to_cli flag)
          add_cli_flags(${flag})
        endfunction()
        forward_to_cli(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(nested_function_parameter_forward_source), 'manual C++ standard flag in CMake')

        nested_macro_parameter_forward_source = write_source(root / 'nested-macro-parameter-forward-standard-flag')
        nested_macro_parameter_forward_nested = nested_macro_parameter_forward_source / 'cmake'
        nested_macro_parameter_forward_nested.mkdir()
        (nested_macro_parameter_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        macro(add_cli_flags forwarded)
          set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS ${forwarded})
        endmacro()
        macro(forward_to_cli flag)
          add_cli_flags(${flag})
        endmacro()
        forward_to_cli(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(nested_macro_parameter_forward_source), 'manual C++ standard flag in CMake')

        neutral_wrapper_warning_flag_source = write_source(root / 'neutral-wrapper-warning-flag-pass')
        neutral_wrapper_warning_flag_nested = neutral_wrapper_warning_flag_source / 'cmake'
        neutral_wrapper_warning_flag_nested.mkdir()
        (neutral_wrapper_warning_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_WARNING_FLAG -Wextra)
        function(forward_args flag)
          target_compile_options(cli PRIVATE ${flag})
        endfunction()
        forward_args(${LOCAL_WARNING_FLAG})
        ''')
        expect_pass(run_checker(neutral_wrapper_warning_flag_source))

        nested_neutral_wrapper_warning_flag_source = write_source(root / 'nested-neutral-wrapper-warning-flag-pass')
        nested_neutral_wrapper_warning_flag_nested = nested_neutral_wrapper_warning_flag_source / 'cmake'
        nested_neutral_wrapper_warning_flag_nested.mkdir()
        (nested_neutral_wrapper_warning_flag_nested / 'flags.cmake').write_text('''
        set(LOCAL_WARNING_FLAG -Wextra)
        function(add_cli_flags forwarded)
          target_compile_options(cli PRIVATE ${forwarded})
        endfunction()
        function(forward_to_cli flag)
          add_cli_flags(${flag})
        endfunction()
        forward_to_cli(${LOCAL_WARNING_FLAG})
        ''')
        expect_pass(run_checker(nested_neutral_wrapper_warning_flag_source))

        function_source_property_forward_source = write_source(root / 'function-source-property-forward-standard-flag')
        function_source_property_forward_nested = function_source_property_forward_source / 'cmake'
        function_source_property_forward_nested.mkdir()
        (function_source_property_forward_nested / 'properties.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        function(add_source_flag flag)
          set_property(SOURCE probe.cpp APPEND PROPERTY COMPILE_OPTIONS ${flag})
        endfunction()
        add_source_flag(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(function_source_property_forward_source), 'manual C++ standard flag in CMake')

        macro_directory_property_forward_source = write_source(root / 'macro-directory-property-forward-standard-flag')
        macro_directory_property_forward_nested = macro_directory_property_forward_source / 'cmake'
        macro_directory_property_forward_nested.mkdir()
        (macro_directory_property_forward_nested / 'properties.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        macro(add_directory_flag flag)
          set_property(DIRECTORY APPEND PROPERTY COMPILE_OPTIONS ${flag})
        endmacro()
        add_directory_flag(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(macro_directory_property_forward_source), 'manual C++ standard flag in CMake')

        neutral_source_property_forward_source = write_source(root / 'neutral-source-property-forward-warning-pass')
        neutral_source_property_forward_nested = neutral_source_property_forward_source / 'cmake'
        neutral_source_property_forward_nested.mkdir()
        (neutral_source_property_forward_nested / 'properties.cmake').write_text('''
        set(LOCAL_WARNING_FLAG -Wextra)
        function(add_source_flag flag)
          set_property(SOURCE probe.cpp APPEND PROPERTY COMPILE_OPTIONS ${flag})
        endfunction()
        add_source_flag(${LOCAL_WARNING_FLAG})
        ''')
        expect_pass(run_checker(neutral_source_property_forward_source))

        neutral_directory_property_forward_source = write_source(root / 'neutral-directory-property-forward-warning-pass')
        neutral_directory_property_forward_nested = neutral_directory_property_forward_source / 'cmake'
        neutral_directory_property_forward_nested.mkdir()
        (neutral_directory_property_forward_nested / 'properties.cmake').write_text('''
        set(LOCAL_WARNING_FLAG -Wextra)
        macro(add_directory_flag flag)
          set_directory_properties(PROPERTIES COMPILE_OPTIONS ${flag})
        endmacro()
        add_directory_flag(${LOCAL_WARNING_FLAG})
        ''')
        expect_pass(run_checker(neutral_directory_property_forward_source))

        foreach_variable_forward_source = write_source(root / 'foreach-variable-forward-standard-flag')
        foreach_variable_forward_nested = foreach_variable_forward_source / 'cmake'
        foreach_variable_forward_nested.mkdir()
        (foreach_variable_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        foreach(flag ${LOCAL_STD_FLAG})
          target_compile_options(cli PRIVATE ${flag})
        endforeach()
        ''')
        expect_fail(run_checker(foreach_variable_forward_source), 'manual C++ standard flag in CMake')

        foreach_in_lists_forward_source = write_source(root / 'foreach-in-lists-forward-standard-flag')
        foreach_in_lists_forward_nested = foreach_in_lists_forward_source / 'cmake'
        foreach_in_lists_forward_nested.mkdir()
        (foreach_in_lists_forward_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        set(STD_FLAG_LIST ${LOCAL_STD_FLAG})
        foreach(flag IN LISTS STD_FLAG_LIST)
          target_compile_options(cli PRIVATE ${flag})
        endforeach()
        ''')
        expect_fail(run_checker(foreach_in_lists_forward_source), 'manual C++ standard flag in CMake')

        block_target_property_append_source = write_source(root / 'block-target-property-append-standard-flag')
        block_target_property_append_nested = block_target_property_append_source / 'cmake'
        block_target_property_append_nested.mkdir()
        (block_target_property_append_nested / 'properties.cmake').write_text('''
        set(LOCAL_STD_FLAG -std=gnu++17)
        block()
          set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS ${LOCAL_STD_FLAG})
        endblock()
        ''')
        expect_fail(run_checker(block_target_property_append_source), 'manual C++ standard flag in CMake')

        foreach_in_lists_doc_label_source = write_source(root / 'foreach-in-lists-doc-label-pass')
        foreach_in_lists_doc_label_nested = foreach_in_lists_doc_label_source / 'cmake'
        foreach_in_lists_doc_label_nested.mkdir()
        (foreach_in_lists_doc_label_nested / 'flags.cmake').write_text('''
        set(STD_FLAG_DOCS "-std=gnu++17 appears in docs")
        block()
          foreach(doc IN LISTS STD_FLAG_DOCS)
            set_property(TARGET cli PROPERTY LABELS ${doc})
          endforeach()
        endblock()
        ''')
        expect_pass(run_checker(foreach_in_lists_doc_label_source))

        foreach_in_items_wrapper_source = write_source(root / 'foreach-in-items-wrapper-standard-flag')
        foreach_in_items_wrapper_nested = foreach_in_items_wrapper_source / 'cmake'
        foreach_in_items_wrapper_nested.mkdir()
        (foreach_in_items_wrapper_nested / 'flags.cmake').write_text('''
        foreach(flag IN ITEMS -std=gnu++17)
          x265_add_option(${flag})
        endforeach()
        ''')
        expect_fail(run_checker(foreach_in_items_wrapper_source), 'manual C++ standard flag in CMake')

        foreach_in_items_wrapper_warning_source = write_source(root / 'foreach-in-items-wrapper-warning-pass')
        foreach_in_items_wrapper_warning_nested = foreach_in_items_wrapper_warning_source / 'cmake'
        foreach_in_items_wrapper_warning_nested.mkdir()
        (foreach_in_items_wrapper_warning_nested / 'flags.cmake').write_text('''
        foreach(flag IN ITEMS -Wextra)
          x265_add_option(${flag})
        endforeach()
        ''')
        expect_pass(run_checker(foreach_in_items_wrapper_warning_source))

        list_transform_compile_flags_source = write_source(root / 'list-transform-compile-flags-pass')
        list_transform_compile_flags_nested = list_transform_compile_flags_source / 'cmake'
        list_transform_compile_flags_nested.mkdir()
        (list_transform_compile_flags_nested / 'flags.cmake').write_text('''
        set(CMAKE_CXX_FLAGS -Wextra)
        list(TRANSFORM CMAKE_CXX_FLAGS PREPEND /clang:)
        ''')
        expect_pass(run_checker(list_transform_compile_flags_source))

        list_transform_docs_replace_source = write_source(root / 'list-transform-docs-replace-pass')
        list_transform_docs_replace_nested = list_transform_docs_replace_source / 'cmake'
        list_transform_docs_replace_nested.mkdir()
        (list_transform_docs_replace_nested / 'docs.cmake').write_text('''
        set(MY_CXX_FLAGS_DOC "-std=gnu++17 docs only")
        list(TRANSFORM MY_CXX_FLAGS_DOC REPLACE "-std=gnu++17" "gnu++17")
        ''')
        expect_pass(run_checker(list_transform_docs_replace_source))

        source_append_string_property_manual_source = write_source(root / 'source-append-string-property-manual-standard')
        source_append_string_property_manual_nested = source_append_string_property_manual_source / 'cmake'
        source_append_string_property_manual_nested.mkdir()
        (source_append_string_property_manual_nested / 'properties.cmake').write_text('set_property(SOURCE probe.cpp APPEND_STRING PROPERTY COMPILE_FLAGS ";-std=gnu++17")\n')
        expect_fail(run_checker(source_append_string_property_manual_source), 'manual C++ standard flag in CMake')

        target_compile_flags_semicolon_source = write_source(root / 'target-compile-flags-semicolon-standard')
        target_compile_flags_semicolon_nested = target_compile_flags_semicolon_source / 'cmake'
        target_compile_flags_semicolon_nested.mkdir()
        (target_compile_flags_semicolon_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND PROPERTY COMPILE_FLAGS "-Wall;-std=gnu++17")\n')
        expect_fail(run_checker(target_compile_flags_semicolon_source), 'manual C++ standard flag in CMake')

        lowercase_wrapper_generator_variable_source = write_source(root / 'lowercase-wrapper-generator-variable-standard-flag')
        lowercase_wrapper_generator_variable_nested = lowercase_wrapper_generator_variable_source / 'cmake'
        lowercase_wrapper_generator_variable_nested.mkdir()
        (lowercase_wrapper_generator_variable_nested / 'flags.cmake').write_text('''
        set(LOCAL_STD_FLAG "$<$<CONFIG:Debug>:-std=gnu++17>")
        x265_add_option(${LOCAL_STD_FLAG})
        ''')
        expect_fail(run_checker(lowercase_wrapper_generator_variable_source), 'manual C++ standard flag in CMake')

        included_manual_standard_source = write_source(root / 'included-manual-standard', BASE_CMAKELISTS + 'include(cmake/flags.cmake)\n')
        included_manual_standard_nested = included_manual_standard_source / 'cmake'
        included_manual_standard_nested.mkdir()
        (included_manual_standard_nested / 'flags.cmake').write_text('target_compile_options(cli PRIVATE "$<$<CONFIG:Debug>:-std=gnu++17>")\n')
        expect_fail(run_checker(included_manual_standard_source), 'manual C++ standard flag in CMake')

        included_feature_source = write_source(root / 'included-compile-feature', BASE_CMAKELISTS + 'include(cmake/features.cmake)\n')
        included_feature_nested = included_feature_source / 'cmake'
        included_feature_nested.mkdir()
        (included_feature_nested / 'features.cmake').write_text('target_compile_features(cli PRIVATE "$<$<COMPILE_LANGUAGE:CXX>:cxx_std_20>")\n')
        expect_fail(run_checker(included_feature_source), 'target-level C++ compile feature override')

        included_target_property_source = write_source(root / 'included-target-property', BASE_CMAKELISTS + 'include(cmake/properties.cmake)\n')
        included_target_property_nested = included_target_property_source / 'cmake'
        included_target_property_nested.mkdir()
        (included_target_property_nested / 'properties.cmake').write_text('set_property(TARGET cli PROPERTY CXX_STANDARD 17)\n')
        expect_fail(run_checker(included_target_property_source), 'target-level C++ standard override')

        included_target_property_same_value_source = write_source(root / 'included-target-property-same-value', BASE_CMAKELISTS + 'include(cmake/properties.cmake)\n')
        included_target_property_same_value_nested = included_target_property_same_value_source / 'cmake'
        included_target_property_same_value_nested.mkdir()
        (included_target_property_same_value_nested / 'properties.cmake').write_text('set_target_properties(cli PROPERTIES CXX_STANDARD 20)\n')
        expect_fail(run_checker(included_target_property_same_value_source), 'target-level C++ standard override')

        included_target_required_same_value_source = write_source(root / 'included-target-required-same-value', BASE_CMAKELISTS + 'include(cmake/properties.cmake)\n')
        included_target_required_same_value_nested = included_target_required_same_value_source / 'cmake'
        included_target_required_same_value_nested.mkdir()
        (included_target_required_same_value_nested / 'properties.cmake').write_text('set_property(TARGET cli PROPERTY CXX_STANDARD_REQUIRED ON)\n')
        expect_fail(run_checker(included_target_required_same_value_source), 'target-level C++ standard override')

        included_target_properties_required_same_value_source = write_source(root / 'included-target-properties-required-same-value', BASE_CMAKELISTS + 'include(cmake/properties.cmake)\n')
        included_target_properties_required_same_value_nested = included_target_properties_required_same_value_source / 'cmake'
        included_target_properties_required_same_value_nested.mkdir()
        (included_target_properties_required_same_value_nested / 'properties.cmake').write_text('set_target_properties(cli PROPERTIES CXX_STANDARD_REQUIRED ON)\n')
        expect_fail(run_checker(included_target_properties_required_same_value_source), 'target-level C++ standard override')

        included_target_extensions_same_value_source = write_source(root / 'included-target-extensions-same-value', BASE_CMAKELISTS + 'include(cmake/properties.cmake)\n')
        included_target_extensions_same_value_nested = included_target_extensions_same_value_source / 'cmake'
        included_target_extensions_same_value_nested.mkdir()
        (included_target_extensions_same_value_nested / 'properties.cmake').write_text('set_property(TARGET cli PROPERTY CXX_EXTENSIONS ON)\n')
        expect_fail(run_checker(included_target_extensions_same_value_source), 'target-level C++ standard override')

        included_source_property_source = write_source(root / 'included-source-property', BASE_CMAKELISTS + 'include(cmake/properties.cmake)\n')
        included_source_property_nested = included_source_property_source / 'cmake'
        included_source_property_nested.mkdir()
        (included_source_property_nested / 'properties.cmake').write_text('set_property(SOURCE probe.cpp PROPERTY COMPILE_FLAGS -std=gnu++17)\n')
        expect_fail(run_checker(included_source_property_source), 'manual C++ standard flag in CMake')

        directory_compile_property_source = write_source(root / 'directory-compile-property-generator')
        directory_compile_property_nested = directory_compile_property_source / 'cmake'
        directory_compile_property_nested.mkdir()
        (directory_compile_property_nested / 'properties.cmake').write_text('set_property(DIRECTORY PROPERTY COMPILE_OPTIONS "$<$<CONFIG:Debug>:-Wextra>")\n')
        expect_pass(run_checker(directory_compile_property_source))

        directory_compile_property_manual_source = write_source(root / 'directory-compile-property-manual-standard')
        directory_compile_property_manual_nested = directory_compile_property_manual_source / 'cmake'
        directory_compile_property_manual_nested.mkdir()
        (directory_compile_property_manual_nested / 'properties.cmake').write_text('set_property(DIRECTORY APPEND PROPERTY COMPILE_OPTIONS -Wall -std=gnu++17)\n')
        expect_fail(run_checker(directory_compile_property_manual_source), 'manual C++ standard flag in CMake')

        directory_properties_manual_source = write_source(root / 'directory-properties-manual-standard')
        directory_properties_manual_nested = directory_properties_manual_source / 'cmake'
        directory_properties_manual_nested.mkdir()
        (directory_properties_manual_nested / 'properties.cmake').write_text('set_directory_properties(PROPERTIES COMPILE_OPTIONS -std=c++17)\n')
        expect_fail(run_checker(directory_properties_manual_source), 'manual C++ standard flag in CMake')

        source_files_compile_options_manual_source = write_source(root / 'source-files-compile-options-manual-standard')
        source_files_compile_options_manual_nested = source_files_compile_options_manual_source / 'cmake'
        source_files_compile_options_manual_nested.mkdir()
        (source_files_compile_options_manual_nested / 'properties.cmake').write_text('set_source_files_properties(probe.cpp PROPERTIES COMPILE_OPTIONS -std=gnu++17)\n')
        expect_fail(run_checker(source_files_compile_options_manual_source), 'manual C++ standard flag in CMake')

        source_compile_property_generator_source = write_source(root / 'source-compile-property-generator')
        source_compile_property_generator_nested = source_compile_property_generator_source / 'cmake'
        source_compile_property_generator_nested.mkdir()
        (source_compile_property_generator_nested / 'properties.cmake').write_text('set_property(SOURCE probe.cpp PROPERTY COMPILE_OPTIONS "$<$<CONFIG:Debug>:-Wextra>")\n')
        expect_pass(run_checker(source_compile_property_generator_source))

        source_compile_property_manual_source = write_source(root / 'source-compile-property-manual-standard')
        source_compile_property_manual_nested = source_compile_property_manual_source / 'cmake'
        source_compile_property_manual_nested.mkdir()
        (source_compile_property_manual_nested / 'properties.cmake').write_text('set_property(SOURCE probe.cpp APPEND PROPERTY COMPILE_OPTIONS -Wextra -std=c++20)\n')
        expect_fail(run_checker(source_compile_property_manual_source), 'manual C++ standard flag in CMake')

        target_properties_compile_flag_source = write_source(root / 'target-properties-compile-flag')
        target_properties_compile_flag_nested = target_properties_compile_flag_source / 'cmake'
        target_properties_compile_flag_nested.mkdir()
        (target_properties_compile_flag_nested / 'properties.cmake').write_text('''
        set_target_properties(cli PROPERTIES
                              COMPILE_OPTIONS -std=gnu++17)
        ''')
        expect_fail(run_checker(target_properties_compile_flag_source), 'manual C++ standard flag in CMake')

        target_property_multi_compile_flag_source = write_source(root / 'target-property-multi-compile-flag')
        target_property_multi_compile_flag_nested = target_property_multi_compile_flag_source / 'cmake'
        target_property_multi_compile_flag_nested.mkdir()
        (target_property_multi_compile_flag_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS -Wall -std=gnu++17)\n')
        expect_fail(run_checker(target_property_multi_compile_flag_source), 'manual C++ standard flag in CMake')

        target_property_multi_compile_flag_pass_source = write_source(root / 'target-property-multi-compile-flag-pass')
        target_property_multi_compile_flag_pass_nested = target_property_multi_compile_flag_pass_source / 'cmake'
        target_property_multi_compile_flag_pass_nested.mkdir()
        (target_property_multi_compile_flag_pass_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND PROPERTY COMPILE_OPTIONS -Wall -Wextra)\n')
        expect_pass(run_checker(target_property_multi_compile_flag_pass_source))

        target_property_append_string_compile_flags_source = write_source(root / 'target-property-append-string-compile-flags')
        target_property_append_string_compile_flags_nested = target_property_append_string_compile_flags_source / 'cmake'
        target_property_append_string_compile_flags_nested.mkdir()
        (target_property_append_string_compile_flags_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND_STRING PROPERTY COMPILE_FLAGS " -std=gnu++17")\n')
        expect_fail(run_checker(target_property_append_string_compile_flags_source), 'manual C++ standard flag in CMake')

        target_property_append_string_compile_flags_pass_source = write_source(root / 'target-property-append-string-compile-flags-pass')
        target_property_append_string_compile_flags_pass_nested = target_property_append_string_compile_flags_pass_source / 'cmake'
        target_property_append_string_compile_flags_pass_nested.mkdir()
        (target_property_append_string_compile_flags_pass_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND_STRING PROPERTY COMPILE_FLAGS " -Wextra")\n')
        expect_pass(run_checker(target_property_append_string_compile_flags_pass_source))

        target_property_append_string_generator_standard_source = write_source(root / 'target-property-append-string-generator-standard-flag')
        target_property_append_string_generator_standard_nested = target_property_append_string_generator_standard_source / 'cmake'
        target_property_append_string_generator_standard_nested.mkdir()
        (target_property_append_string_generator_standard_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND_STRING PROPERTY COMPILE_FLAGS " $<$<CONFIG:Debug>:-std=gnu++17>")\n')
        expect_fail(run_checker(target_property_append_string_generator_standard_source), 'manual C++ standard flag in CMake')

        nested_generator_target_property_source = write_source(root / 'nested-generator-target-property-standard-flag')
        nested_generator_target_property_nested = nested_generator_target_property_source / 'cmake'
        nested_generator_target_property_nested.mkdir()
        (nested_generator_target_property_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND_STRING PROPERTY COMPILE_FLAGS " $<$<AND:$<CONFIG:Debug>,$<BOOL:1>>:-std=gnu++17>")\n')
        expect_fail(run_checker(nested_generator_target_property_source), 'manual C++ standard flag in CMake')

        target_property_append_string_bracket_standard_source = write_source(root / 'target-property-append-string-bracket-standard-flag')
        target_property_append_string_bracket_standard_nested = target_property_append_string_bracket_standard_source / 'cmake'
        target_property_append_string_bracket_standard_nested.mkdir()
        (target_property_append_string_bracket_standard_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND_STRING PROPERTY COMPILE_FLAGS [=[ -std=gnu++17 ]=])\n')
        expect_fail(run_checker(target_property_append_string_bracket_standard_source), 'manual C++ standard flag in CMake')

        target_property_append_string_generator_warning_source = write_source(root / 'target-property-append-string-generator-warning-pass')
        target_property_append_string_generator_warning_nested = target_property_append_string_generator_warning_source / 'cmake'
        target_property_append_string_generator_warning_nested.mkdir()
        (target_property_append_string_generator_warning_nested / 'properties.cmake').write_text('set_property(TARGET cli APPEND_STRING PROPERTY COMPILE_FLAGS " $<$<CONFIG:Debug>:-Wextra>")\n')
        expect_pass(run_checker(target_property_append_string_generator_warning_source))

        source_windows_path_property_source = write_source(root / 'source-windows-path-property-pass')
        source_windows_path_property_nested = source_windows_path_property_source / 'cmake'
        source_windows_path_property_nested.mkdir()
        (source_windows_path_property_nested / 'properties.cmake').write_text('set_property(SOURCE "C:/src/probe.cpp" PROPERTY COMPILE_OPTIONS -Wextra)\n')
        expect_pass(run_checker(source_windows_path_property_source))

        source_windows_path_property_manual_source = write_source(root / 'source-windows-path-property-manual-standard')
        source_windows_path_property_manual_nested = source_windows_path_property_manual_source / 'cmake'
        source_windows_path_property_manual_nested.mkdir()
        (source_windows_path_property_manual_nested / 'properties.cmake').write_text('set_property(SOURCE "C:/src/probe.cpp" PROPERTY COMPILE_OPTIONS -std=gnu++17)\n')
        expect_fail(run_checker(source_windows_path_property_manual_source), 'manual C++ standard flag in CMake')

        top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        # set(CMAKE_CXX_STANDARD 20)
        # set(CMAKE_CXX_STANDARD_REQUIRED ON)
        # set(CMAKE_CXX_EXTENSIONS ON)
        '''
        commented_source = write_source(root / 'commented-contract', top_text)
        expect_fail(run_checker(commented_source), 'missing top-level GNU++20 contract')

        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'toolchain.cmake').write_text('set(CMAKE_CXX_EXTENSIONS OFF)\n')
        expect_fail(run_checker(source), 'CMake GNU++20 contract drift')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'properties.cmake').write_text('''
        set_target_properties(cli PROPERTIES
                              OUTPUT_NAME x265
                              CXX_EXTENSIONS OFF)
        ''')
        expect_fail(run_checker(source), 'target-level C++ standard override')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'properties.cmake').write_text('''
        set_property(TARGET cli
                     PROPERTY CXX_STANDARD_REQUIRED OFF)
        ''')
        expect_fail(run_checker(source), 'target-level C++ standard override')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'features.cmake').write_text('target_compile_features(cli PRIVATE cxx_std_20)\n')
        expect_fail(run_checker(source), 'target-level C++ compile feature override')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'features.cmake').write_text('''
        target_compile_features(cli
                                PRIVATE cxx_std_17)
        ''')
        expect_fail(run_checker(source), 'target-level C++ compile feature override')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root, BASE_CMAKELISTS + 'add_subdirectory(extras)\n')
        nested = source / 'extras'
        nested.mkdir()
        (nested / 'CMakeLists.txt').write_text('set(CMAKE_CXX_EXTENSIONS OFF)\n')
        expect_fail(run_checker(source), 'CMake GNU++20 contract drift')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root, BASE_CMAKELISTS + 'add_subdirectory(extras)\n')
        nested = source / 'extras'
        nested.mkdir()
        (nested / 'CMakeLists.txt').write_text('include(local.cmake)\n')
        (nested / 'local.cmake').write_text('set(CMAKE_CXX_STANDARD 17)\n')
        expect_fail(run_checker(source), 'CMake GNU++20 contract drift')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        set(CMAKE_CXX_STANDARD 17 CACHE STRING "" FORCE)
        set(CMAKE_CXX_STANDARD_REQUIRED ON CACHE BOOL "" FORCE)
        set(CMAKE_CXX_EXTENSIONS ON CACHE BOOL "" FORCE)
        '''
        source = write_source(root, top_text)
        expect_fail(run_checker(source), 'top-level GNU++20 contract drift')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        set(CMAKE_CXX_STANDARD 20 CACHE STRING "" FORCE)
        set(CMAKE_CXX_STANDARD_REQUIRED OFF CACHE BOOL "" FORCE)
        set(CMAKE_CXX_EXTENSIONS ON CACHE BOOL "" FORCE)
        '''
        source = write_source(root, top_text)
        expect_fail(run_checker(source), 'top-level GNU++20 contract drift')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        top_text = BASE_CMAKELISTS + 'set(CMAKE_CXX_EXTENSIONS OFF)\n'
        source = write_source(root, top_text)
        expect_fail(run_checker(source), 'top-level GNU++20 contract drift')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        top_text = BASE_CMAKELISTS + 'set(CMAKE_CXX_STANDARD_REQUIRED OFF)\n'
        source = write_source(root, top_text)
        expect_fail(run_checker(source), 'top-level GNU++20 contract drift')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'flags.cmake').write_text('target_compile_options(cli PRIVATE -std=gnu++17)\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in CMake')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'flags.cmake').write_text('add_compile_options(-std=gnu++17)\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in CMake')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'flags.cmake').write_text('add_definitions(/std:c++17)\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in CMake')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'flags.cmake').write_text('set_property(TARGET cli PROPERTY COMPILE_OPTIONS -std=gnu++17)\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in CMake')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'flags.cmake').write_text('set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -std=c++20")\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in CMake')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'flags.cmake').write_text('set_source_files_properties(probe.cpp PROPERTIES COMPILE_FLAGS -std=gnu++17)\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in CMake')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        nested = source / 'cmake'
        nested.mkdir()
        (nested / 'flags.cmake').write_text('set_source_files_properties(probe.cpp PROPERTIES COMPILE_OPTIONS -std=gnu++17)\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in CMake')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        workflow = root / '.github' / 'workflows'
        workflow.mkdir(parents=True)
        (workflow / 'build.yml').write_text('run: cmake -S source # docs mention -DCMAKE_CXX_STANDARD_REQUIRED=OFF as forbidden\n')
        expect_pass(run_checker(source))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        workflow = root / '.github' / 'workflows'
        workflow.mkdir(parents=True)
        (workflow / 'build.yaml').write_text('run: cmake -S source # docs mention -DCMAKE_CXX_STANDARD_REQUIRED=OFF as forbidden\n')
        expect_pass(run_checker(source))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        action = root / '.github' / 'actions' / 'quoted-comment'
        action.mkdir(parents=True)
        (action / 'action.yml').write_text('''
        name: action
        runs:
          using: composite
          steps:
            - shell: bash
              run: printf '%s\\n' "# keep literal -std=gnu++17 visible"
        ''')
        expect_fail(run_checker(source), 'manual C++ standard flag in workflow/helper')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        workflow = root / '.github' / 'workflows'
        workflow.mkdir(parents=True)
        (workflow / 'build.yml').write_text('run: cmake -DCMAKE_CXX_STANDARD_REQUIRED=OFF source\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in workflow/helper')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        workflow = root / '.github' / 'workflows'
        workflow.mkdir(parents=True)
        (workflow / 'build.yaml').write_text('run: cmake -DCMAKE_CXX_STANDARD_REQUIRED=OFF source\n')
        expect_fail(run_checker(source), 'manual C++ standard flag in workflow/helper')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        action = root / '.github' / 'actions' / 'setup-windows-deps'
        action.mkdir(parents=True)
        (action / 'action.yml').write_text('''
        name: action
        runs:
          using: composite
          steps:
            - shell: bash
              run: c++ --std=c++20 -c probe.cpp
        ''')
        expect_fail(run_checker(source), 'manual C++ standard flag in workflow/helper')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = write_source(root)
        action = root / '.github' / 'actions' / 'setup-windows-deps'
        action.mkdir(parents=True)
        (action / 'action.yml').write_text('''
        name: action
        runs:
          using: composite
          steps:
            - shell: bash
              run: c++ --std=gnu++20 -c probe.cpp
        ''')
        expect_pass(run_checker(source))

    print('CMake GNU++20 contract guardrails validated')


if __name__ == '__main__':
    main()
