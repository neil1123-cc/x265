# Version for Yuuki Asuna mod

find_package(Git)

set(MOD_BUILD "@ADE")

# Get current HEAD tag
execute_process(
    COMMAND ${GIT_EXECUTABLE} describe --tags --match=[0-9].[0-9]* HEAD
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE X265_HEAD_TAG
    ERROR_QUIET OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE X265_HEAD_TAG_RESULT
)

# Get short commit hash
execute_process(
    COMMAND ${GIT_EXECUTABLE} rev-parse --short HEAD
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE X265_HEAD_HASH
    ERROR_QUIET OUTPUT_STRIP_TRAILING_WHITESPACE
)

# Fallback version if git describe fails (e.g., shallow clone, no tags)
if(NOT X265_HEAD_TAG OR X265_HEAD_TAG_RESULT)
    set(X265_VERSION "4.1+unknown-g${X265_HEAD_HASH}")
    set(X265_LATEST_TAG "4.1")
    set(X265_TAG_DISTANCE 0)
    message(STATUS "x265 Mod: ${MOD_BUILD}")
    message(STATUS "x265 Release Version: ${X265_VERSION}")
    return()
endif()

# Parse HEAD tag: format is "TAG-DISTANCE-COMMIT"
string(REPLACE "-" ";" X265_HEAD_TAG_ARR ${X265_HEAD_TAG})
list(LENGTH X265_HEAD_TAG_ARR X265_HEAD_TAG_LEN)

# Validate we have enough parts
if(X265_HEAD_TAG_LEN LESS 3)
    # HEAD is exactly on a tag, use tag as version directly
    string(REPLACE "M" "" X265_LATEST_TAG ${X265_HEAD_TAG})
    set(X265_VERSION "${X265_LATEST_TAG}")
    set(X265_TAG_DISTANCE 0)
    message(STATUS "x265 Mod: ${MOD_BUILD}")
    message(STATUS "x265 Release Version: ${X265_VERSION}")
    return()
endif()

list(GET X265_HEAD_TAG_ARR 0 X265_ORIG_TAG)
list(GET X265_HEAD_TAG_ARR 1 X265_HEAD_DISTANCE)
list(GET X265_HEAD_TAG_ARR 2 X265_HEAD_COMMIT)

# Remove 'M' prefix if present (dirty working tree)
string(REPLACE "M" "" X265_LATEST_TAG ${X265_ORIG_TAG})

# Build version string
set(X265_VERSION "${X265_LATEST_TAG}+${X265_HEAD_DISTANCE}-g${X265_HEAD_HASH}")
set(X265_TAG_DISTANCE ${X265_HEAD_DISTANCE})

message(STATUS "x265 Mod: ${MOD_BUILD}")
message(STATUS "x265 Release Version: ${X265_VERSION}")
