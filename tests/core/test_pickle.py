import pickle  # noqa: S403

import pytest

from nornir.core.task import MultiResult


class Test:
    def test_pickle(self) -> None:
        """
        Makes sure that MultiResult is pickleable - allows
        Nornir to work with Multiprocessing based runners
        """
        try:
            pickle.dumps(MultiResult("fake_result"))
        except Exception as e:
            pytest.fail(f"Exception {e} was raised")
