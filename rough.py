"""

Set of pytest humanfirst.objects.py tests

"""
# ***************************************************************************80**************************************120

# standard imports
import os
import json
from configparser import ConfigParser
from datetime import datetime
import uuid

# third party imports
import numpy
import pandas
import pytest
from dotenv import load_dotenv, find_dotenv
import humanfirst

class HFNamespaceNotAvailableException(Exception):
    """When username/password not provided by the user"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

# CONSTANTS
constants = ConfigParser()
path_to_config_file = os.path.join(here,'humanfirst','config','setup.cfg')
constants.read(path_to_config_file)

dotenv_path = find_dotenv(usecwd=True)
# load the environment variables from the .env file if present
load_dotenv(dotenv_path=dotenv_path)

TEST_NAMESPACE = os.environ.get("HF_TEST_NAMESPACE")
if TEST_NAMESPACE is None:
    raise HFNamespaceNotAvailableException("HF_TEST_NAMESPACE is not set as environment variable")

DEFAULT_DELIMITER = constants.get("humanfirst.CONSTANTS","DEFAULT_DELIMITER")

def test_tags():
    """Test tags"""

    hf_api = humanfirst.apis.HFAPI()

    playbook_name = "Test get_playbook_info"

    create_pb_res = hf_api.create_playbook(namespace=TEST_NAMESPACE,
                                           playbook_name=playbook_name)

    playbook_id = create_pb_res["etcdId"]

    # check if the playbook is available in the workspace
    list_pb = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
    valid_playbook_id = False
    for i,_ in enumerate(list_pb):
        if playbook_id == list_pb[i]["etcdId"]:
            valid_playbook_id = True
    assert valid_playbook_id is True

    try:
        pb_info = hf_api.get_playbook_info(namespace=TEST_NAMESPACE,
                                 playbook=playbook_id)

        print(json.dumps(pb_info,indent=2))

        # delete the workspace and check if the workspace is deleted
        hf_api.delete_playbook(namespace=TEST_NAMESPACE, playbook_id=playbook_id, hard_delete=True)

        # check if the provided playbook is removed from the workspace
        list_pb = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
        valid_playbook_id = False
        for i,_ in enumerate(list_pb):
            if playbook_id == list_pb[i]["etcdId"]:
                valid_playbook_id = True
        assert valid_playbook_id is False
    except humanfirst.apis.HFAPIResponseValidationException as e:
        print(e)

        # delete the workspace and check if the workspace is deleted
        hf_api.delete_playbook(namespace=TEST_NAMESPACE, playbook_id=playbook_id, hard_delete=True)

        # check if the provided playbook is removed from the workspace
        list_pb = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
        valid_playbook_id = False
        for i,_ in enumerate(list_pb):
            if playbook_id == list_pb[i]["etcdId"]:
                valid_playbook_id = True
        assert valid_playbook_id is False


test_tags()
