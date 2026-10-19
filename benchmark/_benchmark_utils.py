import resource
import subprocess
import sys
import time
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BENCHMARK_DIR.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"
FLATTER_LOG_DIR = PROJECT_ROOT / "logs-flatter"
RESULTS_DIR = BENCHMARK_DIR / "results"

BLASTER_COMMAND = (sys.executable, "-m", "blaster.cli", "-q")
OTHER_LOG_HEADER = "seed,type,slope,rhf,real (s),user (s),sys (s)"
SMALL_DIM_HEADER = "m,q,seed,type,slope,rhf,real (s),user (s),sys (s)"


def ensure_directory(path):
    path.mkdir(parents=True, exist_ok=True)


def _run_latticegen(arguments, path):
    ensure_directory(path.parent)
    temporary_path = path.with_name(f"{path.name}.tmp")
    command = ["latticegen", *arguments]
    with temporary_path.open("w", encoding="utf8") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to generate lattice: {result.stderr}")
    temporary_path.replace(path)


def ensure_lattice(m, q, seed):
    path = INPUT_DIR / f"{m}_{q}_{seed}"
    if not path.exists():
        arguments = ["-randseed", str(seed), "q", str(m), str(m // 2), str(q), "q"]
        _run_latticegen(arguments, path)
    return path


def ensure_max_q_lattice(m, lgq, seed):
    path = INPUT_DIR / f"max_q_{m}_{lgq}_{seed}"
    if not path.exists():
        arguments = ["-randseed", str(seed), "q", str(m), str(m // 2), str(lgq), "p"]
        _run_latticegen(arguments, path)
    return path


def run_timed(command, *, env=None, timeout=None):
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    result = subprocess.run(
        command,
        capture_output=True,
        env=env,
        text=True,
        timeout=timeout,
    )
    real = time.perf_counter() - start
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    metrics = {
        "real": real,
        "user": usage_after.ru_utime - usage_before.ru_utime,
        "sys": usage_after.ru_stime - usage_before.ru_stime,
    }
    return result, metrics


def append_csv(path, values):
    with path.open("a", encoding="utf8") as output:
        print(",".join(str(value) for value in values), file=output)
