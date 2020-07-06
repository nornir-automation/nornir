from typing import Any
from nornir.core.connections import ConnectionPlugin
import requests

class HttpSession(ConnectionPlugin):
    """
    This plugin is a simple wrapper. Its :attr:`connection` attribute
    is a ``requests.Session``. This allows you to use cookies and HTTP
    keep-alive for even better performance when making multiple requests
    on one host.

    Inventory:
        extras:
            verify_https_certs: whether or not to verify ssl certificates
                for this session (default: ``true``)
    """
    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        # Create a session
        self.connection = requests.Session()

        # Configure the session's verify attribute
        if extras:
            self.connection.verify = extras.get('verify_https_certs', True)
        else:
            self.connection.verify = True
        
    def close(self) -> None:
        # Close the session
        self.connection.close()
