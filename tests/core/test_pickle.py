from nornir.core.task import MultiResult
import pickle

class Test:
    def test_pickle(self):
        """
        Makes sure that MultiResult is pickleable - allows
        Nornir to work with Multiprocessing based runners
        """
        pickle.dumps(MultiResult("fake_result"))