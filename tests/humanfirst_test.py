# pylint: disable=too-many-lines
"""

Humanfirst tests

"""
# ***************************************************************************80**************************************120

# standard imports
import time
import os
import json
from configparser import ConfigParser
from datetime import datetime
import uuid
from dateutil import parser
import logging


# third party imports
import numpy
import pandas
import pytest
from dotenv import load_dotenv, find_dotenv
import humanfirst
from humanfirst.apis import HFAPIResponseValidationException

class HFNamespaceNotAvailableException(Exception):
    """When username/password not provided by the user"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

# start logger
logger = logging.getLogger('humanfirst_test.py')
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",datefmt="%Y-%m-%d %H:%M:%S")

# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

# CONSTANTS
constants = ConfigParser()
path_to_config_file = os.path.join(here,'..','humanfirst','config','setup.cfg')
constants.read(path_to_config_file)

# constants need type conversion from str to int - TODO: setAttr loop for neatness or function
dotenv_path = find_dotenv(usecwd=True)
# load the environment variables from the .env file if present
load_dotenv(dotenv_path=dotenv_path)

TEST_NAMESPACE = os.environ.get("HF_TEST_NAMESPACE")
if TEST_NAMESPACE is None:
    TEST_NAMESPACE = constants.get("humanfirst.CONSTANTS","TEST_NAMESPACE")
    if TEST_NAMESPACE == "":
        raise HFNamespaceNotAvailableException("TEST_NAMESPACE not available")

DEFAULT_DELIMITER = constants.get("humanfirst.CONSTANTS","DEFAULT_DELIMITER")
TEST_CONVOSET = constants.get("humanfirst.CONSTANTS","TEST_CONVOSET")

# Which environment the test is running on is signficant.
logger.info(f'Running test on HF_ENVIRONMENT={os.environ.get("HF_ENVIRONMENT")}')

def _playbook_is_present(hf_api: humanfirst.apis.HFAPI,
                        namespace: str,
                        playbook_id:  str):
    """check if playbook is available"""

    # check if the provided playbook is removed from the workspace
    list_pb = hf_api.list_playbooks(namespace=namespace)
    valid_playbook_id = False
    for i,_ in enumerate(list_pb):
        if playbook_id == list_pb[i]["id"]:
            valid_playbook_id = True
    return valid_playbook_id

def _create_playbook(hf_api: humanfirst.apis.HFAPI,
                     namespace: str,
                     playbook_name:  str):
    """creates playbook"""

    create_pb_res = hf_api.create_playbook(namespace=namespace,
                                           playbook_name=playbook_name)

    playbook_id = create_pb_res["etcdId"]

    assert _playbook_is_present(hf_api=hf_api,
                        namespace=TEST_NAMESPACE,
                        playbook_id=playbook_id) is True

    return playbook_id

def _del_playbook(hf_api: humanfirst.apis.HFAPI,
                  namespace: str,
                  playbook_id:  str):
    """Delete Playbook"""

    # delete the workspace and check if the workspace is deleted
    hf_api.delete_playbook(namespace=namespace, playbook_id=playbook_id, hard_delete=True)

    assert _playbook_is_present(hf_api=hf_api,
                        namespace=TEST_NAMESPACE,
                        playbook_id=playbook_id) is False

def test_get_conversation_set_list():
    """Test filtering conversation set with conversation source id"""

    hf_api = humanfirst.apis.HFAPI()

    try:
        conversation_obj1 = hf_api.create_conversation_set_with_set_and_src_id(namespace=TEST_NAMESPACE,
                                                                            convoset_name=TEST_CONVOSET)
        try:
            conversation_obj2 = hf_api.create_conversation_set_with_set_and_src_id(namespace=TEST_NAMESPACE,
                                                                                convoset_name="dummy set")
            res = hf_api.get_conversation_set_list(namespace=TEST_NAMESPACE)

            assert len(res) >= 2

            res2 = hf_api.get_conversation_set_list(namespace=TEST_NAMESPACE,
                                                    conversation_source_id=conversation_obj1["convosrc_id"])

            assert len(res2) == 1
            logger.debug(conversation_obj1)

            hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                        convoset_id=conversation_obj2["convoset_id"])

        except (RuntimeError,AssertionError) as e:
            logger.error(e)
            hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                            convoset_id=conversation_obj2["convoset_id"])
            raise

        hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                    convoset_id=conversation_obj1["convoset_id"])

    except (RuntimeError,AssertionError) as e:
        logger.error(e)
        hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                        convoset_id=conversation_obj1["convoset_id"])
        raise

def test_simple_list_playbooks():
    """Test listing playbooks without a conversation_set_id"""
    hf_api = humanfirst.apis.HFAPI()
    hf_api.list_playbooks_old(namespace=TEST_NAMESPACE,conversation_set_id="blah")

def test_new_list_playbooks():
    """Test listing playbooks without a conversation_set_id"""
    hf_api = humanfirst.apis.HFAPI()
    hf_api.list_playbooks(namespace=TEST_NAMESPACE)

def test_list_playbooks():
    """Test listing playbooks with and without a conversation_set_id"""

    hf_api = humanfirst.apis.HFAPI()

    try:
        conversation_obj = hf_api.create_conversation_set_with_set_and_src_id(namespace=TEST_NAMESPACE,
                                                                            convoset_name=TEST_CONVOSET)
        logger.info(f'Created playbook: {conversation_obj}')

        upload_json_file_response = hf_api.upload_json_file_to_conversation_source(namespace=TEST_NAMESPACE,
                                                                conversation_source_id=conversation_obj["convosrc_id"],
                                                                upload_name="abcd_108_test",
                                                                fqfp="./examples/abcd_2022_05_convo_108.json"
                                                                )
        logger.debug(f'Uploaded JSON file response: {upload_json_file_response}')
        try:
            playbook_id1 = _create_playbook(hf_api,
                                    namespace=TEST_NAMESPACE,
                                    playbook_name="test list playbooks 1")
            logger.info(f'Created Playbook1: {playbook_id1}')

            try:
                playbook_id2 = _create_playbook(hf_api,
                                    namespace=TEST_NAMESPACE,
                                    playbook_name="test list playbooks 2")
                logger.info(f'Created Playbook2: {playbook_id2}')

                try:
                    link_res = hf_api.link_conversation_set(namespace=TEST_NAMESPACE, playbook_id=playbook_id2,
                                                            convoset_id=conversation_obj["convoset_id"])
                    logger.info(f'Linked Conversation Sets awaiting trigger next: {link_res}')

                    # check if the link trigger is completed
                    total_wait_time = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,
                                                                trigger_id=link_res["triggerId"])
                    if total_wait_time == -1:
                        raise RuntimeError('Link pipeline failed or was cancelled')
                    elif total_wait_time == 0:
                        raise RuntimeError('Link pipeline timed out')
                    else:
                        logger.info(f'Link convoset completed in: {total_wait_time}')
                        
                    # test list playbooks filtering the playbooks with conversation set attached
                    list_playbooks_res2 = hf_api.list_playbooks(namespace=TEST_NAMESPACE,
                                                            conversation_set_id=conversation_obj["convoset_id"])
                    assert isinstance(list_playbooks_res2,list)
                    assert len(list_playbooks_res2) == 1
                    assert list_playbooks_res2[0]["id"] == playbook_id2
                    assert list_playbooks_res2[0]["conversationSets"][0]["id"] == conversation_obj["convoset_id"]

                    # test list playbooks with no filtering for conversation set
                    list_playbooks_res = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
                    assert isinstance(list_playbooks_res,list)
                    assert len(list_playbooks_res) >=2

                    unlink_res = hf_api.unlink_conversation_set(namespace=TEST_NAMESPACE,
                                                                playbook_id=playbook_id2,
                                                                convoset_id=conversation_obj["convoset_id"])

                    # check if unlink trigger is completed
                    total_wait_time = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,
                                                                trigger_id=unlink_res["triggerId"])
                    if total_wait_time == -1:
                        raise RuntimeError('Unlink pipeline failed or was cancelled')
                    elif total_wait_time == 0:
                        raise RuntimeError('Unlink ipeline timed out')
                    else:
                        logger.info(f'Unlink convoset completed in: {total_wait_time}')

                    # delete conversation set
                    delete_response = hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                                                    convoset_id=conversation_obj["convoset_id"])
                    assert delete_response == {}

                    # delete the workspace and check if the workspace is deleted
                    delete_playbook_res2 = hf_api.delete_playbook(namespace=TEST_NAMESPACE,
                                                                playbook_id=playbook_id2,
                                                                hard_delete=True)
                    assert delete_playbook_res2 == {}

                    delete_playbook_res = hf_api.delete_playbook(namespace=TEST_NAMESPACE,
                                                                playbook_id=playbook_id1,
                                                                hard_delete=True)
                    assert delete_playbook_res == {}

                except (RuntimeError,AssertionError) as e:
                    logger.error(e)
                    hf_api.unlink_conversation_set(namespace=TEST_NAMESPACE,
                                                playbook_id=playbook_id2,
                                                convoset_id=conversation_obj["convoset_id"])
                    raise

            except (RuntimeError,AssertionError) as e:
                logger.error(e)
                _del_playbook(hf_api=hf_api,
                        namespace=TEST_NAMESPACE,
                        playbook_id=playbook_id2)
                raise

        except (RuntimeError,AssertionError) as e:
            logger.error(e)
            _del_playbook(hf_api=hf_api,
                    namespace=TEST_NAMESPACE,
                    playbook_id=playbook_id1)
            raise

    except (RuntimeError,AssertionError) as e:
        logger.error(e)
        hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                        convoset_id=conversation_obj["convoset_id"])
        raise

def test_playbook_creation_deletion():
    """test_playbook_creation_deletion"""

    hf_api = humanfirst.apis.HFAPI()
    # create a playbook
    playbook_id = _create_playbook(hf_api,
                            namespace=TEST_NAMESPACE,
                            playbook_name="test playbook creation")

    try:
        assert "playbook-" in playbook_id

        # delete the workspace and check if the workspace is deleted
        delete_playbook_res = hf_api.delete_playbook(namespace=TEST_NAMESPACE,
                                                    playbook_id=playbook_id,
                                                    hard_delete=True)
        assert delete_playbook_res == {}

        assert _playbook_is_present(hf_api=hf_api,
                                    namespace=TEST_NAMESPACE,
                                    playbook_id=playbook_id) is False

    except Exception as e:
        logger.error(e)
        _del_playbook(hf_api=hf_api,
                namespace=TEST_NAMESPACE,
                playbook_id=playbook_id)
        raise

def test_intent_hierarchy():
    """test_intent_hierarchy"""

    # read csv
    path_to_file = os.path.join(here,'..','examples','intent_hierarchy_example.csv')
    df = pandas.read_csv(path_to_file, sep=",")

    # create a labelled workspace from dataframe
    labelled = humanfirst.objects.HFWorkspace()
    labelled.delimiter = "-"

    for _,row in df.iterrows():
        name_or_hier = str(row["intent"]).split(labelled.delimiter)
        intent = labelled.intent(name_or_hier=name_or_hier)
        example = humanfirst.objects.HFExample(
            text=row["utterance"],
            id=f'example-{uuid.uuid4()}',
            created_at=datetime.now().isoformat(),
            intents=[intent],
            tags=[],
            metadata={}
        )
        labelled.add_example(example)

    actual_intent_names =  [
        "intent1-sub_intent1-int",
        "intent1-sub_intent1-float",
        "intent1-sub_intent1-double",
        "intent2-sub_intent1-int",
        "intent2-sub_intent1-float",
        "intent2-sub_intent1-double",
        "sub_intent1-int",
        "sub_intent1-float",
        "sub_intent1-double"
    ]

    # get intent names from the workspace created
    workspace_intent_names = []
    for _,example in labelled.examples.items():
        intent_id = example.intents[0].intent_id
        intent_name = labelled.get_fully_qualified_intent_name(intent_id=intent_id)
        workspace_intent_names.append(intent_name)
    actual_intent_names = sorted(actual_intent_names)
    workspace_intent_names = sorted(workspace_intent_names)

    # if the if the intent hierarchy isn't matched then we wouldn't get the same fully qualified intent names
    assert len(actual_intent_names) == len(workspace_intent_names)
    assert actual_intent_names == workspace_intent_names


def test_load_testdata():
    """test_load_testdata"""

    dtypes = {
        'external_id': str,
        'timestamp': str,
        'utterance': str,
        'speaker': str,
        'nlu_detected_intent': str,
        'nlu_confidence': str,
        'overall_call_star_rating': int
    }

    # read the input csv
    path_to_file=os.path.join(here,'..','examples','simple_example.csv')
    df = pandas.read_csv(path_to_file,
                         encoding='utf8', dtype=dtypes)
    assert isinstance(df, pandas.DataFrame)
    assert df.shape == (5, 7)


def test_intent_hierarchy_numbers():
    """test_intent_hierarchy_numbers"""

    labelled = humanfirst.objects.HFWorkspace()
    assert len(labelled.intents) == 0
    # multi hierachy
    intent = labelled.intent(
        name_or_hier=['billing', 'billing_issues', 'payment_late']
    )
    assert isinstance(intent, humanfirst.objects.HFIntent)
    assert intent.id == 'intent-2'
    assert intent.name == 'payment_late'
    assert intent.parent_intent_id == 'intent-1'
    assert len(labelled.intents) == 3

def test_tags():
    """Test create, delete and list tags"""

    hf_api = humanfirst.apis.HFAPI()

    playbook_name = "Test tags"

    playbook_id = _create_playbook(hf_api,
                                   namespace=TEST_NAMESPACE,
                                   playbook_name=playbook_name)

    try:
        tag_id = str(uuid.uuid4())
        tag_name = "test_tag"
        tag_color = "#a69890"

        # test create tag
        c_tag = hf_api.create_tag(namespace=TEST_NAMESPACE,
                                playbook=playbook_id,
                                tag_id=tag_id,
                                tag_name=tag_name,
                                tag_color=tag_color)

        assert c_tag["tag"]["id"] == tag_id
        assert c_tag["tag"]["name"] == tag_name
        assert c_tag["tag"]["color"] == tag_color

        # test get tags
        list_tags = hf_api.get_tags(namespace=TEST_NAMESPACE,playbook=playbook_id)

        assert list_tags[0]["id"] == tag_id
        assert list_tags[0]["name"] == tag_name
        assert list_tags[0]["color"] == tag_color

        # test delete tags
        del_tag = hf_api.delete_tag(namespace=TEST_NAMESPACE,
                                    playbook=playbook_id,
                                    tag_id=tag_id)

        assert del_tag == dict()

        list_tags = hf_api.get_tags(namespace=TEST_NAMESPACE,playbook=playbook_id)

        assert list_tags == dict()

        _del_playbook(hf_api=hf_api,
                    namespace=TEST_NAMESPACE,
                    playbook_id=playbook_id)

    except RuntimeError as e:
        logger.error(e)
        _del_playbook(hf_api=hf_api,
                    namespace=TEST_NAMESPACE,
                    playbook_id=playbook_id)
        raise



def test_get_fully_qualified_intent_name():
    """
    test_get_fully_qualified_intent_name

    Before running this test, set HF_USERNAME and HF_PASSWORD as environment variables to access TEST_NAMESPACE
    
    And also update TEST_NAMESPACE before running this test
    """
    #TODO: Modify this to latest test standards of calling apis with try/except to avoid creating multiple copies

    hf_api = humanfirst.apis.HFAPI()


    create_pb_res = hf_api.create_playbook(namespace=TEST_NAMESPACE,
                                           playbook_name="fully_qualified_intent_name function test")

    playbook_id = create_pb_res["etcdId"]

    assert _playbook_is_present(hf_api=hf_api,
                        namespace=TEST_NAMESPACE,
                        playbook_id=playbook_id) is True

    path_to_file = os.path.join(here,'..','examples','json_model_example_output.json')

    with open(path_to_file, mode="r", encoding="utf8") as file_obj:
        workspace_dict = json.load(file_obj)

    _ = hf_api.import_intents(namespace=TEST_NAMESPACE, playbook=playbook_id, workspace_as_dict=workspace_dict)

    # get the playbook and form a HF workspace object
    full_pb = hf_api.get_playbook(namespace=TEST_NAMESPACE, playbook=playbook_id)
    hf_workspace = humanfirst.objects.HFWorkspace.from_json(full_pb, delimiter=DEFAULT_DELIMITER)

    actual_intent_names = [
        "GROUP1",
        "GROUP2",
        f"GROUP1{DEFAULT_DELIMITER}GROUP1_EN_INJURED_AT_THE_ZOO",
        f"GROUP2{DEFAULT_DELIMITER}GROUP2_DREADFULLY_INJURED"
    ]

    assert len(hf_workspace.intents_by_id) == len(actual_intent_names)

    # check if the funtion properly generates fully qualified intent names for all intents
    for intent_id in hf_workspace.intents_by_id:
        intent_name = hf_workspace.get_fully_qualified_intent_name(intent_id=intent_id)
        assert intent_name in actual_intent_names

    # delete the workspace and check if the workspace is deleted
    hf_api.delete_playbook(namespace=TEST_NAMESPACE, playbook_id=playbook_id, hard_delete=True)

    assert _playbook_is_present(hf_api=hf_api,
                                namespace=TEST_NAMESPACE,
                                playbook_id=playbook_id) is False

def test_create_intent_second_time():
    """test_create_intent_second_time"""

    labelled = humanfirst.objects.HFWorkspace()
    intent = labelled.intent(
        name_or_hier=['billing', 'billing_issues', 'payment_late'])
    assert isinstance(intent, humanfirst.objects.HFIntent)
    assert intent.name == 'payment_late'
    assert intent.id == 'intent-2'
    assert intent.parent_intent_id == 'intent-1'
    assert len(labelled.intents) == 3
    intent = labelled.intent(name_or_hier=['billing'])
    assert isinstance(intent, humanfirst.objects.HFIntent)
    assert intent.name == 'billing'
    assert intent.id == 'intent-0'
    assert intent.parent_intent_id is None
    assert len(labelled.intents) == 3


def test_metadata_intent():
    """test_metadata_intent"""

    labelled = humanfirst.objects.HFWorkspace()
    metadata = {
        'somekey': 'somevalue',
        'anotherkey': 'anothervalue'
    }
    intent = labelled.intent(
        name_or_hier=['billing', 'billing_issues', 'payment_late'], metadata=metadata)
    assert isinstance(intent, humanfirst.objects.HFIntent)
    assert intent.metadata['anotherkey'] == 'anothervalue'
    assert len(labelled.intents) == 3
    # this is the possibly undesirable bit
    assert (
        labelled.intents['billing'].metadata['anotherkey'] == 'anothervalue')
    assert (
        labelled.intents['billing-billing_issues'].metadata['anotherkey'] == 'anothervalue')
    assert (
        labelled.intents['billing-billing_issues-payment_late'].metadata['anotherkey'] == 'anothervalue')


def test_tag_color_create():
    """test_tag_color_create"""

    labelled = humanfirst.objects.HFWorkspace()
    tag = labelled.tag(tag='exclude', is_tag_ref=False)
    assert isinstance(tag, humanfirst.objects.HFTag)
    assert tag.color.startswith('#')
    assert len(tag.color) == 7
    old_color = tag.color
    new_color = '#ffffff'
    # if try to recreate, already exists tag doesn't change
    tag = labelled.tag(tag='exclude', color=new_color, is_tag_ref=False)
    assert tag.color == old_color
    # creating new works
    tag = labelled.tag(tag='exclude-white', color=new_color, is_tag_ref=False)
    assert tag.color == new_color


def test_tag_reference():
    """test_tag_reference"""

    labelled = humanfirst.objects.HFWorkspace()
    tag = labelled.tag(tag='exclude')
    assert isinstance(tag, humanfirst.objects.HFTagReference)
    # check if color is not present in the HFTagReference
    assert "color" not in list(tag.__dict__.keys())


def test_write_csv():
    """test_write_csv"""

    # delete output file so can sure we are testing fresh each time
    path_to_file = os.path.join(here,'..','examples','write_csv_example.csv')
    if os.path.exists(path_to_file):
        os.remove(path_to_file)
    workspace = path_to_file.replace(".csv",".json")

    with open(workspace, mode="r", encoding="utf8") as file_obj:
        data = json.load(file_obj)
    labelled_workspace = humanfirst.objects.HFWorkspace.from_json(data,delimiter=None)
    assert isinstance(labelled_workspace, humanfirst.objects.HFWorkspace)
    output_file = "./examples/write_csv_example.csv"
    labelled_workspace.write_csv(output_file)
    df = pandas.read_csv(output_file, encoding="utf8")

    # Check column names
    columns_should_be = []
    # utterance and full name
    columns_should_be.extend(["utterance", "fully_qualified_intent_name"])
    # four different intent keys
    columns_should_be.extend(["intent_metadata-intent_metadata1", "intent_metadata-intent_metadata2",
                             "intent_metadata-intent_metadata3", "intent_metadata-intent_metadata4"])
    # two different metadata keys
    columns_should_be.extend(
        ["example_metadata-example_metadata1", "example_metadata-example_metadata2"])
    columns_should_be.sort()

    columns = list(df.columns)
    columns.sort()

    assert columns == columns_should_be

    # Check intent level values
    assert list(df["intent_metadata-intent_metadata1"].unique()
            == ['value1', numpy.nan, 'value5'])
    assert df[df["intent_metadata-intent_metadata1"] == 'value1'].shape[0] == 5
    assert df[df["intent_metadata-intent_metadata1"] == 'value5'].shape[0] == 1
    assert df[df["intent_metadata-intent_metadata1"].isna()].shape[0] == 5

    assert list(df["intent_metadata-intent_metadata2"].unique()
            == ['value2', numpy.nan, 'value6'])
    assert df[df["intent_metadata-intent_metadata2"] == 'value2'].shape[0] == 5
    assert df[df["intent_metadata-intent_metadata2"] == 'value6'].shape[0] == 1
    assert df[df["intent_metadata-intent_metadata2"].isna()].shape[0] == 5

    # Check example level values
    assert list(df["example_metadata-example_metadata1"].unique()
            == [numpy.nan, 'valueA'])
    assert (df[df["example_metadata-example_metadata1"]
            == 'valueA'].shape[0] == 1)
    assert df[df["example_metadata-example_metadata1"].isna()].shape[0] == 10


def test_read_json():
    """test_read_json"""

    input_file = "./examples/json_model_example_output.json"
    workspace = humanfirst.objects.HFWorkspace()
    json_input = json.loads(open(input_file, 'r', encoding='utf8').read())
    workspace = workspace.from_json(json_input,delimiter=None)
    intent_index = workspace.get_intent_index("-")
    assert list(intent_index.values()) == [
            "GROUP1", "GROUP1-GROUP1_EN_INJURED_AT_THE_ZOO", "GROUP2", "GROUP2-GROUP2_DREADFULLY_INJURED"]

def test_write_json():
    """test_write_json"""

    input_file = "./examples/json_model_example_output.json"
    workspace = humanfirst.objects.HFWorkspace()
    json_input_1 = json.loads(open(input_file, 'r', encoding='utf8').read())
    workspace = workspace.from_json(json_input_1,delimiter=None)

    output_file = input_file.replace(".json","_123.json")
    file_out = open(output_file, 'w', encoding='utf8')
    workspace.write_json(file_out)
    file_out.close()

    json_input_2 = json.loads(open(output_file, 'r', encoding='utf8').read())

    df_example_1 = pandas.json_normalize(data=json_input_1["examples"], sep="-")
    df_example_2 = pandas.json_normalize(data=json_input_2["examples"], sep="-")
    df_intent_1 = pandas.json_normalize(data=json_input_1["intents"], sep="-")
    df_intent_2 = pandas.json_normalize(data=json_input_2["intents"], sep="-")
    df_tag_1 = pandas.json_normalize(data=json_input_1["tags"], sep="-")
    df_tag_2 = pandas.json_normalize(data=json_input_2["tags"], sep="-")

    assert df_example_1.equals(df_example_2)
    assert df_intent_1.equals(df_intent_2)
    assert df_tag_1.equals(df_tag_2)

    # Check if file exists
    if os.path.exists(output_file):
        # Delete the file
        os.remove(output_file)


def test_tag_filter_validation():
    """test_tag_filter_validation"""

    tag_filters = humanfirst.objects.HFTagFilters()
    assert (tag_filters.validate_tag_list_format(
        ["test-regression", "test-analyst"]) == ["test-regression", "test-analyst"])
    assert (tag_filters.validate_tag_list_format(
        "test-regression,test-analyst") == ["test-regression", "test-analyst"])


def test_tag_filters():
    """test_tag_filters"""

    tag_filters = humanfirst.objects.HFTagFilters()
    assert isinstance(tag_filters.intent, humanfirst.objects.HFTagFilter)
    assert isinstance(tag_filters.utterance, humanfirst.objects.HFTagFilter)

    # check we can set the list of values
    tag_filters.set_tag_filter("intent", "exclude", [
                               "test-regression", "test-analyst"])
    assert isinstance(tag_filters.intent.exclude, list)
    assert tag_filters.intent.exclude[0] == "test-regression"
    assert tag_filters.intent.exclude[1] == "test-analyst"
    assert len(tag_filters.intent.exclude) == 2

    # Check we can access like a list
    tag_filters.intent.exclude.pop(0)
    assert len(tag_filters.intent.exclude) == 1
    assert tag_filters.intent.exclude[0] == "test-analyst"

    # Check if we set the other tag_type we don't lose the other already set data
    tag_filters.set_tag_filter("intent", "include", [
                               "release-1.0.1", "release-1.0.2", "release-1.0.3"])
    assert tag_filters.intent.exclude[0] == "test-analyst"
    assert tag_filters.intent.include[1] == "release-1.0.2"

    # check validates on tag level
    with pytest.raises(humanfirst.objects.InvalidFilterLevel) as e:
        tag_filters.set_tag_filter("workspace", "exclude", [
                                   "test-regression", "test-analyst"])
        assert str(
            e.value) == "Accepted levels are ['intent', 'utterance'] level was: workspace"

    # check validates on tag type
    with pytest.raises(humanfirst.objects.InvalidFilterType) as e:
        tag_filters.set_tag_filter(
            "intent", "both", ["test-regression", "test-analyst"])
        assert str(
            e.value) == "Accepted types are ['incldue', 'exclude'] level was: both"

def test_conversation_set_functionalities():
    """Test Upload,link,unlink,delete a conversation set"""

    hf_api = humanfirst.apis.HFAPI()

    try:
        # test create conversation set
        conversation_obj = hf_api.create_conversation_set_with_set_and_src_id(namespace=TEST_NAMESPACE,
                                                                                convoset_name=TEST_CONVOSET)

        assert isinstance(conversation_obj, dict)
        assert "convoset_id" in conversation_obj
        assert "convosrc_id" in conversation_obj
        assert isinstance(conversation_obj["convoset_id"], str)
        assert isinstance(conversation_obj["convosrc_id"], str)
        assert "convset-" in conversation_obj["convoset_id"]
        assert "convsrc-" in conversation_obj["convosrc_id"]
        logger.info(f'Created convoset_id: {conversation_obj["convoset_id"]}')

        # test upload a file to the conversation set
        upload_response = hf_api.upload_json_file_to_conversation_source(namespace=TEST_NAMESPACE,
                                                                conversation_source_id=conversation_obj["convosrc_id"],
                                                                upload_name="abcd_108_test",
                                                                fqfp="./examples/abcd_2022_05_convo_108.json"
                                                                )
        logger.info(f'Uploaded JSON: {upload_response}')

        assert isinstance(upload_response,dict)
        assert upload_response["filename"] == "abcd_108_test"
        assert len(set(upload_response.keys()).intersection({"triggerId","conversationSourceId"})) == 2
        logger.debug(upload_response)

        # Check a file exists in the test account created convoset
        # from the config file

        list_files = hf_api.list_conversation_src_files(namespace=TEST_NAMESPACE,
                                                        conversation_set_src_id=conversation_obj["convosrc_id"])
        assert isinstance(list_files,list)
        assert len(list_files) == 1
        assert list_files[0]["name"] == "abcd_108_test"
        assert list_files[0]["format"] == "IMPORT_FORMAT_HUMANFIRST_JSON"
        assert isinstance(list_files[0]["fromLastUpload"],bool)
        upload_time = list_files[0]["uploadTime"]
        upload_datetime = parser.parse(upload_time)
        assert isinstance(upload_datetime,datetime)
        
        logger.info(f'Listed files: {list_files}')

        # test linking the conversation set to a workspace
        try:
            # create a playbook
            playbook_id = _create_playbook(hf_api,
                                    namespace=TEST_NAMESPACE,
                                    playbook_name="test link-unlink dataset")

            assert "playbook-" in playbook_id
            logger.info(f'Created playbook: {playbook_id}')

            try:
                link_res = hf_api.link_conversation_set(namespace=TEST_NAMESPACE, playbook_id=playbook_id,
                                                        convoset_id=conversation_obj["convoset_id"])
                assert "triggerId" in link_res
                assert isinstance(link_res["triggerId"],str)
                assert "trig-" in link_res["triggerId"]

                # check if the link trigger is completed
                total_wait_time = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,
                                                            trigger_id=link_res["triggerId"])
                if total_wait_time == -1:
                    raise RuntimeError('Link pipeline failed or was cancelled')
                elif total_wait_time == 0:
                    raise RuntimeError('Link pipeline timed out')
                else:
                    logger.info(f'Link convoset completed in: {total_wait_time}')

                # return empty json when there is no changes made in the tool
                # trying to link the same dataset to the same workspace as above
                link_res = hf_api.link_conversation_set(namespace=TEST_NAMESPACE,
                                                        playbook_id=playbook_id,
                                                        convoset_id=conversation_obj["convoset_id"])
                assert link_res == {}
                
                # Check that we can download the full conversations
                # build the metadata_predicate
                metadata_predicate = []
                metadata_predicate.append(
                    {
                        "key": "abcd_id", # lookup by abcd
                        "operator": "EQUALS",
                        "value": "108", # get conversation 108
                        "optional": False
                    }
                )

                # download both sides of the conversation - using 3 to skip source
                test_convos = hf_api.export_query_conversation_inputs(namespace=TEST_NAMESPACE,
                                                                      playbook_id=playbook_id,
                                                                      metadata_predicate=metadata_predicate,
                                                                      source_kind=1,# unlabelled
                                                                      source=-1, # skip source
                )
                assert("examples" in test_convos.keys())
                assert len(test_convos["examples"]) == 14 # 14 utterances in test set
                # check the ordering is maintained
                assert test_convos["examples"][0]["metadata"]["conversation_turn"] == "000"
                assert test_convos["examples"][13]["metadata"]["conversation_turn"] == "013"


                # upon trying to delete the conversation set when it is linked to workspaces, it throws error
                delete_res_exception = ""
                try:
                    _ = hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                                        convoset_id=conversation_obj["convoset_id"])
                except HFAPIResponseValidationException as e:
                    delete_res_exception = e.message

                assert "conversation set is still being referenced" in delete_res_exception

                # test unlinking the conversation set from a workspace
                unlink_res = hf_api.unlink_conversation_set(namespace=TEST_NAMESPACE,
                                                            playbook_id=playbook_id,
                                                            convoset_id=conversation_obj["convoset_id"])
                assert "triggerId" in unlink_res
                assert isinstance(unlink_res["triggerId"],str)
                assert "trig-" in unlink_res["triggerId"]

                # check if the link trigger is completed
                total_wait_time = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,
                                                            trigger_id=unlink_res["triggerId"])
                if total_wait_time == -1:
                    raise RuntimeError('Link pipeline failed or was cancelled')
                elif total_wait_time == 0:
                    raise RuntimeError('Link pipeline timed out')
                else:
                    logger.info(f'Link convoset completed in: {total_wait_time}')

                # return empty json when there is no changes made in the tool
                # trying to unlink the same dataset from the same workspace as above
                unlink_res = hf_api.unlink_conversation_set(namespace=TEST_NAMESPACE,
                                                            playbook_id=playbook_id,
                                                            convoset_id=conversation_obj["convoset_id"])
                assert unlink_res == {}

                # Test deleting a file from a convoset
                delete_res = hf_api.delete_conversation_file(namespace=TEST_NAMESPACE,
                                                            conversation_set_src_id=conversation_obj["convosrc_id"],
                                                            file_name="abcd_108_test"
                                                            )

                assert "triggerId" in delete_res
                assert isinstance(delete_res["triggerId"],str)
                assert "trig-" in delete_res["triggerId"]

                # check if delete trigger completes
                total_wait_time = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,
                                                            trigger_id=delete_res["triggerId"])
                if total_wait_time == -1:
                    raise RuntimeError('Delete pipeline failed or was cancelled')
                elif total_wait_time == 0:
                    raise RuntimeError('Delete pipeline timed out')
                else:
                    logger.info(f'Delete convoset completed in: {total_wait_time}')
                
                # Test deleting a file from a convoset with exception
                output_exception = ""
                try:
                    hf_api.delete_conversation_file(namespace=TEST_NAMESPACE,
                                                    conversation_set_src_id=conversation_obj["convosrc_id"],
                                                    file_name="abcd_108_test"
                                                    )
                except humanfirst.apis.HFAPIResponseValidationException as e:
                    output_exception = str(e.message)

                assert '"message":"file doesn\'t exists"' in output_exception

                # delete conversation set
                delete_response = hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                                                convoset_id=conversation_obj["convoset_id"])
                assert delete_response == {}

                # delete the workspace and check if the workspace is deleted
                delete_playbook_res = hf_api.delete_playbook(namespace=TEST_NAMESPACE,
                                                            playbook_id=playbook_id,
                                                            hard_delete=True)
                assert delete_playbook_res == {}

                assert _playbook_is_present(hf_api=hf_api,
                                            namespace=TEST_NAMESPACE,
                                            playbook_id=playbook_id) is False

            except RuntimeError as e:
                logger.error(e)
                hf_api.unlink_conversation_set(namespace=TEST_NAMESPACE,
                                            playbook_id=playbook_id,
                                            convoset_id=conversation_obj["convoset_id"])
                raise

        except RuntimeError as e:
            logger.error(e)
            _del_playbook(hf_api=hf_api,
                    namespace=TEST_NAMESPACE,
                    playbook_id=playbook_id)
            raise

    except RuntimeError as e:
        logger.error(e)
        hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                        convoset_id=conversation_obj["convoset_id"])
        raise

def test_batch_predict():
    """Test upload a dataset then predicting batch predicts with different timeouts"""

    # open API
    hf_api = humanfirst.apis.HFAPI()

    # Create the playbook and get the ID
    playbook = hf_api.create_playbook(namespace=TEST_NAMESPACE,playbook_name="test_batch_predict")
    playbook_id = playbook["metastorePlaybook"]["id"]
    nlu_id = playbook["metastorePlaybook"]["nlu"]["id"]
    logger.info(f'nlu_id: {nlu_id}')

    # Read a JSON file of humanfirst training
    file_in = open('examples/Academy-Ex03-Disambiguation-2024-09-15.json',mode='r',encoding='utf8')
    workspace_dict = json.load(file_in)
    file_in.close()

    # Send it to that workspace
    import_intents_response = hf_api.import_intents(namespace=TEST_NAMESPACE,
                          playbook=playbook_id,
                          workspace_as_dict=workspace_dict)
    logger.debug(import_intents_response)
    
    # this is going to start an import job but we aren't quite sure when it finsihes and we don't have an import trigger to check
    # so wait a moment before triggering NLU this improves reliability of the test.
    time.sleep(1)
    
    # train the NLU on that workspace
    train_nlu_trigger = hf_api.trigger_train_nlu(namespace=TEST_NAMESPACE,
                                                playbook=playbook_id,
                                                nlu_id=nlu_id)

    logger.debug(train_nlu_trigger)

    # Use describetrigger to know the status of NLU training
    total_wait_time = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE, trigger_id=train_nlu_trigger["triggerId"])
    
    if total_wait_time == 0:
        raise RuntimeError(f'Timed out waiting for NLU to finish training')
    elif total_wait_time == -1:
        raise RuntimeError(f'NLU Training cancelled')
    else:
        logger.info(f"Total wait for NLU to train is: {total_wait_time}")
    
    # Also then poll check for being trained (should already be when trigger completes above)
    sleep_counter = 0 # doing linear rather than expo backoff in this test
    total_wait_time = 0
    list_trained_nlu = []
    while len(list_trained_nlu) == 0:
        sleep_counter = sleep_counter + 1
        time.sleep(sleep_counter)
        total_wait_time = total_wait_time + sleep_counter
        list_trained_nlu = hf_api.list_trained_nlu(namespace=TEST_NAMESPACE,
                                  playbook=playbook_id)
        logger.info(f"List trained NLU: {list_trained_nlu}")
        if sleep_counter > 60:
            raise RuntimeError("Counted get trained NLU")

    # when we have one check it
    status = ""
    sleep_counter = 0
    while status != "RUN_STATUS_AVAILABLE":
        list_trained_nlu = hf_api.list_trained_nlu(namespace=TEST_NAMESPACE,playbook=playbook_id)
        for nlu in list_trained_nlu:
            if nlu["params"]["engines"][0]["nluId"] == nlu_id:
                status = nlu["status"]
                total_wait_time = total_wait_time + sleep_counter
                sleep_counter = sleep_counter + 1
                logger.debug(f'{status} - wait time: {sleep_counter} - total time waited to date: {total_wait_time}')
                time.sleep(sleep_counter)
        if sleep_counter > 60:
            raise RuntimeError("Couldn't get nlu to showcorrect status")

    sentences = [
        "Hello this is a really long way to say hello hello",
        "Goodbye, and goodbye and goodbye and goodbye",
        "Where is the paisley bus somewhere up the highroad on it's way to vindaloo?"
    ]

    # First call - no timeout param
    predictions = hf_api.batchPredict(sentences=sentences,
                        namespace=TEST_NAMESPACE,
                        playbook=playbook_id)

    assert len(predictions) == 3
    assert predictions[0]["matches"][0]["name"] == "greeting"

    # make the predictions really big and then set timeout to one so almost certainly failes
    big_sentences = []
    for n in range(0,100):
        big_sentences.extend(sentences)
    assert len(big_sentences) == 300

    # Second call timeout set to 1 so almost certainly fails batch predict
    timeout_exception = ""
    try:
        predictions = hf_api.batchPredict(sentences=big_sentences,
                            namespace=TEST_NAMESPACE,
                            playbook=playbook_id,
                            timeout=0.1)
    except Exception as e: # pylint: disable=broad-exception-caught
        timeout_exception = e
    assert timeout_exception != ""
    # TODO: better exception check

    # third with a big timeout where it should work
    predictions = hf_api.batchPredict(sentences=big_sentences,
                    namespace=TEST_NAMESPACE,
                    playbook=playbook_id,
                    timeout=30)

    assert len(predictions) == 300

    # clean up and delete the workspace
    delete_response = hf_api.delete_playbook(namespace=TEST_NAMESPACE,
                           playbook_id=playbook_id,
                           hard_delete=True)

    assert delete_response == {}


def test_no_trigger():
    """Create convoset
    Upload a file with no_trigger - check no trigger
    upload a second file with trigger - check triggers run"""

    hf_api = humanfirst.apis.HFAPI()

    # test create conversation set
    conversation_obj = hf_api.create_conversation_set_with_set_and_src_id(namespace=TEST_NAMESPACE,
                                                                            convoset_name=TEST_CONVOSET)
    
    
    # link a workspace
    playbook_id = _create_playbook(hf_api,
                            namespace=TEST_NAMESPACE,
                            playbook_name="test link-unlink dataset")
    link_response = hf_api.link_conversation_set(namespace=TEST_NAMESPACE, playbook_id=playbook_id,
                                                convoset_id=conversation_obj["convoset_id"])
    logger.debug(link_response)
    assert "triggerId" in link_response.keys()
    wait_time_till_done = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,trigger_id=link_response["triggerId"])
    
    
    # test upload a file to the conversation set with no trigger
    upload_response = hf_api.upload_json_file_to_conversation_source(namespace=TEST_NAMESPACE,
                                                            conversation_source_id=conversation_obj["convosrc_id"],
                                                            upload_name="abcd_108_test",
                                                            fqfp="./examples/abcd_2022_05_convo_108.json",
                                                            no_trigger=True
                                                            )
    logger.debug(upload_response)    
    assert not "triggerId" in upload_response.keys()
    
    # test a second file with trigger
    upload_response = hf_api.upload_json_file_to_conversation_source(namespace=TEST_NAMESPACE,
                                                            conversation_source_id=conversation_obj["convosrc_id"],
                                                            upload_name="abcd_109_test",
                                                            fqfp="./examples/abcd_2022_05_convo_109.json",
                                                            no_trigger=False)

    logger.debug(upload_response)
    assert "triggerId" in upload_response.keys()

    # Check that trigger
    wait_time_till_done = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,trigger_id=upload_response["triggerId"])
    assert wait_time_till_done > 0

    # delete a file the same way starting with the most recent
    delete_response = hf_api.delete_conversation_file(namespace=TEST_NAMESPACE,
                                                      conversation_set_src_id=conversation_obj["convosrc_id"],
                                                      file_name="abcd_109_test",
                                                      no_trigger=True)
    logger.debug(delete_response)
    assert not "triggerId" in delete_response.keys()

    # Now delete and check the trigger
    delete_response = hf_api.delete_conversation_file(namespace=TEST_NAMESPACE,
                                                      conversation_set_src_id=conversation_obj["convosrc_id"],
                                                      file_name="abcd_108_test",
                                                      no_trigger=False)
    logger.debug(delete_response)

    # Check that trigger
    wait_time_till_done = hf_api.loop_trigger_check(namespace=TEST_NAMESPACE,trigger_id=delete_response["triggerId"])
    assert wait_time_till_done > 0

    # delete the workspace
    _del_playbook(hf_api=hf_api,namespace=TEST_NAMESPACE,playbook_id=playbook_id)

    # delete conversation set
    delete_convo_response = hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,
                                                        convoset_id=conversation_obj["convoset_id"])
    logger.info(delete_convo_response)
    
def test_cleanup_convosets_and_workspaces():
    """testing delete test convosets if exist"""

    hf_api = humanfirst.apis.HFAPI()

    # get all workspaces/playbooks
    logger.info('Getting playbook list')
    list_playbooks = hf_api.list_playbooks(namespace=TEST_NAMESPACE,timeout=120)
    logger.info(f'Number of playbooks returned: {len(list_playbooks)}')

    # find any that match and delete them
    for p in list_playbooks:
        if "name" in p.keys():
            if p["name"] in ["test link-unlink dataset","test list playbooks 1","test list playbooks 2"]:
                playbook_delete_respone = hf_api.delete_playbook(namespace=TEST_NAMESPACE,playbook_id=p['id'])
                logger.debug(playbook_delete_respone)
                logger.info(f'Hard deleted playbook: {p["id"]}')

    # get all convosets
    logger.info(f'Getting all convosets')
    convoset_list = hf_api.get_conversation_set_list(namespace=TEST_NAMESPACE,timeout=120)
    logger.info(f'Received convosets: {len(convoset_list)}')

    # Loop through deleting any that exist - assumption is all test workspaces have been deleted
    # i.e no check to unlink, if something is still attached here there is a logical error earlier in the test
    for c in convoset_list:
        if c["name"] == TEST_CONVOSET:
            convoset_delete_response = hf_api.delete_conversation_set(namespace=TEST_NAMESPACE,convoset_id=c["id"])
            logger.debug(convoset_delete_response)
            logger.info(f'Deleted convoset: {c["id"]}')
            
def test_get_conversation_set_list_simple():
    hf_api = humanfirst.apis.HFAPI()
    convosets = hf_api.get_conversation_set_list(namespace=TEST_NAMESPACE)
    # if running with aio image which starts completely empty this will have 0 convosets
    if len(convosets) > 0:
        df_simple = pandas.json_normalize(convosets)
        assert isinstance(df_simple,pandas.DataFrame)

def test_refresh_minimnum_expiry():
    hf_api = humanfirst.apis.HFAPI(min_expires_in_seconds=3597) # i.e only 3 seconds old with window of 1 hour
    
    # list the playbooks - get the first token
    playbooks = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
    
    # sleep 0 - should have same token
    playbooks = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
    
    # sleep 3 more - should get new token
    time.sleep(3)
    playbooks = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
    


# This test is for a legacy piece of functionality and very slow so commenting for speed.
# TODO: decommission this function
# def test_get_conversation_set_list_deep_report():
#     hf_api = humanfirst.apis.HFAPI()
#     df_full_report = pandas.json_normalize(hf_api.get_conversation_set_deep_report(namespace=TEST_NAMESPACE))
#     print(df_full_report)
#     print(df_full_report.loc[0,:])
#     print(df_full_report.columns)