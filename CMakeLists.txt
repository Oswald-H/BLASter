cmake_minimum_required(VERSION 3.15...3.26)

project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(CheckCXXCompilerFlag)
include(CheckIPOSupported)

if(APPLE AND NOT OpenMP_ROOT)
  find_program(BREW_EXECUTABLE brew)
  if(BREW_EXECUTABLE)
    execute_process(
      COMMAND "${BREW_EXECUTABLE}" --prefix libomp
      OUTPUT_VARIABLE _HOMEBREW_LIBOMP_PREFIX
      OUTPUT_STRIP_TRAILING_WHITESPACE
      ERROR_QUIET
    )
    if(_HOMEBREW_LIBOMP_PREFIX)
      set(OpenMP_ROOT "${_HOMEBREW_LIBOMP_PREFIX}")
    endif()
  endif()
endif()

find_package(Python 3.10 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)

find_package(OpenMP REQUIRED COMPONENTS CXX)
find_package(Eigen3 REQUIRED NO_MODULE)


nanobind_add_module(_core
  core/bindings.cpp
  core/eigen_matmul.cpp
  core/lattice_reduction.cpp
)

target_link_libraries(_core PRIVATE Eigen3::Eigen OpenMP::OpenMP_CXX)

target_compile_definitions(_core PRIVATE EIGEN_NO_DEBUG)

set_target_properties(_core PROPERTIES
  CXX_STANDARD 17
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN TRUE
)

check_ipo_supported(RESULT BLASTER_IPO_SUPPORTED OUTPUT BLASTER_IPO_OUTPUT LANGUAGES CXX)
if(BLASTER_IPO_SUPPORTED)
  set_target_properties(_core PROPERTIES INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
else()
  message(STATUS "IPO/LTO not enabled: ${BLASTER_IPO_OUTPUT}")
endif()

target_compile_options(_core PRIVATE
  $<$<AND:$<NOT:$<CXX_COMPILER_ID:MSVC>>,$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>,$<CONFIG:MinSizeRel>>>:-O3>
  $<$<AND:$<NOT:$<CXX_COMPILER_ID:MSVC>>,$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>,$<CONFIG:MinSizeRel>>>:-march=native>
)

install(TARGETS _core LIBRARY DESTINATION blaster)
