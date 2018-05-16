import os

#  from nornir.core.exceptions import NornirExecutionError
from nornir.plugins.tasks import connections, networking

#  from napalm.base import exceptions

#  import pytest


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_cli"


class Test(object):

    def test_napalm_cli(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_cli"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(
            networking.napalm_cli, commands=["show version", "show interfaces"]
        )
        assert result
        for h, r in result.items():
            assert r.result["show version"]
            assert r.result["show interfaces"]


#  def test_napalm_cli_error(self, nornir):
#      opt = {"path": THIS_DIR + "/test_napalm_cli_error"}
#      with pytest.raises(NornirExecutionError) as e:
#          nornir.filter(name="dev3.group_2").run(networking.napalm_cli,
#                                                  num_workers=1,
#                                                  commands=["show version",
#                                                            "show interfacesa"],
#                                                  optional_args=opt)
#      assert len(e.value.failed_hosts)
#      for result in e.value.failed_hosts.values():
#          assert isinstance(result.exception, exceptions.CommandErrorException)
#          print(exc)
