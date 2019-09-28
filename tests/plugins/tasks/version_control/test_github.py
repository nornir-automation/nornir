import tempfile

from nornir.plugins.tasks.version_control import github


diff_create = """--- 

+++ dummy

@@ -0,0 +1 @@

+dummy"""  # noqa

diff_update = """--- dummy

+++ dummy

@@ -1 +1 @@

-dummy
+new line"""

diff_get = """--- {f}

+++ {f}

@@ -0,0 +1 @@

+content"""


def create_file(
    nornir,
    requests_mock,
    url,
    owner,
    repository,
    branch,
    filename,
    content,
    action,
    dry_run,
    commit_message,
    repo_status_code,
    repo_resp,
    branch_status_code,
    branch_resp,
    file_status_code,
    file_resp,
    create_status_code,
    create_resp,
):
    token = "dummy"

    repo_url = f"{url}/repos/{owner}/{repository}"
    requests_mock.get(repo_url, status_code=repo_status_code, json=repo_resp)

    branch_url = f"{repo_url}/branches/{branch}"
    requests_mock.get(branch_url, status_code=branch_status_code, json=branch_resp)

    file_url = f"{repo_url}/contents/{filename}?ref={branch}"
    requests_mock.get(file_url, status_code=file_status_code, json=file_resp)

    create_file_url = f"{repo_url}/contents/{filename}"
    requests_mock.put(create_file_url, status_code=create_status_code, json=create_resp)

    res = nornir.run(
        github,
        url=url,
        token=token,
        owner=owner,
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
    owner,
    repository,
    branch,
    filename,
    content,
    dry_run,
    commit_message,
    repo_status_code,
    repo_resp,
    branch_status_code,
    branch_resp,
    file_status_code,
    file_resp,
    update_status_code,
    update_resp,
):
    token = "dummy"

    repo_url = f"{url}/repos/{owner}/{repository}"
    requests_mock.get(repo_url, status_code=repo_status_code, json=repo_resp)

    branch_url = f"{repo_url}/branches/{branch}"
    requests_mock.get(branch_url, status_code=branch_status_code, json=branch_resp)

    file_url = f"{repo_url}/contents/{filename}?ref={branch}"
    requests_mock.get(file_url, status_code=file_status_code, json=file_resp)

    update_file_url = f"{repo_url}/contents/{filename}"
    requests_mock.put(update_file_url, status_code=update_status_code, json=update_resp)

    res = nornir.run(
        github,
        url=url,
        token=token,
        owner=owner,
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
    owner,
    repository,
    filename,
    destination,
    ref,
    dry_run,
    repo_status_code,
    repo_resp,
    ref_status_code,
    ref_resp,
    file_status_code,
    file_resp,
):
    token = "dummy"

    repo_url = f"{url}/repos/{owner}/{repository}"
    requests_mock.get(repo_url, status_code=repo_status_code, json=repo_resp)

    ref_url = f"{repo_url}/commits/{ref}"
    requests_mock.get(ref_url, status_code=ref_status_code, json=ref_resp)

    file_url = f"{repo_url}/contents/{filename}?ref={ref}"
    requests_mock.get(file_url, status_code=file_status_code, json=file_resp)

    res = nornir.run(
        github,
        url=url,
        token=token,
        owner=owner,
        repository=repository,
        filename=filename,
        destination=destination,
        action="get",
        dry_run=dry_run,
        ref=ref,
    )
    return res


class Test(object):
    def test_github_create_dry_run(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=True,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=200,
            branch_resp={"name": "master"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
            create_status_code=201,
            create_resp={"branch": "master", "file_path": "dummy"},
        )

        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_create

    def test_github_create(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=200,
            branch_resp={"name": "master"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
            create_status_code=201,
            create_resp={"branch": "master", "file_path": "dummy"},
        )

        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_create

    def test_github_create_file_exists(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=200,
            branch_resp={"name": "master"},
            file_status_code=200,
            file_resp={"name": "dummy", "content": "ZHVtbXk=\n", "sha": "3d21ec5"},
            create_status_code=201,
            create_resp={"branch": "master", "file_path": "dummy"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_create_invalid_repo(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            repo_status_code=404,
            repo_resp={"message": "Not Found"},
            branch_status_code=404,
            branch_resp={"message": "Not Found"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
            create_status_code=201,
            create_resp={"branch": "master", "file_path": "dummy"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_create_invalid_branch(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = create_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="bar",
            filename="dummy",
            content="dummy",
            action="create",
            dry_run=False,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=404,
            branch_resp={"message": "Branch not found"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
            create_status_code=201,
            create_resp={"branch": "master", "file_path": "dummy"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_update_dry_run(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=True,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=200,
            branch_resp={"name": "master"},
            file_status_code=200,
            file_resp={"name": "dummy", "content": "ZHVtbXk=\n", "sha": "3d21ec5"},
            update_status_code=200,
            update_resp={"content": {"name": "dummy", "path": "dummy"}},
        )

        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_update

    def test_github_update(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=200,
            branch_resp={"name": "master"},
            file_status_code=200,
            file_resp={"name": "dummy", "content": "ZHVtbXk=\n", "sha": "3d21ec5"},
            update_status_code=200,
            update_resp={"content": {"name": "dummy", "path": "dummy"}},
        )

        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff_update

    def test_github_update_invalid_repo(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            repo_status_code=404,
            repo_resp={"message": "Not Found"},
            branch_status_code=200,
            branch_resp={"name": "master"},
            file_status_code=200,
            file_resp={"name": "dummy", "content": "ZHVtbXk=\n", "sha": "3d21ec5"},
            update_status_code=200,
            update_resp={"content": {"name": "dummy", "path": "dummy"}},
        )
        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_update_invalid_branch(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="bar",
            filename="dummy",
            content="new line",
            dry_run=False,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=404,
            branch_resp={"message": "Not Found"},
            file_status_code=200,
            file_resp={"name": "dummy", "content": "ZHVtbXk=\n", "sha": "3d21ec5"},
            update_status_code=200,
            update_resp={"content": {"name": "dummy", "path": "dummy"}},
        )
        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_update_invalid_file(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = update_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            branch="master",
            filename="bar",
            content="new line",
            dry_run=False,
            commit_message="commit",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            branch_status_code=200,
            branch_resp={"name": "master"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
            update_status_code=200,
            update_resp={"content": {"name": "dummy", "path": "dummy"}},
        )
        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_get_dry_run(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        t_file = tempfile.NamedTemporaryFile()
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            filename="bar",
            destination=t_file.name,
            ref="master",
            dry_run=True,
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            ref_status_code=200,
            ref_resp={"name": "master"},
            file_status_code=200,
            file_resp={"name": "dummy", "content": "Y29udGVudA==\n", "sha": "3d21ec5"},
        )

        diff = diff_get.format(f=t_file.name)
        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff

    def test_github_get(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        t_file = tempfile.NamedTemporaryFile()
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            filename="bar",
            destination=t_file.name,
            ref="master",
            dry_run=False,
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            ref_status_code=200,
            ref_resp={"name": "master"},
            file_status_code=200,
            file_resp={"name": "dummy", "content": "Y29udGVudA==\n", "sha": "3d21ec5"},
        )

        diff = diff_get.format(f=t_file.name)
        assert not res["dev1.group_1"][0].failed
        assert res["dev1.group_1"][0].changed
        assert res["dev1.group_1"][0].diff == diff

    def test_github_get_invalid_repo(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            filename="bar",
            destination="/tmp/foo",
            ref="master",
            dry_run=False,
            repo_status_code=404,
            repo_resp={"message": "Not Found"},
            ref_status_code=404,
            ref_resp={"message": "Not Found"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_get_ref(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            filename="bar",
            destination="/tmp/foo",
            ref="master1",
            dry_run=False,
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            ref_status_code=404,
            ref_resp={"message": "Not Found"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed

    def test_github_get_invalid_file(self, nornir, requests_mock):
        nornir = nornir.filter(name="dev1.group_1")
        res = get_file(
            nornir=nornir,
            requests_mock=requests_mock,
            url="http://localhost",
            owner="dummy",
            repository="test",
            filename="baz",
            dry_run=False,
            destination="/tmp/foo",
            ref="master",
            repo_status_code=200,
            repo_resp={"name": "dummy"},
            ref_status_code=200,
            ref_resp={"name": "master"},
            file_status_code=404,
            file_resp={"message": "Not Found"},
        )

        assert res["dev1.group_1"][0].failed
        assert not res["dev1.group_1"][0].changed
