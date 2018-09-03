class GlobalState(object):
    """
    This class is just a placeholder to share data amongst different
    versions of Nornir after running ``filter`` multiple times.

    Attributes:
        failed_hosts (list): Hosts that have failed to run a task properly
    """

    dry_run = None
    failed_hosts = set()

    @classmethod
    def recover_host(cls, host):
        """Remove ``host`` from list of failed hosts."""
        cls.failed_hosts.discard(host)

    @classmethod
    def reset_failed_hosts(cls):
        """Reset failed hosts and make all hosts available for future tasks."""
        cls.failed_hosts = set()

    @classmethod
    def to_dict(cls):
        """ Return a dictionary representing the object. """
        return cls.__dict__
