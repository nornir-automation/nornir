class GlobalState(object):
    """
    This class is just a placeholder to share data amongst different
    versions of Nornir after running ``filter`` multiple times.

    Attributes:
        failed_hosts: Hosts that have failed to run a task properly
    """

    def __init__(self):
        self.dry_run = None
        self.failed_hosts = set()

    def recover_host(self, host):
        """Remove ``host`` from list of failed hosts."""
        self.failed_hosts.discard(host)

    def reset_failed_hosts(self):
        """Reset failed hosts and make all hosts available for future tasks."""
        self.failed_hosts = set()

    def to_dict(self):
        """ Return a dictionary representing the object. """
        return self.__dict__
