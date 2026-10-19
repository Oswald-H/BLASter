import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-benchmarks",
        action="store_true",
        default=False,
        help="Run the long-running benchmark suite.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-benchmarks"):
        return
    skip_benchmark = pytest.mark.skip(reason="Long-running benchmark; pass --run-benchmarks to execute it.")
    for item in items:
        item.add_marker(skip_benchmark)
