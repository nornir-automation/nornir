from importlib.metadata import version

from nornir.init_nornir import AInitNornir, InitNornir

__version__ = version("nornir")

__all__ = ("AInitNornir", "InitNornir", "__version__")
