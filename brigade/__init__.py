import pkg_resources

try:
    __version__ = pkg_resources.get_distribution('brigade').version
except pkg_resources.DistributionNotFound:
    __version__ = "Not installed"
