class CommandError(Exception):
    """
    Raised when there is a command error.

    Attributes:
        status_code (int): status code returned by the command
        stdout (str): stdout
        stderr (str): stderr
        command (str): command that triggered the error
    """

    def __init__(self, message, command, status_code, stdout, stderr):
        super().__init__(message)
        self.status_code = status_code
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
