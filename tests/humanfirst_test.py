"""

Set of pytest humanfirst.objects.py tests

"""
# ***************************************************************************80**************************************120

# standard imports
import os
import json

# third party imports
import numpy
import pandas
import pytest
import humanfirst

# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

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
        labelled.intents['billing_issues'].metadata['anotherkey'] == 'anothervalue')
    assert (
        labelled.intents['payment_late'].metadata['anotherkey'] == 'anothervalue')


def test_tag_color_create():
    """test_tag_color_create"""

    labelled = humanfirst.objects.HFWorkspace()
    tag = labelled.tag(tag='exclude')
    assert isinstance(tag, humanfirst.objects.HFTag)
    assert tag.color.startswith('#')
    assert len(tag.color) == 7
    old_color = tag.color
    new_color = '#ffffff'
    # if try to recreate, already exists tag doesn't change
    tag = labelled.tag(tag='exclude', color=new_color)
    assert tag.color == old_color
    # creating new works
    tag = labelled.tag(tag='exclude-white', color=new_color)
    assert tag.color == new_color


def test_write_csv():
    """test_write_csv"""

    # delete output file so can sure we are testing fresh each time
    path_to_file = os.path.join(here,'..','examples','write_csv_example.csv')
    if os.path.exists(path_to_file):
        os.remove(path_to_file)
    workspace = path_to_file.replace(".csv",".json")

    with open(workspace, mode="r", encoding="utf8") as file_obj:
        data = json.load(file_obj)
    labelled_workspace = humanfirst.objects.HFWorkspace.from_json(data)
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
    workspace = workspace.from_json(json_input)
    intent_index = workspace.get_intent_index("-")
    assert list(intent_index.values()) == [
            "GROUP1", "GROUP1-GROUP1_EN_INJURED_AT_THE_ZOO", "GROUP2", "GROUP2-GROUP2_DREADFULLY_INJURED"]


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
