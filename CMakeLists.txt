cmake_minimum_required(VERSION 3.18)
project(ornaments LANGUAGES C CXX)
include(GNUInstallDirs)
include(ExternalProject)

option(ORNAMENTS_INSTALL_PYTHON "Install the Python CLI alongside the native engine" OFF)
if(ORNAMENTS_INSTALL_PYTHON)
    find_package(Python 3.10 REQUIRED COMPONENTS Interpreter)
    # Query a relative path so the package remains relocatable after installation.
    execute_process(
        COMMAND "${Python_EXECUTABLE}" -c
            "import sysconfig; print(sysconfig.get_path('purelib', vars={'base': '', 'platbase': ''}).lstrip('/'))"
        OUTPUT_VARIABLE ORNAMENTS_SITE_PACKAGES
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE ORNAMENTS_PYTHON_PATH_RESULT
    )
    if(NOT ORNAMENTS_PYTHON_PATH_RESULT EQUAL 0)
        message(FATAL_ERROR "Could not determine the Python installation directory")
    endif()
    set(ORNAMENTS_INSTALL_DIR "${ORNAMENTS_SITE_PACKAGES}/ornaments/_bin" CACHE STRING
        "Native engine installation directory" FORCE)
    configure_file(cmake/install-python.cmake.in install-python.cmake @ONLY)
    install(SCRIPT "${CMAKE_CURRENT_BINARY_DIR}/install-python.cmake")
endif()

option(USE_HDF5 "Compile with HDF5 support" OFF)
set(ORNAMENTS_INSTALL_DIR "${CMAKE_INSTALL_BINDIR}" CACHE STRING "Native engine installation directory")
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

find_package(Threads REQUIRED)
find_package(ZLIB REQUIRED)
find_package(BZip2 REQUIRED)
find_package(LibLZMA REQUIRED)
find_program(AUTOHEADER_EXECUTABLE autoheader REQUIRED)
find_program(AUTOCONF_EXECUTABLE autoconf REQUIRED)
find_program(HTSLIB_MAKE_EXECUTABLE NAMES gmake make REQUIRED)

# Configure/build the committed HTSlib API in a private writable copy.
# No remote dependency sources, and no generated files in the source tree.
set(HTSLIB_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/htslib-source")
file(MAKE_DIRECTORY "${HTSLIB_SOURCE}")
file(COPY "${PROJECT_SOURCE_DIR}/ext/htslib/" DESTINATION "${HTSLIB_SOURCE}"
     PATTERN "src" EXCLUDE PATTERN "tmp" EXCLUDE PATTERN "*.o" EXCLUDE PATTERN "*.a" EXCLUDE)
get_filename_component(ZLIB_LIBRARY_DIR "${ZLIB_LIBRARY_RELEASE}" DIRECTORY)
ExternalProject_Add(htslib
    PREFIX "${CMAKE_CURRENT_BINARY_DIR}/htslib-build"
    SOURCE_DIR "${HTSLIB_SOURCE}"
    DOWNLOAD_COMMAND ""
    UPDATE_COMMAND ""
    BUILD_IN_SOURCE TRUE
    CONFIGURE_COMMAND ${AUTOHEADER_EXECUTABLE}
        COMMAND ${AUTOCONF_EXECUTABLE}
        COMMAND ${CMAKE_COMMAND} -E env "CC=${CMAKE_C_COMPILER}"
            "CPPFLAGS=-I${ZLIB_INCLUDE_DIRS}" "LDFLAGS=-L${ZLIB_LIBRARY_DIR}"
            "${HTSLIB_SOURCE}/configure" --disable-bz2 --disable-lzma --disable-libcurl
    BUILD_COMMAND ${HTSLIB_MAKE_EXECUTABLE} lib-static
    BUILD_BYPRODUCTS "${HTSLIB_SOURCE}/libhts.a"
    INSTALL_COMMAND ""
)
add_subdirectory(src)
