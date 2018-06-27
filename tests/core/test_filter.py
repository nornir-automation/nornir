from nornir.core.filter import F



def test_simple(nornir):
    f = F(site="site1")
    filtered = sorted(list((nornir.filter(filter_func=f).inventory.hosts.keys())))

    assert filtered == ["dev1.group_1", "dev2.group_1"]


def test_and(nornir):
    f = F(site="site1") & F(role="www")
    filtered = sorted(list((nornir.filter(filter_func=f).inventory.hosts.keys())))

    assert filtered == ["dev1.group_1"]


def test_or(nornir):
    f = F(site="site1") | F(role="www")
    filtered = sorted(list((nornir.filter(filter_func=f).inventory.hosts.keys())))

    assert filtered == ["dev1.group_1", "dev2.group_1", "dev3.group_2"]


def test_combined(nornir):
    f = F(site="site2") | (F(role="www") & F(my_var="comes_from_dev1.group_1"))
    filtered = sorted(list((nornir.filter(filter_func=f).inventory.hosts.keys())))

    assert filtered == ["dev1.group_1", "dev3.group_2", "dev4.group_2"]


def test_contains(nornir):
    f = F(groups__contains="group_1")
    filtered = sorted(list((nornir.filter(filter_func=f).inventory.hosts.keys())))

    assert filtered == ["dev1.group_1", "dev2.group_1"]


def test_negate(nornir):
    f = ~F(groups__contains="group_1")
    filtered = sorted(list((nornir.filter(filter_func=f).inventory.hosts.keys())))

    assert filtered == ["dev3.group_2", "dev4.group_2"]
