"""
conftest.py

Helps pass parameter to the pytest
"""

from pytest import fixture

def pytest_addoption(parser):
    """Define what parameters to pass through CLI"""
    parser.addoption("--playbook_id", action="store",default="hello",help="Playbook ID")
    parser.addoption("--delimiter", action="store",default="-",help="Intent name delimiter")


@fixture()
def playbook_id(request):
    """Gets the playbook_id parameter from CLI"""
    return request.config.getoption("--playbook_id")

@fixture()
def delimiter(request):
    """Gets the delimiter parameter from CLI"""
    return request.config.getoption("--delimiter")
