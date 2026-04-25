# vim: syntax=cmake
# Modern CMake: dynamicHDR10 library
cmake_minimum_required(VERSION 3.16)

if(ENABLE_HDR10_PLUS)

add_library(dynamicHDR10 OBJECT
    BasicStructures.h
    json11/json11.cpp json11/json11.h
    JsonHelper.cpp JsonHelper.h
    metadataFromJson.cpp metadataFromJson.h
    SeiMetadataDictionary.cpp SeiMetadataDictionary.h
    hdr10plus.h
    api.cpp )

# C++17 is already set in parent CMakeLists.txt via CMAKE_CXX_STANDARD
# This OBJECT library inherits the standard from parent scope

# Collect compile definitions and options for this target
set(DHDR10_COMPILE_DEFINITIONS "")
set(DHDR10_COMPILE_OPTIONS "")

if(GCC)
    list(APPEND DHDR10_COMPILE_OPTIONS -Wall -Wextra -Wshadow)
    list(APPEND DHDR10_COMPILE_DEFINITIONS __STDC_LIMIT_MACROS=1)

    if(ENABLE_PIC)
        list(APPEND DHDR10_COMPILE_OPTIONS -fPIC)
    endif()

    if(NATIVE_BUILD)
        if(INTEL_CXX)
            list(APPEND DHDR10_COMPILE_OPTIONS -xhost)
        else()
            list(APPEND DHDR10_COMPILE_OPTIONS -march=native)
        endif()
    elseif(X86 AND NOT X64)
        string(FIND "${CMAKE_CXX_FLAGS}" "-march" marchPos)
        if(marchPos LESS "0")
            list(APPEND DHDR10_COMPILE_OPTIONS -march=i686)
            if(WIN32 AND NOT INTEL_CXX AND NOT CLANG AND
               CMAKE_CXX_COMPILER_VERSION VERSION_GREATER 6.0 AND CMAKE_CXX_COMPILER_VERSION VERSION_LESS 7.0)
                list(APPEND DHDR10_COMPILE_OPTIONS -mpreferred-stack-boundary=2)
            endif()
        endif()
    endif()

    if(ARM AND CROSS_COMPILE_ARM)
        set(ARM_ARGS -march=armv6 -mfloat-abi=soft -mfpu=vfp -marm -fPIC)
    elseif(ARM)
        find_package(Neon)
        if(CPU_HAS_NEON)
            set(ARM_ARGS -mcpu=native -mfloat-abi=hard -mfpu=neon -marm -fPIC)
            list(APPEND DHDR10_COMPILE_DEFINITIONS HAVE_NEON)
        else()
            set(ARM_ARGS -mcpu=native -mfloat-abi=hard -mfpu=vfp -marm)
        endif()
    endif()

    if(ARM_ARGS)
        list(APPEND DHDR10_COMPILE_OPTIONS ${ARM_ARGS})
    endif()

    # Profile generation
    if(FPROFILE_GENERATE)
        if(INTEL_CXX)
            list(APPEND DHDR10_COMPILE_OPTIONS -prof-gen "-prof-dir=${CMAKE_CURRENT_BINARY_DIR}")
        else()
            include(CheckCXXCompilerFlag)
            check_cxx_compiler_flag(-fprofile-generate CC_HAS_PROFILE_GENERATE)
            if(CC_HAS_PROFILE_GENERATE)
                list(APPEND DHDR10_COMPILE_OPTIONS -fprofile-generate)
            endif()
        endif()
    endif()

    # Profile usage
    if(FPROFILE_USE)
        if(INTEL_CXX)
            list(APPEND DHDR10_COMPILE_OPTIONS -prof-use "-prof-dir=${CMAKE_CURRENT_BINARY_DIR}")
        else()
            include(CheckCXXCompilerFlag)
            check_cxx_compiler_flag(-fprofile-use CC_HAS_PROFILE_USE)
            check_cxx_compiler_flag(-fprofile-correction CC_HAS_PROFILE_CORRECTION)
            check_cxx_compiler_flag(-Wno-error=coverage-mismatch CC_HAS_COVMISMATCH)
            if(CC_HAS_PROFILE_USE)
                list(APPEND DHDR10_COMPILE_OPTIONS -fprofile-use)
            endif()
            if(CC_HAS_PROFILE_CORRECTION)
                list(APPEND DHDR10_COMPILE_OPTIONS -fprofile-correction)
            endif()
            if(CC_HAS_COVMISMATCH)
                list(APPEND DHDR10_COMPILE_OPTIONS -Wno-error=coverage-mismatch)
            endif()
        endif()
    endif()

    if(STATIC_LINK_CRT)
        list(APPEND DHDR10_COMPILE_OPTIONS -static)
    endif()

    # Optional compiler flags
    include(CheckCXXCompilerFlag)
    check_cxx_compiler_flag(-Wno-array-bounds CC_HAS_NO_ARRAY_BOUNDS)
    if(CC_HAS_NO_ARRAY_BOUNDS)
        list(APPEND DHDR10_COMPILE_OPTIONS -Wno-array-bounds)
    endif()

    check_cxx_compiler_flag(-ffast-math CC_HAS_FAST_MATH)
    if(CC_HAS_FAST_MATH)
        list(APPEND DHDR10_COMPILE_OPTIONS -ffast-math)
    endif()

    check_cxx_compiler_flag(-mstackrealign CC_HAS_STACK_REALIGN)
    if(CC_HAS_STACK_REALIGN)
        list(APPEND DHDR10_COMPILE_OPTIONS -mstackrealign)
    endif()

    # Disable exceptions
    check_cxx_compiler_flag(-fno-exceptions CC_HAS_FNO_EXCEPTIONS_FLAG)
    if(CC_HAS_FNO_EXCEPTIONS_FLAG)
        list(APPEND DHDR10_COMPILE_OPTIONS -fno-exceptions)
    endif()

    # Sanitizer options
    set(FSANITIZE "" CACHE STRING "-fsanitize options for GCC/clang")
    if(FSANITIZE)
        list(APPEND DHDR10_COMPILE_OPTIONS "-fsanitize=${FSANITIZE}")
    endif()

    # Aggressive checks
    option(ENABLE_AGGRESSIVE_CHECKS "Enable stack protection and -ftrapv" OFF)
    if(ENABLE_AGGRESSIVE_CHECKS)
        list(APPEND DHDR10_COMPILE_DEFINITIONS USING_FTRAPV=1)
        check_cxx_compiler_flag(-fsanitize=undefined-trap CC_HAS_CATCH_UNDEFINED)
        check_cxx_compiler_flag(-ftrapv CC_HAS_FTRAPV)
        check_cxx_compiler_flag(-fstack-protector-all CC_HAS_STACK_PROTECT)
        if(CC_HAS_FTRAPV)
            list(APPEND DHDR10_COMPILE_OPTIONS -ftrapv)
        endif()
        if(CC_HAS_CATCH_UNDEFINED)
            list(APPEND DHDR10_COMPILE_OPTIONS -fsanitize=undefined-trap -fsanitize-undefined-trap-on-error)
        endif()
        if(CC_HAS_STACK_PROTECT)
            list(APPEND DHDR10_COMPILE_OPTIONS -fstack-protector-all)
        endif()
    endif()
endif(GCC)

# Apply compile definitions and options (Modern CMake)
target_compile_definitions(dynamicHDR10 PRIVATE ${DHDR10_COMPILE_DEFINITIONS})
if(DHDR10_COMPILE_OPTIONS)
    target_compile_options(dynamicHDR10 PRIVATE ${DHDR10_COMPILE_OPTIONS})
endif()

# Install header
install(FILES hdr10plus.h DESTINATION include)

endif(ENABLE_HDR10_PLUS)
