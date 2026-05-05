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

        inline_cache_top_text = '''
        cmake_minimum_required(VERSION 3.20)
        project(x265)
        set(CMAKE_CXX_STANDARD 20 CACHE STRING "project standard" FORCE) # keep cache callers aligned
        set(CMAKE_CXX_STANDARD_REQUIRED ON CACHE BOOL "" FORCE)
        set(CMAKE_CXX_EXTENSIONS ON CACHE BOOL "" FORCE)
        '''
        inline_cache_source = write_source(root / 'inline-cache-contract', inline_cache_top_text)
        expect_pass(run_checker(inline_cache_source))

        readonly_source = write_source(root / 'readonly-property')
        readonly_nested = readonly_source / 'cmake'
        readonly_nested.mkdir()
        (readonly_nested / 'query.cmake').write_text('get_property(current TARGET cli PROPERTY CXX_STANDARD)\n')
        expect_pass(run_checker(readonly_source))

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

        legal_feature_source = write_source(root / 'legal-target-features')
        legal_feature_nested = legal_feature_source / 'cmake'
        legal_feature_nested.mkdir()
        (legal_feature_nested / 'features.cmake').write_text('''
        set(cxx_std_feature cxx_constexpr)
        target_compile_features(cli PRIVATE cxx_constexpr cxx_lambdas ${cxx_std_feature})
        ''')
        expect_pass(run_checker(legal_feature_source))

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
