# vim: syntax=cmake

check_symbol_exists(__rdtsc "intrin.h" HAVE_RDTSC)
# add X86 assembly files
if(X86)
enable_language(ASM_NASM)

if(MSVC_IDE)
    set(NASM_SRC checkasm-a.obj)
    add_custom_command(
        OUTPUT checkasm-a.obj
        COMMAND ${NASM_EXECUTABLE}
        ARGS ${NASM_FLAGS} ${CMAKE_CURRENT_SOURCE_DIR}/checkasm-a.asm -o checkasm-a.obj
        DEPENDS checkasm-a.asm)
else()
    set(NASM_SRC checkasm-a.asm)
endif()
endif(X86)

# add ARM assembly files
if(ARM OR CROSS_COMPILE_ARM)
    enable_language(ASM)
    set(NASM_SRC checkasm-arm.S)
    add_custom_command(
        OUTPUT checkasm-arm.obj
        COMMAND ${CMAKE_CXX_COMPILER}
        ARGS ${NASM_FLAGS} ${CMAKE_CURRENT_SOURCE_DIR}/checkasm-arm.S -o checkasm-arm.obj
        DEPENDS checkasm-arm.S)
endif(ARM OR CROSS_COMPILE_ARM)

# add PowerPC assembly files
if(POWER)
    set(NASM_SRC)
endif(POWER)

add_executable(TestBench ${NASM_SRC}
    testbench.cpp testharness.h
    pixelharness.cpp pixelharness.h
    mbdstharness.cpp mbdstharness.h
    ipfilterharness.cpp ipfilterharness.h
    intrapredharness.cpp intrapredharness.h)

target_link_libraries(TestBench x265-static ${PLATFORM_LIBS})
if(X265_CXX20_WARNING_OPTIONS)
    target_compile_options(TestBench PRIVATE ${X265_CXX20_WARNING_TARGET_OPTIONS})
endif()
if(HAVE_RDTSC)
    target_compile_definitions(TestBench PRIVATE HAVE_RDTSC=1)
endif()
if(LINKER_OPTIONS)
    if(EXTRA_LIB)
        list(APPEND LINKER_OPTIONS "-L..")
    endif(EXTRA_LIB)
    string(REPLACE ";" " " LINKER_OPTION_STR "${LINKER_OPTIONS}")
    set_target_properties(TestBench PROPERTIES LINK_FLAGS "${LINKER_OPTION_STR}")
endif()
