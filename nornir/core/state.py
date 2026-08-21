from __future__ import annotations

from typing import Any


class GlobalState:
    """Placeholder to share data amongst different versions of Nornir.

    The same object is shared amongst all the versions of Nornir that result from
    running ``filter`` multiple times.

    Attributes:
        failed_hosts: Hosts that have failed to run a task properly

    """

    __slots__ = "dry_run", "failed_hosts"

    def __init__(self, dry_run: bool = False, failed_hosts: set[str] | None = None) -> None:
        self.dry_run = dry_run
        self.failed_hosts = failed_hosts or set()

    def recover_host(self, host: str) -> None:
        """Remove ``host`` from list of failed hosts."""
        self.failed_hosts.discard(host)

    def reset_failed_hosts(self) -> None:
        """Reset failed hosts and make all hosts available for future tasks."""
        self.failed_hosts = set()

    def dict(self) -> dict[str, Any]:
        """Return a dictionary representing the object.

        Returns:
            The value of each attribute in ``__slots__`` keyed by its name.

        """
        return {item: getattr(self, item) for item in GlobalState.__slots__}
