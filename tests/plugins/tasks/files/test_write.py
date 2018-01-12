import os
import uuid

from brigade.plugins.tasks import files


content_a = """
BLAH
BLEH
BLIH
BLOH
BLUH
"""

content_b = """
BLAH
BLOH
BLUH BLUH
BLIH
"""


diff_new = """--- /tmp/brigade-write/dev3.group_2-f66d9331-3eeb-4912-98b9-37f55ac48deb

+++ new

@@ -0,0 +1,6 @@

+
+BLAH
+BLEH
+BLIH
+BLOH
+BLUH"""

diff_overwrite = """--- /tmp/brigade-write/dev4.group_2-e63969eb-2261-4200-8913-196a12f4d791

+++ new

@@ -1,6 +1,5 @@

 
 BLAH
-BLEH
+BLOH
+BLUH BLUH
 BLIH
-BLOH
-BLUH"""  # noqa


diff_append = """--- /tmp/brigade-write/dev4.group_2-36ea350d-6623-4098-a961-fc143504eb42

+++ new

@@ -4,3 +4,8 @@

 BLIH
 BLOH
 BLUH
+
+BLAH
+BLOH
+BLUH BLUH
+BLIH"""  # noqa


BASEPATH = "/tmp/brigade-write"
if not os.path.exists(BASEPATH):
    os.makedirs(BASEPATH)


def _test_write(task):
    filename = "{}/{}-{}".format(BASEPATH, task.host, str(uuid.uuid4()))
    r = task.run(files.write,
                 filename=filename,
                 content=content_a)

    assert r.diff.splitlines()[1:] == diff_new.splitlines()[1:]
    assert r.changed

    task.dry_run = False
    r = task.run(files.write,
                 filename=filename,
                 content=content_a)

    assert r.diff.splitlines()[1:] == diff_new.splitlines()[1:]
    assert r.changed

    task.dry_run = False
    r = task.run(files.write,
                 filename=filename,
                 content=content_a)

    assert not r.diff
    assert not r.changed


def _test_overwrite(task):
    filename = "{}/{}-{}".format(BASEPATH, task.host, str(uuid.uuid4()))
    task.dry_run = False

    r = task.run(files.write,
                 filename=filename,
                 content=content_a)

    assert r.diff.splitlines()[1:] == diff_new.splitlines()[1:]
    assert r.changed

    r = task.run(files.write,
                 filename=filename,
                 content=content_b)

    assert r.diff.splitlines()[1:] == diff_overwrite.splitlines()[1:]
    assert r.changed

    r = task.run(files.write,
                 filename=filename,
                 content=content_b)

    assert not r.diff
    assert not r.changed


def _test_append(task):
    filename = "{}/{}-{}".format(BASEPATH, task.host, str(uuid.uuid4()))
    task.dry_run = False

    r = task.run(files.write,
                 filename=filename,
                 content=content_a)

    assert r.diff.splitlines()[1:] == diff_new.splitlines()[1:]
    assert r.changed

    r = task.run(files.write,
                 filename=filename,
                 content=content_b,
                 append=True)

    assert r.diff.splitlines()[1:] == diff_append.splitlines()[1:]
    assert r.changed


class Test(object):

    def test_write(self, brigade):
        brigade.run(_test_write)

    def test_overwrite(self, brigade):
        brigade.run(_test_overwrite)

    def test_append(self, brigade):
        brigade.run(_test_append)
