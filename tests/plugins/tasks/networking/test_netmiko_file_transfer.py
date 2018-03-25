from brigade.plugins.tasks import networking


class Test(object):
    def test_netmiko_file_transfer(self, brigade):
        source_file = 'test_file.txt'
        dest_file = 'test_file.txt'
        result = brigade.filter(name="dev4.group_2").run(networking.netmiko_file_transfer,
                                                         source_file=source_file,
                                                         dest_file=dest_file,
                                                         direction='put')
        assert result
        for h, r in result.items():
            assert r.result
            assert r.changed
