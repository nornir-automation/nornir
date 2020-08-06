import uuid
import os

from urllib.parse import quote

from nornir.plugins.tasks.version_control import gitlab


BASE_PATH = os.path.join(os.path.dirname(__file__), "gitlab")

diff_create = """--- 

+++ dummy

@@ -0,0 +1 @@

+dummy"""  # noqa

diff_update = """--- dummy

+++ dummy

@@ -1 +1 @@

-dummy
+new line"""

diff_get = """--- /tmp/{f}

+++ /tmp/{f}

@@ -0,0 +1 @@

+content"""


def create_file(
    nornir,
    requests_mock,
    url,
    repository,
    branch,
    filename,
    content,
    action,
    dry_run,
    commit_message,
    status_code,
    resp,
):
    token = "dummy"

    quoted_repository = quote(repository, safe="")
    create_file_url = (
        f"{url}/api/v4/projects/{quoted_repository}/repository/files/{filename}"
    )
    requests_mock.post(create_file_url, status_code=status_code, json=resp)

    res = nornir.run(
        gitlab,
        url=url,
        token=token,
        repository=repository,
        filename=filename,
        content=content,
        action="create",
        dry_run=dry_run,
        branch=branch,
        commit_message=commit_message,
    )
    return res


def update_file(
    nornir,
    requests_mock,
    url,
    repository,
    branch,
    filename,
    content,
    dry_run,
    commit_message,
    status_code,
    exists_status_code,
    exists_resp,
    resp,
):
    token = "dummy"
    quoted_repository = quote(repository, safe="")
    exists_file_url = (
        f"{url}/api/v4/projects/{quoted_repository}/repository/files/{filename}"
        f"?ref={branch}"
    )
    requests_mock.get(exists_file_url, status_code=exists_status_code, json=exists_resp)

    update_file_url = (
        f"{url}/api/v4/projects/{quoted_repository}/repository/files/{filename}"
    )
    requests_mock.put(update_file_url, status_code=status_code, json=resp)

    res = nornir.run(
        gitlab,
        url=url,
        token=token,
        repository=repository,
        filename=filename,
        content=content,
        action="update",
        dry_run=dry_run,
        branch=branch,
        commit_message=commit_message,
    )
    return res


def get_file(
    nornir,
    requests_mock,
    url,
    repository,
    filename,
    destination,
    dry_run,
    exists_status_code,
    exists_resp,
    ref,
):
    token = "dummy"
    quoted_repository = quote(repository, safe="")
    exists_file_url = (
        f"{url}/api/v4/projects/{quoted_repository}/repository/files/{filename}"
        f"?ref={ref}"
    )
    requests_mock.get(exists_file_url, status_code=exists_status_code, json=exists_resp)

    res = nornir.run(
        gitlab,
        url=url,
        token=token,
        repository=repository,
        filename=filename,
        destination=destination,
        action="get",
        dry_run=dry_run,
        ref=ref,
    )
    return res


class Test(object):
    def test_gitlab_create_dry_run(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=True,
            commit_message="commit",
            status_code=201,
            resp={"branch": "master", "file_path": "dummy"},
        )

        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_create

    def test_gitlab_create(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            status_code=201,
            resp={"branch": "master", "file_path": "dummy"},
        )

        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_create

    def test_gitlab_create_file_exists(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            status_code=400,
            resp={"branch": "master", "file_path": "dummy"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_create_invalid_branch(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="bar",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            status_code=400,
            resp={"branch": "master", "file_path": "dummy"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_update_dry_run(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=True,
            commit_message="commit",
            status_code=200,
            exists_status_code=200,
            exists_resp={"content": "ZHVtbXk=\n"},
            resp={"branch": "master", "file_path": "dummy"},
        )

        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_update

    def test_gitlab_update(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            status_code=200,
            exists_status_code=200,
            exists_resp={"content": "ZHVtbXk=\n"},
            resp={"branch": "master", "file_path": "dummy"},
        )
        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_update

    def test_gitlab_update_invalid_branch(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="bar",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            status_code=200,
            exists_status_code=400,
            exists_resp="",
            resp={"branch": "master", "file_path": "dummy"},
        )
        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_update_invalid_file(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            branch="master",
            filename="bar",
            content="new line",
            dry_run=False,
            commit_message="commit",
            status_code=200,
            exists_status_code=400,
            exists_resp={"content": "ZHVtbXk=\n"},
            resp={"branch": "master", "file_path": "dummy"},
        )
        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_get_dry_run(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        u = uuid.uuid4()
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            filename="bar",
            dry_run=True,
            destination=f"/tmp/{u}",
            exists_status_code=200,
            exists_resp={"content": "Y29udGVudA==\n"},
            ref="master",
        )

        diff = diff_get.format(f=u)
        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff

    def test_gitlab_get(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        u = uuid.uuid4()
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            filename="bar",
            dry_run=False,
            destination=f"/tmp/{u}",
            exists_status_code=200,
            exists_resp={"content": "Y29udGVudA==\n"},
            ref="master",
        )

        diff = diff_get.format(f=u)
        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff

    def test_gitlab_get_invalid_branch(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            filename="bar",
            dry_run=False,
            destination="/tmp/foo",
            exists_status_code=400,
            exists_resp={"content": "Y29udGVudA==\n"},
            ref="lll",
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_get_invalid_file(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            filename="baz",
            dry_run=False,
            destination="/tmp/foo",
            exists_status_code=400,
            exists_resp={"content": "Y29udGVudA==\n"},
            ref="",
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed
