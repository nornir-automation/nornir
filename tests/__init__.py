import os

import pytest

skip = pytest.mark.skipif(
    os.getenv("NORNIR_TESTS") != "1", reason="This test can only run in Docker"
)
