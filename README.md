# BLASter

BLASter is a proof-of-concept implementation of an LLL-like lattice reduction algorithm using parallelization, segmentation, Seysen's reduction, and Eigen for linear algebra.

This repository is a fork of BLASter for further development and experimentation. It may differ from the upstream project in behavior,
performance, and supported workflows.

## Disclaimer

The goal of this software is to showcase speedups that are possible in lattice reduction software.
This software is a *proof of concept*!

In particular, we **do not**:

- guarantee that the algorithm terminates or that its output is correct on all lattices,
- support lattices with large entries,
- consider issues or PRs that improve efficiency or robustness,
- actively maintain this software.

We **do**:

- happily answer questions about design choices phrased as: *"Why is X done in Y way?"* In many cases, the answer may be: "because it is faster in practice."
- encourage the cryptographic community to build a new robust lattice reduction library incorporating the ideas in this proof of concept.

## Requirements

- `uv` and Python >= 3.13
- CMake and C++ compiler
- OpenMP and Eigen3/Eigen5 support

## Installation

Install the project in the local `uv` environment:

```bash
uv sync
```

Install development dependencies when needed:

```bash
uv sync --group dev
```

Note: If CMake cannot find Eigen3/Eigen5 or OpenMP, specify their paths through uv:

```bash
CMAKE_ARGS="-DOpenMP_ROOT=<openmp-path> -DCMAKE_PREFIX_PATH=<eigen-path>" uv sync --reinstall-package blaster
```

## Running

Show the available command-line options:

```bash
blaster -h
```

Reduce a lattice from an input file:

```bash
blaster -i INPUTFILE -p -q -v
```

Run LLL, DeepLLL, or BKZ with the corresponding options:

```bash
blaster -pqv
blaster -d4 -pqv
blaster -b60 -t1 -P2 -pqv
```

Here:

- `-i INPUTFILE` reads the lattice from `INPUTFILE`.
- `-p` prints the output basis profile.
- `-q` suppresses the reduced basis on standard output.
- `-v` enables verbose output.
- `-d4` enables DeepLLL with depth 4.
- `-b60` runs BKZ with block size 60.
- `-t1` runs one BKZ tour, and `-P2` sets the progressive block-size increment to 2.

Use BLASter from Python:

```python
from blaster import reduce
```

The input format is compatible with NTL, FPLLL, and Flatter:

```text
[[a_11 a_12 ... a_1n]
 [a_21 a_22 ... a_2n]
 ...
 [a_k1 a_k2 ... a_kn]]
```

## Citation

This fork is based on the BLASter implementation described in the following publication:

> Léo Ducas, Ludo N. Pulles, Marc Stevens. *Towards a Modern LLL Implementation*.
> In: ASIACRYPT 2025, Part III. LNCS, vol 16247. Springer, December 2025.
> DOI: [10.1007/978-981-95-5099-9_3](https://doi.org/10.1007/978-981-95-5099-9_3)
