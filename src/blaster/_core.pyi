"""Type stubs for the _core nanobind extension (C++/Eigen/OMP)."""

from numpy import float64, int64
from numpy.typing import NDArray

# Module-level functions (no return value, called for side-effects only)

def set_debug_flag(flag: int) -> None: ...
def set_num_cores(num_cores: int) -> None: ...

# Lattice reduction — all three modify R, B_red, U in-place (void in C++)

def block_lll(
    R: NDArray[float64],
    B_red: NDArray[int64],
    U: NDArray[int64],
    delta: float,
    offset: int,
    block_size: int,
) -> None: ...
def block_deep_lll(
    depth: int,
    R: NDArray[float64],
    B_red: NDArray[int64],
    U: NDArray[int64],
    delta: float,
    offset: int,
    block_size: int,
) -> None: ...
def block_bkz(
    beta: int,
    R: NDArray[float64],
    B_red: NDArray[int64],
    U: NDArray[int64],
    delta: float,
    offset: int,
    block_size: int,
) -> None: ...

# BLAS wrappers

def FT_matmul(
    A: NDArray[float64],
    B: NDArray[float64],
) -> NDArray[float64]: ...
def ZZ_matmul(
    A: NDArray[int64],
    B: NDArray[int64],
) -> NDArray[int64]: ...
def ZZ_left_matmul_strided(
    A: NDArray[int64],
    B: NDArray[int64],
) -> None: ...
def ZZ_right_matmul(
    A: NDArray[int64],
    B: NDArray[int64],
) -> None: ...
def ZZ_right_matmul_strided(
    A: NDArray[int64],
    B: NDArray[int64],
) -> None: ...
