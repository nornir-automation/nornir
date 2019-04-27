import os
import uuid

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
    pid,
    branch,
    filename,
    content,
    action,
    dry_run,
    commit_message,
    status_code,
    project_status_code,
    project_resp,
    resp,
):
    token = "dummy"

    repo_url = f"{url}/api/v4/projects?search={repository}"
    requests_mock.get(repo_url, status_code=project_status_code, json=project_resp)

    create_file_url = f"{url}/api/v4/projects/{pid}/repository/files/{filename}"
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
    pid,
    branch,
    filename,
    content,
    dry_run,
    commit_message,
    status_code,
    project_status_code,
    exists_status_code,
    project_resp,
    exists_resp,
    resp,
):
    token = "dummy"

    repo_url = f"{url}/api/v4/projects?search={repository}"
    requests_mock.get(repo_url, status_code=project_status_code, json=project_resp)

    exists_file_url = (
        f"{url}/api/v4/projects/{pid}/repository/files/{filename}?ref={branch}"
    )
    requests_mock.get(exists_file_url, status_code=exists_status_code, json=exists_resp)

    update_file_url = f"{url}/api/v4/projects/{pid}/repository/files/{filename}"
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
    pid,
    filename,
    destination,
    dry_run,
    project_status_code,
    exists_status_code,
    project_resp,
    exists_resp,
    ref,
):
    token = "dummy"

    repo_url = f"{url}/api/v4/projects?search={repository}"
    requests_mock.get(repo_url, status_code=project_status_code, json=project_resp)

    exists_file_url = (
        f"{url}/api/v4/projects/{pid}/repository/files/{filename}?ref={ref}"
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
            pid=1,
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=True,
            commit_message="commit",
            status_code=201,
            project_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            status_code=201,
            project_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            status_code=400,
            project_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
            resp={"branch": "master", "file_path": "dummy"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_create_invalid_project(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            pid=1,
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            status_code=201,
            project_status_code=200,
            project_resp=[{"name": "aaa", "id": 1}],
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
            pid=1,
            branch="bar",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            status_code=400,
            project_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=True,
            commit_message="commit",
            status_code=200,
            project_status_code=200,
            exists_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            status_code=200,
            project_status_code=200,
            exists_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
            exists_resp={"content": "ZHVtbXk=\n"},
            resp={"branch": "master", "file_path": "dummy"},
        )
        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_update

    def test_gitlab_update_invalid_project(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            pid=1,
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            status_code=200,
            project_status_code=200,
            exists_status_code=200,
            project_resp=[{"name": "123", "id": 1}],
            exists_resp={"content": "ZHVtbXk=\n"},
            resp={"branch": "master", "file_path": "dummy"},
        )
        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_update_invalid_branch(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            pid=1,
            branch="bar",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            status_code=200,
            project_status_code=200,
            exists_status_code=400,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            branch="master",
            filename="bar",
            content="new line",
            dry_run=False,
            commit_message="commit",
            status_code=200,
            project_status_code=200,
            exists_status_code=400,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            filename="bar",
            dry_run=True,
            destination=f"/tmp/{u}",
            project_status_code=200,
            exists_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            filename="bar",
            dry_run=False,
            destination=f"/tmp/{u}",
            project_status_code=200,
            exists_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
            exists_resp={"content": "Y29udGVudA==\n"},
            ref="master",
        )

        diff = diff_get.format(f=u)
        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff

    def test_gitlab_get_invalid_project(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            pid=2,
            filename="bar",
            dry_run=False,
            destination="/tmp/foo",
            project_status_code=400,
            exists_status_code=200,
            project_resp=[{"name": "test", "id": 1}],
            exists_resp={"content": "Y29udGVudA==\n"},
            ref="master",
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_gitlab_get_invalid_branch(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            repository="test",
            pid=1,
            filename="bar",
            dry_run=False,
            destination="/tmp/foo",
            project_status_code=200,
            exists_status_code=400,
            project_resp=[{"name": "test", "id": 1}],
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
            pid=1,
            filename="baz",
            dry_run=False,
            destination="/tmp/foo",
            project_status_code=200,
            exists_status_code=400,
            project_resp=[{"name": "test", "id": 1}],
            exists_resp={"content": "Y29udGVudA==\n"},
            ref="",
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed
