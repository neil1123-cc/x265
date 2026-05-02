# - Try to find L-SMASH
# Once done this will define
#  LSMASH_FOUND - System has L-SMASH
#  LSMASH_INCLUDE_DIRS - The L-SMASH include directories
#  LSMASH_LIBRARIES - The libraries needed to use L-SMASH
#  LSMASH_LIBRARY_DIRS - The directory to find L-SMASH libraries

include(FindPackageHandleStandardArgs)
find_package(PkgConfig)

if(PKG_CONFIG_FOUND)
    pkg_check_modules(PC_LSMASH lsmash)
endif()

find_path(LSMASH_INCLUDE_DIR
    NAMES lsmash.h
    HINTS ${PC_LSMASH_INCLUDEDIR} ${PC_LSMASH_INCLUDE_DIRS})

find_library(LSMASH_LIBRARY
    NAMES lsmash
    HINTS ${PC_LSMASH_LIBDIR} ${PC_LSMASH_LIBRARY_DIRS})

set(LSMASH_INCLUDE_DIRS ${LSMASH_INCLUDE_DIR})
set(LSMASH_LIBRARIES ${LSMASH_LIBRARY})
get_filename_component(LSMASH_LIBRARY_DIRS "${LSMASH_LIBRARY}" DIRECTORY)

find_package_handle_standard_args(LSMASH DEFAULT_MSG
    LSMASH_LIBRARY LSMASH_INCLUDE_DIR)

mark_as_advanced(LSMASH_INCLUDE_DIR LSMASH_LIBRARY)
