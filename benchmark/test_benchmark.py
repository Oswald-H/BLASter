import os

import pytest
from _benchmark_utils import (
    BENCHMARK_DIR,
    BLASTER_COMMAND,
    FLATTER_LOG_DIR,
    LOG_DIR,
    OTHER_LOG_HEADER,
    OUTPUT_DIR,
    append_csv,
    ensure_directory,
    ensure_lattice,
    run_timed,
)
from flatter_conversion import convert_logfiles

from blaster.lattice_io import read_qary_lattice
from blaster.stats import get_profile, rhf, slope

# Specify which lattices we want to test:
MQS = [
    (128, 631),  # latticegen q 2 1 10 p
    (256, 829561),  # latticegen q 2 1 20 p
    (512, 968665207),  # latticegen q 2 1 30 p
    (1024, 968665207),  # latticegen q 2 1 30 p
]
SEEDS = range(10)

DEEPLLL_DEPTH = 4
BKZ_BETA = 60
BKZ_PROG = 2
NUM_THREADS = 1
FLATTER_ALPHA = None

LATTICES = [(m, q, seed) for m, q in MQS for seed in SEEDS]
LATTICE_IDS = [f"m{m}-q{q}-seed{seed}" for m, q, seed in LATTICES]


@pytest.fixture(scope="session")
def other_log_files():
    log_files = {}
    for m, _ in MQS:
        path = BENCHMARK_DIR / f"logs_other_{m}.csv"
        path.write_text(f"{OTHER_LOG_HEADER}\n", encoding="utf8")
        log_files[m] = path
    return log_files


def run_blaster(path, options, logfile):
    ensure_directory(logfile.parent)
    command = [*BLASTER_COMMAND, "-i", str(path), "-l", str(logfile), *options]
    print(f'Executing "{" ".join(command)}".', flush=True)
    result, _ = run_timed(command)
    if result.returncode != 0:
        logfile.unlink(missing_ok=True)
        raise RuntimeError(result.stderr)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_lll(m, q, seed):
    path = ensure_lattice(m, q, seed)
    logfile = LOG_DIR / f"lll_{m}_{q}_{seed}.csv"
    run_blaster(path, [], logfile)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_deeplll(m, q, seed):
    path = ensure_lattice(m, q, seed)
    logfile = LOG_DIR / f"deeplll{DEEPLLL_DEPTH}_{m}_{q}_{seed}.csv"
    run_blaster(path, ["-d", str(DEEPLLL_DEPTH)], logfile)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_pbkz(m, q, seed):
    path = ensure_lattice(m, q, seed)
    logfile = LOG_DIR / f"progbkz{BKZ_BETA}_{m}_{q}_{seed}.csv"
    options = ["-b", str(BKZ_BETA), "-P", str(BKZ_PROG), "-t", "1"]
    run_blaster(path, options, logfile)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_flatter(m, q, seed):
    path = ensure_lattice(m, q, seed)
    ensure_directory(FLATTER_LOG_DIR)
    flogfile = FLATTER_LOG_DIR / f"{m}_{q}_{seed}.log"
    plogfile = LOG_DIR / f"flatter_{m}_{q}_{seed}.csv"
    ensure_directory(plogfile.parent)
    flogfile.unlink(missing_ok=True)

    command = ["flatter", "-q", str(path)]
    if FLATTER_ALPHA is not None:
        command.extend(["-alpha", str(FLATTER_ALPHA)])
    env = os.environ | {
        "OMP_NUM_THREADS": str(NUM_THREADS),
        "FLATTER_LOG": str(flogfile),
    }
    print(f'Executing "{" ".join(command)}".', flush=True)
    run_timed(command, env=env)
    if not flogfile.exists():
        raise RuntimeError(f"flatter did not create the expected log file: {flogfile}")
    convert_logfiles(flogfile, plogfile)


@pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
def test_fplll(m, q, seed, other_log_files):
    path = ensure_lattice(m, q, seed)
    temp_lat = OUTPUT_DIR / f"temp_fplll_{m}_{q}_{seed}.lat"
    command = ["fplll", str(path)]
    print(f'Executing "{" ".join(command)}".', flush=True)
    result, metrics = run_timed(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    temp_lat.write_text(result.stdout, encoding="utf8")

    profile = get_profile(read_qary_lattice(temp_lat))
    data = [
        seed,
        "fpLLL",
        f"{slope(profile):.6f}",
        f"{rhf(profile):.5f}",
        f"{metrics['real']:.2f}",
        f"{metrics['user']:.2f}",
        f"{metrics['sys']:.2f}",
    ]
    append_csv(other_log_files[m], data)


# optlll is intentionally disabled because KEF21 is not normally needed for these benchmarks.
# def run_kef21(m, q, seed, path, num_threads, other_log_files):
#     temp_lat = OUTPUT_DIR / f"temp_kef21_{m}_{q}_{seed}.lat"
#     command = ["optlll", "-p", str(num_threads), "<", str(path), ">", str(temp_lat)]
#     result, metrics = run_timed(command)
#     profile = get_profile(read_qary_lattice(temp_lat))
#     data = [
#         seed,
#         f"KEF21 ({num_threads} threads)",
#         f"{slope(profile):.6f}",
#         f"{rhf(profile):.5f}",
#         f"{metrics['real']:.2f}",
#         f"{metrics['user']:.2f}",
#         f"{metrics['sys']:.2f}",
#     ]
#     append_csv(other_log_files[m], data)
#
#
# @pytest.mark.parametrize(("m", "q", "seed"), LATTICES, ids=LATTICE_IDS)
# def test_kef21(m, q, seed, other_log_files):
#     path = ensure_lattice(m, q, seed)
#     run_kef21(m, q, seed, path, NUM_THREADS, other_log_files)
