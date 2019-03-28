import os

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
