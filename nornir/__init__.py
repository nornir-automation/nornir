from importlib.metadata import version

from nornir.init_nornir import InitNornir

__version__ = version("nornir")

__all__ = ("InitNornir", "__version__")
