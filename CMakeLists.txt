cmake_minimum_required(VERSION 3.30...4.4)

project(blaster LANGUAGES CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)
find_package(Eigen3 CONFIG REQUIRED)
find_package(OpenMP REQUIRED COMPONENTS CXX)

nanobind_add_module(_core
  core/bindings.cpp
  core/eigen_matmul.cpp
  core/lattice_reduction.cpp
)

target_compile_features(_core PRIVATE cxx_std_23)
set_target_properties(_core PROPERTIES CXX_EXTENSIONS OFF)

target_link_libraries(_core PRIVATE Eigen3::Eigen OpenMP::OpenMP_CXX)

install(TARGETS _core
  LIBRARY DESTINATION blaster
  RUNTIME DESTINATION blaster
  ARCHIVE DESTINATION blaster
)
