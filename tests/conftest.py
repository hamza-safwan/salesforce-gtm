import pytest

from gtmdq.config import PROJECT_ROOT, GenerationConfig, read_yaml
from gtmdq.generator.pipeline import generate


@pytest.fixture(scope="session")
def configuration():
    return GenerationConfig.load(PROJECT_ROOT / "config/generation.yml")


@pytest.fixture(scope="session")
def rules():
    return read_yaml(PROJECT_ROOT / "config/segmentation.yml")


@pytest.fixture(scope="session")
def stages():
    return read_yaml(PROJECT_ROOT / "config/opportunity_stages.yml")


@pytest.fixture(scope="session")
def dataset(configuration, rules, stages):
    return generate(configuration, rules, stages)
