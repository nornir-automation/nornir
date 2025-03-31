from nornir.core.task import MultiResult
import pickle

class Test:
    def test_pickle(self):
        """
        Makes sure that MultiResult is pickleable - allows
        Nornir to work with Multiprocessing based runners
        """
        try:
            pickle.dumps(MultiResult("fake_result"))
        except Exception as e:
            assert False, f"Exception {e} was raised"