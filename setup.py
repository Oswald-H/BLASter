from pathlib import Path
from sys import platform
from setuptools import Extension, setup, find_packages
from Cython.Build import cythonize
import numpy as np
import sys

def find_eigen():
    for f in [Path('eigen3'),
              Path('/usr/include/eigen3'),
              Path.home().joinpath('.local/include/eigen3')]:
        if f.exists() and f.is_dir():
            return str(f)
    print("ERROR: Eigen3 library is required!")
    print("NOTE : Please run 'make eigen3'")
    exit(1)


openmp_arg = '/openmp' if sys.platform.startswith("win") else '-fopenmp'

compile_args = [
    '--std=c++17',
    '-DNPY_NO_DEPRECATED_API=NPY_1_9_API_VERSION',
    openmp_arg,
]

link_args = [openmp_arg]

debug_args = [
    '-O1',
    '-fsanitize=address,undefined',
    '-g',
    '-fno-omit-frame-pointer',
]

release_args = [
    '-O3',
    '-march=native',
    '-DEIGEN_NO_DEBUG',
]

if '--cython-gdb' in sys.argv:
    compile_args += debug_args
    link_args += debug_args
else:
    compile_args += release_args

extensions = [
    Extension(
        name="blaster_core",
        sources=["core/blaster.pyx"],
        include_dirs=[np.get_include(), find_eigen()],
        extra_compile_args=compile_args,
        extra_link_args=link_args,
        language="c++",
    )
]

setup(
    name="blaster",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
        build_dir='build/cpp',
    ),
)
