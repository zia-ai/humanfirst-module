"""

Set of pytest humanfirst.objects.py tests

"""
# ***************************************************************************80**************************************120

# standard imports
import time
import os
import json
from configparser import ConfigParser
from datetime import datetime
from dateutil import parser
import uuid

# third party imports
import numpy
import pandas
import pytest
import humanfirst

# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

# CONSTANTS
constants = ConfigParser()
path_to_config_file = os.path.join(here,'..','humanfirst','config','setup.cfg')
constants.read(path_to_config_file)

# constants need type conversion from str to int - TODO: setAttr loop for neatness or function
TEST_NAMESPACE = constants.get("humanfirst.CONSTANTS","TEST_NAMESPACE")
DEFAULT_DELIMITER = constants.get("humanfirst.CONSTANTS","DEFAULT_DELIMITER")
TEST_CONVOSET = constants.get("humanfirst.CONSTANTS","TEST_CONVOSET")
TEST_CONVOSET_SET_SRC = constants.get("humanfirst.CONSTANTS","TEST_CONVOSET_SET_SRC")

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

def test_get_fully_qualified_intent_name():
    """
    test_get_fully_qualified_intent_name

    Before running this test, set HF_USERNAME and HF_PASSWORD as environment variables to access TEST_NAMESPACE
    
    And also update TEST_NAMESPACE before running this test
    """

    hf_api = humanfirst.apis.HFAPI()

    create_pb_res = hf_api.create_playbook(namespace=TEST_NAMESPACE,
                                           playbook_name="fully_qualified_intent_name function test")

    playbook_id = create_pb_res["etcdId"]

    # check if the playbook is available in the workspace
    list_pb = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
    valid_playbook_id = False
    for i,_ in enumerate(list_pb):
        if playbook_id == list_pb[i]["etcdId"]:
            valid_playbook_id = True
    assert valid_playbook_id is True

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

    # check if the provided playbook is removed from the workspace
    list_pb = hf_api.list_playbooks(namespace=TEST_NAMESPACE)
    valid_playbook_id = False
    for i,_ in enumerate(list_pb):
        if playbook_id == list_pb[i]["etcdId"]:
            valid_playbook_id = True
    assert valid_playbook_id is False

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

def test_conversation_set_file_upload():
    """Upload a conversation set to the test conversation set"""

    hf_api = humanfirst.apis.HFAPI()
    upload_response = hf_api.upload_json_file_to_conversation_source(namespace=TEST_NAMESPACE,
                                                                    conversation_source_id=TEST_CONVOSET_SET_SRC,
                                                                    upload_name="abcd_108_test",
                                                                    fqfp="./examples/abcd_2022_05_convo_108.json"
                                                                    )

    assert isinstance(upload_response,dict)
    assert upload_response["filename"] == "abcd_108_test"
    assert len(set(upload_response.keys()).intersection({"triggerId","conversationSourceId"})) == 2
    print(upload_response)

def test_conversation_set_list():
    """Check a file exists in the test account created convoset
    from the config file"""

    hf_api = humanfirst.apis.HFAPI()

    list_files = hf_api.list_conversation_src_files(namespace=TEST_NAMESPACE,
                                                    conversation_set_src_id=TEST_CONVOSET_SET_SRC)

    assert isinstance(list_files,list)
    assert len(list_files) == 1
    assert list_files[0]["name"] == "abcd_108_test"
    assert list_files[0]["format"] == "IMPORT_FORMAT_HUMANFIRST_JSON"
    assert isinstance(list_files[0]["fromLastUpload"],bool)
    upload_time = list_files[0]["uploadTime"]
    upload_datetime = parser.parse(upload_time)
    assert isinstance(upload_datetime,datetime)

def test_delete_conversation_file():
    """Test deleting a file from a convoset"""

    hf_api = humanfirst.apis.HFAPI()

    deleted_file_return = hf_api.delete_conversation_file(namespace=TEST_NAMESPACE,
                                                 conversation_set_src_id=TEST_CONVOSET_SET_SRC,
                                                 file_name="abcd_108_test"
                                                 )

def test_delete_not_exists_conversation_file():
    """Test deleting a file from a convoset"""

    hf_api = humanfirst.apis.HFAPI()

    output_exception = ""
    try:
        hf_api.delete_conversation_file(namespace=TEST_NAMESPACE,
                                        conversation_set_src_id=TEST_CONVOSET_SET_SRC,
                                        file_name="abcd_108_test"
                                        )
    except humanfirst.apis.HFAPIResponseValidationException as e:
        output_exception = str(e.message)

    assert '"message":"file doesn\'t exists"' in output_exception

def test_batch_predict():
    """Test upload a dataset then predicting batch predicts with different timeouts"""

    # open API
    hf_api = humanfirst.apis.HFAPI()

    # Create the playbook and get the ID
    playbook = hf_api.create_playbook(namespace=TEST_NAMESPACE,playbook_name="test_batch_predict")
    playbook_id = playbook["metastorePlaybook"]["id"]
    nlu_id = playbook["metastorePlaybook"]["nlu"]["id"]
    print(nlu_id)

    # Read a JSON file of humanfirst training
    file_in = open('examples/Academy-Ex03-Disambiguation-2024-09-15.json',mode='r',encoding='utf8')
    workspace_dict = json.load(file_in)
    file_in.close()

    # Send it to that workspace
    hf_api.import_intents(namespace=TEST_NAMESPACE,
                          playbook=playbook_id,
                          workspace_as_dict=workspace_dict)

    # train the NLU on that workspace
    hf_api.trigger_train_nlu(namespace=TEST_NAMESPACE,
                             playbook=playbook_id,
                             nlu_id=nlu_id)

    # Poll for it being trained
    sleep_counter = 0 # doin linear rather than expo backoff in this test
    total_wait_time = 0
    list_trained_nlu = []
    while len(list_trained_nlu) == 0:
        sleep_counter = sleep_counter + 1
        time.sleep(sleep_counter)
        total_wait_time = total_wait_time + sleep_counter
        list_trained_nlu = hf_api.list_trained_nlu(namespace=TEST_NAMESPACE,
                                  playbook=playbook_id)
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
                print(f'{status} - wait time: {sleep_counter} - total time waited to date: {total_wait_time}')
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
                            timeout=1)
    except Exception as e:
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