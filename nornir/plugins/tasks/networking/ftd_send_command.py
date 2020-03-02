from typing import Any, List, Optional

from nornir.core.task import Result, Task

import time
import socket
import warnings
import re

warnings.filterwarnings(action="ignore", module=".*paramiko.*")


class Base:
    def __init__(self) -> None:
        self.conn, self.cli, self.server, self.username, self.password = None, None, None, None, None
        self.find_prompt = bytes()
        socket.setdefaulttimeout(1800.0)

    def connect(self, task: Task) -> None:
        self.server, self.username, self.password = task.host.hostname, task.host.username, task.host.password
        if not task.host.port:
            task.host.port = 22
        self.conn = task.host.get_connection("paramiko", task.nornir.config)
        self.cli = self.conn.invoke_shell(width=160, height=2048)
        time.sleep(5)

    @staticmethod
    def default_prompts() -> list:
        return list()

    def send_command(self,
                     command: Optional[str] = None,
                     prompt: Optional[List[str]] = None,
                     buf: int = 4096, timeout: float = 30.0) -> str:

        cli_output = bytes()
        self.cli.settimeout(timeout)
        self.cli.setblocking(0)
        if command:
            while True:
                if self.cli.send_ready():
                    self.cli.sendall("{}\n".format(command))
                    time.sleep(0.3)
                    break
                time.sleep(2.0)
            while True:
                while True:
                    if self.cli.recv_ready():
                        time.sleep(0.3)
                        break
                    time.sleep(2.0)
                output = self.cli.recv(buf).decode("utf-8")
                if command in output:
                    output = output.replace(command, self.find_prompt.decode("utf-8") + command)

                cli_output += output.encode("utf-8")
                if output:
                    output = output.split("\n")[-1].replace("\r", "").replace("\n", "")
                    self.find_prompt = output.encode("utf-8")
                    if prompt and isinstance(prompt, list):
                        if [True for i in prompt if re.match(i, output) is not False]:
                            return "\n".join(cli_output.decode("utf-8").splitlines()[1:])
                    else:
                        if [True for i in self.default_prompts() if re.match(i, output) is not None]:
                            return "\n".join(cli_output.decode("utf-8").splitlines()[1:])


class FTDCLI(Base):
    def __init__(self) -> None:
        super(FTDCLI, self).__init__()
        self.is_admin_prompt, self.is_diagnostic_prompt = False, False

    @staticmethod
    def default_prompts() -> list:
        return [r".*[>]\s$", r".*[#]\s$", r".*[$]\s$"]

    def enter_expert_mode(self) -> None:
        if not self.is_admin_prompt:
            self.send_command(command="expert")
            self.send_command(command="sudo su", prompt=[r"Password:\s$"])
            self.send_command(command=self.password)
            self.is_diagnostic_prompt, self.is_admin_prompt = False, True

    def exit_expert_mode(self) -> None:
        if self.is_admin_prompt:
            self.send_command(command="exit")
            self.send_command(command="exit")
            self.is_diagnostic_prompt, self.is_admin_prompt = False, False

    def enter_diagnostic_cli(self) -> None:
        if not self.is_diagnostic_prompt:
            self.send_command(command="system support diagnostic-cli", prompt=[r">\s$"])
            self.send_command(command="enable", prompt=[r"Password:\s$"])
            self.send_command(command="\n", prompt=[r"firepower#\s$"])
            self.is_diagnostic_prompt, self.is_admin_prompt = True, False
            self.send_command(command='terminal pager 0', prompt=[r"firepower#\s$"])

    def exit_diagnostic_cli(self) -> None:
        if self.is_diagnostic_prompt:
            self.send_command(command="exit", prompt=[r"firepower>\s$"])
            self.send_command(command="exit")
            self.is_diagnostic_prompt, self.is_admin_prompt = False, False


def ftd_send_command(
    task: Task,
    command_string: str,
    command_mode: Optional[str] = None,
    prompt: Optional[List[str]] = None,
    **kwargs: Any
) -> Result:
    """
    Execute FTD send_command method (or send_command_timing)

    Arguments:
        command_string: Command to execute on the remote network device.
        command_mode: The CLI on a Firepower Threat Defense device has different modes, which are really separate CLIs rather than sub-modes to a single CLI. You can tell which mode you are in by looking at the command prompt.
            - Regular: Use this CLI for Firepower Threat Defense management configuration and troubleshooting.
                - Prompt: >
            - Diagnostic: Use this CLI for advanced troubleshooting. This CLI includes additional show and other commands, including the session wlan console command needed to enter the CLI for the wireless access point on an ASA 5506W-X.
                - Prompt: firepower#
            - Expert: Use Expert Mode only if a documented procedure tells you it is required, or if the Cisco Technical Assistance Center asks you to use it.
                - Prompt: root@firepower:/home/admin#
        prompt: A list strings of regular expressions to exit the prompt at a specific regex patten.
        kwargs: Additional arguments to pass to send_command method.

    Returns:
        Result object with the following attributes set:
          * result: Result of the show command (generally a string, but depends on use of TextFSM).
    """

    cli = task.host.connections.get('ftd_connection')
    if not cli:
        cli = FTDCLI()
        cli.connect(task)
        task.host.connections['ftd_connection'] = cli

    if command_mode.capitalize() == 'Expert':
        if cli.is_diagnostic_prompt:
            cli.exit_diagnostic_cli()
        cli.enter_expert_mode()
    elif command_mode.capitalize() == 'Diagnostic':
        if cli.is_admin_prompt:
            cli.exit_expert_mode()
        cli.enter_diagnostic_cli()
    else:
        if cli.is_admin_prompt:
            cli.exit_expert_mode()
        elif cli.is_diagnostic_prompt:
            cli.exit_diagnostic_cli()

    result = cli.send_command(command_string, prompt)
    return Result(host=task.host, result=result)
