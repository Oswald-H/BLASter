import pytest
from _benchmark_utils import (
    BLASTER_COMMAND,
    LOG_DIR,
    RESULTS_DIR,
    ensure_directory,
    ensure_lattice,
    run_timed,
)

MQS = [
    (128, 631),  # latticegen q 2 1 10 p
    (256, 829561),  # latticegen q 2 1 20 p
    (512, 968665207),  # latticegen q 2 1 30 p
    (1024, 968665207),  # latticegen q 2 1 30 p
]
SEEDS = range(10)
ERROR_FILE = RESULTS_DIR / "optimal_segment_size-errors.txt"


def get_lll_sizes(m):
    for lll_size in range(32, 130, 2):
        if (
            m < 512
            or (m == 512 and lll_size not in [92, 94, 98, 104])
            or (m == 1024 and lll_size not in [76, 86, 90, 104, 106, 108, 110])
        ):
            continue
        if lll_size > m:
            break
        yield lll_size


CASES = [(m, q, lll_size, seed) for m, q in MQS for lll_size in get_lll_sizes(m) for seed in SEEDS]
CASE_IDS = [f"m{m}-q{q}-L{lll_size}-seed{seed}" for m, q, lll_size, seed in CASES]


@pytest.fixture(scope="session", autouse=True)
def print_header():
    print("m,q,LLLsize,seed,real,user,sys", flush=True)


def write_error(message):
    ensure_directory(ERROR_FILE.parent)
    with ERROR_FILE.open("a", encoding="utf8") as output:
        print(message, file=output)


def run_blaster(m, q, seed, lll_size, options=()):
    path = ensure_lattice(m, q, seed)
    logfile = LOG_DIR / "optimal_segment_size" / f"lll_{m}_{q}_{seed}_{lll_size}.csv"
    ensure_directory(logfile.parent)
    command = [*BLASTER_COMMAND, "-i", str(path), "-l", str(logfile), "-L", str(lll_size), *options]
    print(f'Executing "{" ".join(command)}".', flush=True)
    result, metrics = run_timed(command)
    if result.returncode != 0:
        write_error(f'Non zero return code encountered for command "{" ".join(command)}"')
        write_error(result.stderr)
        raise RuntimeError(result.stderr)
    return metrics


def run_blaster_deeplll(m, q, seed, lll_size, depth):
    return run_blaster(m, q, seed, lll_size, ["-d", str(depth)])


@pytest.mark.parametrize(("m", "q", "lll_size", "seed"), CASES, ids=CASE_IDS)
def test_lll(m, q, lll_size, seed):
    metrics = run_blaster(m, q, seed, lll_size)
    print(
        f"{m:4d},{q:9d},{lll_size},{seed:1d},{metrics['real']:6.2f},{metrics['user']:6.2f},{metrics['sys']:6.2f}",
        flush=True,
    )
