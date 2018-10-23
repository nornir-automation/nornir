from nornir.init_nornir import InitNornir
import pkg_resources


try:
    __version__ = pkg_resources.get_distribution("nornir").version
except pkg_resources.DistributionNotFound:
    __version__ = "Not installed"


__all__ = ("InitNornir", "__version__")
