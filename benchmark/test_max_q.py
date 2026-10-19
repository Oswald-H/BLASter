import subprocess

import pytest
from _benchmark_utils import (
    BLASTER_COMMAND,
    RESULTS_DIR,
    ensure_directory,
    ensure_max_q_lattice,
    run_timed,
)

NUM_TRIALS = 10
DIMENSIONS = range(2**4, 2**9 + 1, 2**4)
ERROR_FILE = RESULTS_DIR / "max_q_errors.txt"


@pytest.fixture(scope="session", autouse=True)
def print_header():
    print("m,lgq,num_success,time_min,time_avg,time_max", flush=True)


@pytest.fixture(scope="session")
def error_file():
    ensure_directory(ERROR_FILE.parent)
    ERROR_FILE.write_text("", encoding="utf8")
    return ERROR_FILE


def write_error(message, error_file):
    with error_file.open("a", encoding="utf8") as output:
        print(message, file=output)


def run_blaster(m, lgq, seed, path, error_file):
    timeout = 5 if m < 256 else 15
    command = [*BLASTER_COMMAND, "-i", str(path)]
    print(f'Executing "{" ".join(command)}".', flush=True)
    try:
        result, metrics = run_timed(command, timeout=timeout)
    except subprocess.TimeoutExpired:
        write_error(f'Timeout expired for command "{" ".join(command)}"', error_file)
        return None
    if result.returncode != 0:
        description = f"BLASter(m={m}, lgq={lgq}, seed={seed})"
        write_error(f"{description} finished with error code {result.returncode}.", error_file)
        write_error(result.stderr, error_file)
        return None
    return metrics["real"]


def count_successes(m, lgq, error_file):
    walltimes = []
    for seed in range(NUM_TRIALS):
        path = ensure_max_q_lattice(m, lgq, seed)
        result = run_blaster(m, lgq, seed, path, error_file)
        if result:
            walltimes.append(result)

    min_time, avg_time, max_time = (
        (min(walltimes), sum(walltimes) / len(walltimes), max(walltimes)) if walltimes else (0, 0, 0)
    )
    print(f"{m:4d},{lgq:2d},{len(walltimes):2d},{min_time:6.2f},{avg_time:6.2f},{max_time:6.2f}", flush=True)
    return len(walltimes)


@pytest.mark.parametrize("m", DIMENSIONS)
def test_max_q(m, error_file):
    for lgq in range(30, 65):
        if count_successes(m, lgq, error_file) == 0:
            break
