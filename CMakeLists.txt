cmake_minimum_required(VERSION 3.30...4.4)

project(blaster LANGUAGES CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(BLASTER_NATIVE AUTO CACHE STRING "Native CPU tuning: AUTO (editable installs only), ON, or OFF")
set_property(CACHE BLASTER_NATIVE PROPERTY STRINGS AUTO ON OFF)
if(BLASTER_NATIVE STREQUAL "AUTO")
  set(BLASTER_NATIVE OFF)
  if(SKBUILD_STATE STREQUAL "editable" AND NOT CMAKE_CROSSCOMPILING
      AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    set(BLASTER_NATIVE ON)
  endif()
endif()
option(BLASTER_LTO "Enable link-time optimization in optimized builds" ON)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)
find_package(Eigen3 CONFIG REQUIRED)
find_package(OpenMP REQUIRED COMPONENTS CXX)

# bindings.cpp also contains the OpenMP block-reduction loops.
nanobind_add_module(_core NOMINSIZE
  core/bindings.cpp
  core/eigen_matmul.cpp
  core/lattice_reduction.cpp
)

target_compile_features(_core PRIVATE cxx_std_23)
set_target_properties(_core PROPERTIES CXX_EXTENSIONS OFF)

if(SKBUILD_STATE STREQUAL "editable")
  add_custom_target(_core_editable ALL
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
      "$<TARGET_FILE:_core>" "${CMAKE_CURRENT_SOURCE_DIR}/src/blaster/$<TARGET_FILE_NAME:_core>"
    DEPENDS _core
    VERBATIM
  )
endif()

if(BLASTER_NATIVE)
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64|ARM64)$")
    set(BLASTER_NATIVE_FLAG -mcpu=native)
  else()
    set(BLASTER_NATIVE_FLAG -march=native)
  endif()
  include(CheckCXXCompilerFlag)
  check_cxx_compiler_flag("${BLASTER_NATIVE_FLAG}" BLASTER_HAS_NATIVE_FLAG)
  if(NOT BLASTER_HAS_NATIVE_FLAG)
    message(FATAL_ERROR "BLASTER_NATIVE requires compiler support for ${BLASTER_NATIVE_FLAG}")
  endif()
  target_compile_options(_core PRIVATE ${BLASTER_NATIVE_FLAG})
endif()

if(BLASTER_LTO)
  include(CheckIPOSupported)
  check_ipo_supported(RESULT BLASTER_HAS_IPO OUTPUT BLASTER_IPO_ERROR LANGUAGES CXX)
  if(BLASTER_HAS_IPO)
    set_target_properties(_core PROPERTIES
      INTERPROCEDURAL_OPTIMIZATION_RELEASE ON
      INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO ON
      INTERPROCEDURAL_OPTIMIZATION_MINSIZEREL ON
    )
  else()
    message(WARNING "Link-time optimization is unavailable: ${BLASTER_IPO_ERROR}")
  endif()
endif()

target_link_libraries(_core PRIVATE Eigen3::Eigen OpenMP::OpenMP_CXX)

install(TARGETS _core
  LIBRARY DESTINATION blaster
  RUNTIME DESTINATION blaster
  ARCHIVE DESTINATION blaster
)
