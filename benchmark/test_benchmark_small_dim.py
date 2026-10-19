import os
from time import perf_counter

import pytest
from _benchmark_utils import (
    BENCHMARK_DIR,
    OUTPUT_DIR,
    SMALL_DIM_HEADER,
    ensure_directory,
    ensure_lattice,
    run_timed,
)

from blaster import reduce
from blaster.lattice_io import read_qary_lattice
from blaster.stats import get_profile, rhf, slope


def is_prime(x):
    if x <= 2:
        return x == 2
    for y in range(2, x):
        if y * y > x:
            return True
        if x % y == 0:
            return False
    return True


def next_prime(x):
    while not is_prime(x):
        x += 1
    return x


# Specify which lattices we want to test:
MQS = [(m, next_prime(2 ** (m // 8))) for m in range(48, 256, 16)]
SEEDS = range(10)
NUM_THREADS = 1
DEEPLLL_DEPTH = 4

LATTICES = [(m, q, seed) for m, q in MQS for seed in SEEDS]
LATTICE_IDS = [f"m{m}-q{q}-seed{seed}" for m, q, seed in LATTICES]
OUTPUT_FILE = BENCHMARK_DIR / "small-dimension.csv"
OUTPUT_LATTICE = OUTPUT_DIR / "temp_small_dim.lat"


@pytest.fixture(scope="session")
def output_file():
    OUTPUT_FILE.write_text(f"{SMALL_DIM_HEADER}\n", encoding="utf8")
    ensure_directory(OUTPUT_DIR)
    return OUTPUT_FILE


def output_data(data, output_file):
    line = ",".join(str(value) for value in data)
    print(line)
    with output_file.open("a", encoding="utf8") as output:
        print(line, file=output)


def run_command(command, instance, output_file, env=None):
    result, metrics = run_timed(command, env=env)
    if result.returncode != 0:
        print("ERROR WHILE EXECUTING COMMAND!")
        print(result.stderr)
        raise RuntimeError(result.stderr)

    profile = get_profile(read_qary_lattice(OUTPUT_LATTICE))
    data = instance | {"slope": f"{slope(profile):.6f}", "rhf": f"{rhf(profile):.5f}"}
    output_data(
        list(data.values()) + [f"{metrics['real']:.2f}", f"{metrics['user']:.2f}", f"{metrics['sys']:.2f}"],
        output_file,
    )


def exec_blaster(inputfile, depth, instance, output_file):
    start = perf_counter()
    basis = read_qary_lattice(inputfile)
    _, basis_reduced, _ = reduce(basis, depth=depth)
    real = perf_counter() - start

    profile = get_profile(basis_reduced)
    data = instance | {"slope": f"{slope(profile):.6f}", "rhf": f"{rhf(profile):.5f}"}
    output_data(list(data.values()) + [f"{real:.2f}", "0", "0"], output_file)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_lll(m, q, seed, output_file):
    path = ensure_lattice(m, q, seed)
    exec_blaster(path, 0, {"m": m, "q": q, "seed": seed, "type": "LLL"}, output_file)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_deeplll(m, q, seed, output_file):
    path = ensure_lattice(m, q, seed)
    instance = {"m": m, "q": q, "seed": seed, "type": f"DeepLLL{DEEPLLL_DEPTH}"}
    exec_blaster(path, DEEPLLL_DEPTH, instance, output_file)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_flatter(m, q, seed, output_file):
    path = ensure_lattice(m, q, seed)
    env = os.environ | {"OMP_NUM_THREADS": str(NUM_THREADS)}
    run_command(
        ["flatter", str(path), str(OUTPUT_LATTICE)],
        {
            "m": m,
            "q": q,
            "seed": seed,
            "type": f"Flatter ({NUM_THREADS} threads)",
        },
        output_file,
        env=env,
    )


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_fplll(m, q, seed, output_file):
    path = ensure_lattice(m, q, seed)
    result, metrics = run_timed(["fplll", str(path)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    OUTPUT_LATTICE.write_text(result.stdout, encoding="utf8")
    profile = get_profile(read_qary_lattice(OUTPUT_LATTICE))
    data = {
        "m": m,
        "q": q,
        "seed": seed,
        "type": "fpLLL",
        "slope": f"{slope(profile):.6f}",
        "rhf": f"{rhf(profile):.5f}",
    }
    output_data(
        list(data.values()) + [f"{metrics['real']:.2f}", f"{metrics['user']:.2f}", f"{metrics['sys']:.2f}"],
        output_file,
    )


# optlll is intentionally disabled because KEF21 is not normally needed for these benchmarks.
# def test_kef21(m, q, seed, output_file):
#     path = ensure_lattice(m, q, seed)
#     output_lattice = OUTPUT_DIR / f"temp_kef21_{m}_{q}_{seed}.lat"
#     command = ["optlll", "-p", str(NUM_THREADS), "<", str(path), ">", str(output_lattice)]
#     run_command(
#         command,
#         {"m": m, "q": q, "seed": seed, "type": f"KEF21 ({NUM_THREADS} threads)"},
#         output_file,
#     )
