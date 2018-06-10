from nornir.plugins.inventory.helpers.filters import F

def test_simple(nornir):
    f = F(site="site1")
    filtered = sorted(list((nornir.filter(filter_func=f.match).inventory.hosts.keys())))

    assert filtered == ['dev1.group_1', 'dev2.group_1']


def test_and(nornir):
    f = F(site="site1") & F(role='www')
    filtered = sorted(list((nornir.filter(filter_func=f.match).inventory.hosts.keys())))

    assert filtered == ['dev1.group_1']

def test_or(nornir):
    f = F(site="site1") | F(role='www')
    filtered = sorted(list((nornir.filter(filter_func=f.match).inventory.hosts.keys())))

    assert filtered == ['dev1.group_1', 'dev2.group_1', 'dev3.group_2']
