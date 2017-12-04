#  from brigade.core.exceptions import BrigadeExecutionError, CommandError
#  from brigade.plugins.tasks import networking

#  import pytest


#  class Test(object):

#      def test_netmiko_run(self, brigade):
#          result = brigade.filter(name="host4.group_2").run(networking.netmiko_run,
#                                                            method="send_command",
#                                                            cmd_args="hostname")
#          assert result
#          for h, r in result.items():
#              import pdb
#              pdb.set_trace()

#      #  def test_remote_command_error_generic(self, brigade):
#      #      with pytest.raises(BrigadeExecutionError) as e:
#      #          brigade.run(commands.remote_command,
#      #                      command="ls /asdadsd")
#      #      assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
#      #      for exc in e.value.failed_hosts.values():
#      #          assert isinstance(exc, CommandError)
