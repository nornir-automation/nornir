import os
import uuid

from nornir.plugins.tasks import networking

THIS_DIR = os.path.dirname(os.path.realpath(__file__))


class Test(object):
    def test_netmiko_file_transfer(self, nornir):
        u = uuid.uuid4()
        source_file = os.path.join(THIS_DIR, "data", "test_file.txt")
        dest_file = f"test_file-{u}.txt"
        result = nornir.filter(name="dev4.group_2").run(
            networking.netmiko_file_transfer,
            source_file=source_file,
            dest_file=dest_file,
            direction="put",
        )
        assert result
        for h, r in result.items():
            assert r.result
            assert r.changed
