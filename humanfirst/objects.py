"""

humanfirst.py

a set of helper classes and methods for describing, validating and interacting with HFOBjects
that make up the HF JSON format

https://numpydoc.readthedocs.io/en/latest/format.html

"""
# ***************************************************************************80**************************************120

# standard imports
import datetime
import copy
import hashlib
import json
import random
from typing import IO, Any, Dict, List, Optional, Union
import logging
import logging.config
import os
import uuid

# third party imports
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import pandas

# locate where we are
here = os.path.abspath(os.path.dirname(__file__))
path_to_log_config_file = os.path.join(here,'config','logging.conf')

# Get the current date and time
current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Create the log file name with the current datetime
log_filename = f"log_{current_datetime}.log"

# Decide whether to save logs in a file or not
log_file_enable = os.environ.get("HF_LOG_FILE_ENABLE")

log_handler_list = []

if log_file_enable == "TRUE":
    log_handler_list.append('rotatingFileHandler')
elif log_file_enable == "FALSE" or log_file_enable is None:
    pass
else:
    raise RuntimeError("Incorrect HF_LOG_FILE_ENABLE value. Should be - 'TRUE', 'FALSE' or ''")

log_defaults = {}

# get log directory if going to save the logs
path_to_save_log = os.path.join(here,'logs',log_filename)
if log_file_enable == "TRUE":
    log_dir = os.environ.get("HF_LOG_DIR")
    if log_dir:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        path_to_save_log = os.path.join(log_dir,log_filename)
    else:
        raise RuntimeError("Require Log directory environment variable set up - HF_LOG_DIR")
else:
    # avoid logging to a file
    path_to_save_log = '/dev/null'  # On Linux/MacOS, this discards logs (Windows: NUL)
log_defaults['HF_LOG_FILE_PATH'] = path_to_save_log

# Decide whether to print the logs in the console or not
log_console_enable = os.environ.get("HF_LOG_CONSOLE_ENABLE")

if log_console_enable == "TRUE":
    log_handler_list.append('consoleHandler')
elif log_console_enable == "FALSE" or log_console_enable is None:
    pass
else:
    raise RuntimeError("Incorrect HF_LOG_CONSOLE_ENABLE value. Should be - 'TRUE', 'FALSE' or ''")

if log_handler_list:
    log_defaults['HF_LOG_HANDLER'] = ",".join(log_handler_list)
else:
    log_defaults['HF_LOG_HANDLER'] = "nullHandler"


# Set log levels
log_level = os.environ.get("HF_LOG_LEVEL")
if log_level is not None:
    # set log level
    if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        raise RuntimeError("Incorrect log level. Should be - 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'")

    log_defaults['HF_LOG_LEVEL'] = log_level
else:
    log_defaults['HF_LOG_LEVEL'] = 'INFO' # default level


# Load logging configuration
logging.config.fileConfig(
    path_to_log_config_file,
    defaults=log_defaults
)

# create logger
logger = logging.getLogger('humanfirst.objects')

HFMetadata = Dict[str, Any]

class HFIncompatibleOptionException(Exception):
    """When parameters passed are incompatible"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFMissingCredentialsException(Exception):
    """When can't locate assumed credentials"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFMapperException(Exception):
    """When a mapping can't be resolved"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFOutputFileMustBeDifferent(Exception):
    """When the output file name is the same as the input file name"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFInvlaidIntentTypeException(Exception):
    """This happens when intent is not of type HFIntentRef, HFIntent or str (intent_id) objects"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFInvalidWorkspaceInputTypeException(Exception):
    """This happens when HFWorkspace object is not from a dict of a json (from api) or from a json file"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFExxampleIDNotPresentException(Exception):
    """This happens when HF example does not have any ID to be included in the workspace"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFContextTypeException(Exception):
    """This happens when HF example does not have any ID to be included in the workspace"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFContextRoleException(Exception):
    """This happens when HF example does not have any ID to be included in the workspace"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

@dataclass_json
@dataclass
class HFTag:
    '''Schema object for HF Tags

    Validates the format of a tag

    Parameters
    ----------
    id:    str            unique id for tag
    name:  str            name of tag that will be displayed in HF studio
    color: str, optional  a hex code starting with # for a color to display the tag in eg #ff33da (a bright pink)
                          if a color isn't provided a random one will be assigned
    '''
    id: str
    name: str
    color: Optional[str] = None

    def __init__(self,
                 id: str, # pylint: disable=redefined-builtin
                 name: str,
                 color: Optional[str] = None):
        self.id = id # pylint: disable=redefined-builtin
        self.name = name
        if color and color != '':
            self.color = color
        else:
            self.color = generate_random_color()

@dataclass_json
@dataclass
class HFTagReference:
    '''Schema object for HF Tags to be used in HF intents and HF examples

    Validates the format of a tag used in intents and examples

    These tags are added to HFIntents and HFExamples

    Parameters
    ----------
    id:    str            unique id for tag
    name:  str            name of tag that will be displayed in HF studio
    '''
    id: str
    name: str

    def __init__(self,
                 id: str, # pylint: disable=redefined-builtin
                 name: str):
        self.id = id # pylint: disable=redefined-builtin
        self.name = name

@dataclass_json
@dataclass
class HFTagFilter:
    '''Schema object for HF Tag Filter

    Validates the format of a tag filter
    of types include|exclude

    Provide lists of tags to filter as comma delimited strings or lists

    Parameters
    ----------
    include: [],
    exclude: [],
    '''
    include: list
    exclude: list

    def __init__(self, include: list = None, exclude: list = None):

        if include is None:
            include = []

        if exclude is None:
            exclude = []

        self.include = include
        self.exclude = exclude

@dataclass_json
@dataclass
class HFTagFilters:
    """
    HumaFirst Tag filters

    Sets and validates intent and utterance level tags
    """
    intent: HFTagFilter
    utterance: HFTagFilter

    def __init__(self):
        """Provide skeleton tag filter object
        tags can be provided as a comma delimited string
        or an extracted list
        """
        self.intent = HFTagFilter()
        self.utterance = HFTagFilter()

    def set_tag_filter(self, level: str, tag_type: str, tags: Union[list,str]):
        """Sets tag filters"""
        accepted_levels = ["intent","utterance"]
        if not level in accepted_levels :
            raise InvalidFilterLevel(f"Accepted levels are {accepted_levels} level was: {level}")
        accepted_types = ["include","exclude"]
        if not tag_type in accepted_types :
            raise InvalidFilterType(f"Accepted tag_types are {accepted_types} tag_type was: {tag_type}")
        tags = self.validate_tag_list_format(tags)
        tag_filter = getattr(self,level)
        setattr(tag_filter,tag_type,tags)
        setattr(self,"level",tag_filter)

    def validate_tag_list_format(self,tags: Union[list,str]) -> list:
        """Validates the tag list"""
        if tags == []:
            return []
        if tags == "":
            return []
        if isinstance(tags, str):
            try:
                tags = tags.split(",")
                assert isinstance(tags, list)
                assert len(tags) > 0
            except InvalidTagFilterListFormat as e:
                error_msg_1 = "Couldn't parse -g --tags filters"
                error_msg_2 = "please make sure a quoted string with a comma separated list of tag names :"
                logger.error("%s %s %s", error_msg_1, error_msg_2, e)
                quit()
            return tags
        if isinstance(tags,list):
            return tags
            # could have a tag validate function here,
            # but that would need to check if have a labelled workspace to check against
        raise InvalidTagFilterListFormat(
            f"Did not recognise type of tags argument passed {tags} {type(tags)}"
        )

@dataclass_json
@dataclass
class HFIntent:
    '''Schema object for HF Intent

     Validates the format of an Intent

     Parameters
     ----------
     id:        str            unique id for intent
     name:      str            name of intent that will be displayed in HF studio
     metadata:  dict           a dictionary or HFMetadata object of string only key value pairs
     tags:      list           a list of HFTagReference objects
     parent_intent_id: str, optional  a reference to the ID of the immediate parent if using hierarchy intents
     '''
    id: str
    name: str
    metadata: HFMetadata = field(default_factory=dict)
    tags: List[HFTagReference] = field(default_factory=list)
    parent_intent_id: Optional[str] = None

    def __init__(self,
                 id: str, # pylint: disable=redefined-builtin
                 name: str,
                 metadata: HFMetadata = None,
                 tags: List[HFTagReference] = None,
                 parent_intent_id: Optional[str] = None):


        if metadata is None:
            metadata = {}

        if tags is None:
            tags = []

        self.id = id
        self.name = name
        self.parent_intent_id = parent_intent_id
        self.metadata = metadata
        self.tags = tags


@dataclass_json
@dataclass
class HFContext:
    '''Schema object for HFContext

    Validates the format of a the Context object interelating multiple HFExamples (utterances)
    within a document or conversation.

    Parameters
    ----------
    context_id: str             unique id for context object
    type      : str, optional   the document type, only "conversation" is currently supported
                                will control how the utterances display in multi utterance GUI items
    role      : str, optional   two roles are defined for conversation document
                                'client' - the analysed party in the tool typically the human user, customer etc.
                                'expert' - the responding party in the tool typically the bot, agent etc.
    '''
    context_id: Optional[str] = None
    type: Optional[str] = None
    role: Optional[str] = None

    def __init__(self,
                 context_id: Optional[str] = None,
                 type: Optional[str] = None, #pylint: disable=W0622:redefined-builtin
                 role: Optional[str] = None):
        self.context_id = context_id
        if type and type != '':
            if type in ['conversation',"utterance","training_phrase",'unknown']:
                self.type = type
                if role and role != '':
                    if type == 'conversation':
                        if role in ['expert', 'client']:
                            self.role = role
                        else:
                            raise HFContextRoleException(
                                'Only "client" or "expert" roles are currently supported with "converation" context type')
                    else:
                        raise HFContextRoleException(
                            'Not expecting a role for context types except conversation'
                        )
            else:
                raise HFContextTypeException(
                    'Only "conversation","utterance","training_phrase" and "unknown" document types are currently supported')


@dataclass_json
@dataclass
class HFIntentRef:
    '''Schema object for HFIntentRef - a reference to another intent typically for identifying the parent in a hierarchy

    Validates the format of a the HFIntentRef Object

    Parameters
    ----------
    intent_id: str  the id of the referenced intent
    '''
    intent_id: str

    def __init__(self, intent_id: str):
        self.intent_id = intent_id


@dataclass_json
@dataclass
class HFExample:
    '''Schema object for HFExample - a labelled or unlabelled utterance example

    Text from a document of some kind.
    May be a single utterance or be linked by a HFContext object to other examples forming a document
    May contain metadata about where was created useful to an annotator in the HF Studio

    TODO: annotation of entities

    Parameters
    ----------
    id:       str  An id for the Example
    text:     str  The text of the example
    context:  HFContext, optional  A HFContext object defining what document type the example came from
                                   defining what role the speaker/writer was performing and linking the
                                   example to other examples making up that document
    intents:  list HFIntentRef|HFIntent|str
                                   A list of HFintentRefs for intents, or a list of HFIntents
                                   or a list of strings containing intent ids
                                   May be empty list [] if so the utterance will be treated as unlabelled
    tags:     list HFTagReference A list of ids of intents for which this example text is an example of
                                   May be empty list [] if so the utterance will be treated as unlabelled
                                   and appear int the data section
                                   If provided these utterance will be treated as labelled and appear in the
                                   intents section
    metadata: dict | HFMetadata    A dict of string only key value pairs detailing information about the text
                                   useful to a future annotator
    '''
    id: str
    text: str
    created_at: str
    intents: List[HFIntentRef] = field(default_factory=list)
    tags: List[HFTagReference] = field(default_factory=list)
    metadata: HFMetadata = field(default_factory=dict)
    context: Optional[HFContext] = None

    def __init__(
            self,
            text: str,
            id: str, # pylint: disable=redefined-builtin
            created_at: Optional[datetime.datetime] = None,
            intents: Union[List[HFIntentRef],List[HFIntent],List[str]] = None,
            tags: List[HFTagReference] = None,
            metadata: HFMetadata = None,
            context: Optional[HFContext] = None
        ):

        if intents is None:
            intents = []

        if tags is None:
            tags = []

        if metadata is None:
            metadata = {}

        if context is None:
            context = {}

        self.id = id
        self.text = text
        self.intents = intents
        self.tags = tags
        self.metadata = metadata
        self.context = context
        if self.context is None:
            self.context = {}

        if created_at is not None:
            if isinstance(created_at, str):
                self.created_at = created_at
            else:
                self.created_at = created_at.isoformat() + 'Z'

        if len(intents) > 0:
            if isinstance(intents[0],HFIntentRef):
                self.intents = [HFIntentRef(intent.intent_id)
                                for intent in intents]
            elif isinstance(intents[0],HFIntent):
                self.intents = [HFIntentRef(intent.id)
                                for intent in intents]
            elif isinstance(intents[0],str):
                self.intents = [HFIntentRef(intent)
                                for intent in intents]
            else:
                raise HFInvlaidIntentTypeException(
                    "Intents can be provided as a list of HFIntentRef, HFIntent or str (intent_id) objects only")


class HFWorkspace:
    '''Schema object for HFWorkspace - may be used to update labelled or unlabelled data to HF Studio

    Validates the overall workspace and all sub objects

    TODO: entities

    Attributes
    ----------
    TODO:

    '''
    intents: Dict[str, HFIntent]
    intents_by_id: Dict[str, HFIntent]
    examples: Dict[str, HFExample]
    tags: Dict[str, HFTag]
    tag_reference: Dict[str, HFTagReference]
    delimiter: str

    def __init__(self):
        self.intents = {}
        self.intents_by_id = {}
        self.tags = {}
        self.tag_reference = {}
        self.examples = {}
        self.delimiter = None

    def intent(self,
               name_or_hier: Union[str, List[str]],
               id: Optional[str] = None, # pylint: disable=redefined-builtin
               tags: List[HFTagReference] = None,
               metadata: HFMetadata = None) -> HFIntent:
        '''Check whether the intent exists within the hierarchy provided, if it does return the intent object found
        If it does not, create it, along with all necessary parents that don't exist and return the new object

        Parameters
        ----------
        name_or_hier: str | List[str]       Name of the intent if no hierachy or the top level of an intent hierarchy
                                            i.e "billing"
                                            Or a list of names of intents in a list in the order of their hierarchy
                                            ["billing","issues","cannot_pay"]
        id:           str,optional          If not present will be generated as a repeatable hash of the text
        tags:         List[HFTagReference]  A list of tags placed on the intent and display in the tool
        metadata:     dict | HFMetadata     A dict of string only key value pairs detailing information about the text
                                            useful to an annotator in HF Studio
        '''
        if tags is None:
            tags = []

        if metadata is None:
            metadata = {}

        if not isinstance(name_or_hier, list):
            name_or_hier = [name_or_hier]

        parent_intent_id = None
        last = None
        for i,part in enumerate(name_or_hier):

            if part == '':
                break

            if i == 0:
                previous_parts = ""
                full_intent_path = part
            elif i == 1:
                previous_parts = name_or_hier[0]
                full_intent_path = "-".join([previous_parts,part])
            else:
                previous_parts = "-".join(name_or_hier[0:i])
                full_intent_path = "-".join([previous_parts,part])

            if  full_intent_path not in self.intents:
                if not id:
                    genid = f'intent-{len(self.intents)}'
                else:
                    genid = id

                # TODO: this doesn't work if you want the parent intent to have
                # different metadata or tags to the child intent.
                # the first child intent creates the full hierarchy
                intent = HFIntent(
                    id=genid,
                    name=part,
                    parent_intent_id=parent_intent_id,
                    metadata=metadata,
                    tags=tags,
                )
                self.intents[full_intent_path] = intent
                self.intents_by_id[genid] = intent
            last = self.intents[full_intent_path]
            parent_intent_id = last.id

        return last

    def tag_intent(self, intent_id, tag: HFTagReference):
        """Sets the intent tags"""
        # get the intent here
        intent = self.intent_by_id(intent_id)
        assert isinstance(intent, HFIntent)
        for i,_ in enumerate(intent.tags):
            assert isinstance(intent.tags[i], HFTagReference)
            if intent.tags[i] == tag.name:
                intent.tags[i] = tag
                self.intents_by_id[intent_id] = intent
                logger.info("tag_exists")
                return tag
        intent.tags.append(tag)
        self.intents_by_id[intent_id] = intent
        return tag

    def get_intent_index(self, delimiter: str) -> dict:
        """ Compute fully qualified intent name for all the intents"""

        # for every intent
        # go back up it's parent hierachy by id
        # reassemble name_or_hier
        # concatentate
        # in other file need to split and trim
        # hopefully should compare.
        intent_name_index = {}
        for intent_id in self.intents_by_id:
            working = self.intents_by_id[intent_id]
            fullpath = working.name
            while working.parent_intent_id:
                working = self.intents_by_id[working.parent_intent_id]
                fullpath = f'{working.name}{delimiter}{fullpath}'
            intent_name_index[intent_id] = fullpath
        return intent_name_index

    def write_csv(self, output_path: str,
                  intent_metadata: bool = True,
                  example_metadata: bool = True,
                  tags: bool = True,
                  delimiter: str = '-',
                  tag_filters:HFTagFilters = None) -> None:
        """Writes the HF Workspace to a CSV file at the fully qualified path output_path
        Will by default include intent level metadata, example level metdata and tags override using arguments
        Optionally will filter to only export certain tags"""

        intent_name_index = self.get_intent_index(delimiter=delimiter)

        obj_list = []
        for phrase_id in self.examples:
            example = self.examples[phrase_id]
            top_intent = example.intents[0].intent_id
            obj = {
                "utterance": example.text,
                "fully_qualified_intent_name": intent_name_index[example.intents[0].intent_id],
            }

            # intent level
            if intent_metadata:
                obj["intent_metadata"] = self.intent_by_id(top_intent).metadata
            if tags:
                tag_obj = {}
                for tag in self.intent_by_id(top_intent).tags:
                    tag_obj[tag.name] = True
                obj["intent_tags"] = tag_obj

            # example level
            if example_metadata:
                obj["example_metadata"] = example.metadata
            if tags:
                tag_obj = {}
                for tag in example.tags:
                    tag_obj[tag.name] = True
                obj["example_tags"] = tag_obj

            obj_list.append(copy.deepcopy(obj))


        df = pandas.json_normalize(obj_list, sep=delimiter)
        logger.info("df0 %s",df.shape)

        if tag_filters:
            filtered_df = pandas.DataFrame()

            # include utterances
            if len(tag_filters.utterance.include) > 0:
                for tag_name in tag_filters.utterance.include:
                    column_name = f'example_tags{delimiter}{tag_name}'
                    if column_name in df.columns.to_list():
                        filtered_df = pandas.concat([filtered_df,df[df[column_name] is True]])
            else:
                filtered_df = df
            filtered_df = filtered_df.drop_duplicates()
            logger.info('fi0 %s',filtered_df.shape)

            # exclude utterances
            for tag_name in tag_filters.utterance.exclude:
                column_name = f'example_tags{delimiter}{tag_name}'
                if column_name in filtered_df.columns.to_list():
                    filtered_df = filtered_df[filtered_df[column_name] is not True]
            filtered_df = filtered_df.drop_duplicates()
            logger.info('fi0 %s',filtered_df.shape)

            final_df = pandas.DataFrame()

            # include intents
            if len(tag_filters.intent.include) > 0:
                for tag_name in tag_filters.intent.include:
                    column_name = f'intent_tags{delimiter}{tag_name}'
                    if column_name in filtered_df.columns.to_list():
                        final_df = pandas.concat([final_df,filtered_df[filtered_df[column_name] is True]])
            else:
                final_df = filtered_df
            final_df = final_df.drop_duplicates()
            logger.info('fa0 %s',final_df.shape)

            # exclude intents
            for tag_name in tag_filters.intent.exclude:
                column_name = f'intent_tags{delimiter}{tag_name}'
                if column_name in final_df.columns.to_list():
                    final_df = final_df[final_df[column_name] is not True]
            final_df = final_df.drop_duplicates()
            logger.info('fa0 %s',final_df.shape)

            df = final_df

        df = df.sort_values(["fully_qualified_intent_name"],ignore_index=True)
        df.to_csv(output_path, sep=",", encoding="utf8", index=False)
        logger.info("\n%s",df)


    def intent_by_id(self, id: str) -> Optional[HFIntent]: # pylint: disable=redefined-builtin
        '''Return a particular intent by id

        Parameters
        ----------
        id: str   id to return
        '''
        return self.intents_by_id.get(id)

    def tag(self, tag: str, color: Optional[str] = None, is_tag_ref: bool = True):
        '''Check whether tag (i.e tag name) already exists, if it does return the tag object with that name
        If not create the tag object
        '''
        if tag not in self.tags:
            tag_id = f'tag-{uuid.uuid4()}'
            self.tags[tag] = HFTag(tag_id, tag, color)
            self.tag_reference[tag] = HFTagReference(id = self.tags[tag].id,
                                                     name = self.tags[tag].name)

        if is_tag_ref:
            return self.tag_reference[tag]
        else:
            return self.tags[tag]

    def example(self, text: str,
                id: Optional[str] = None, # pylint: disable=redefined-builtin
                created_at: Optional[datetime.datetime] = None,
                intents: List[HFIntent] = None,
                tags: List[HFTagReference] = None,
                metadata: HFMetadata = None,
                context: Optional[HFContext] = None) -> HFExample:
        '''Create a new example based on passed properties, assigning an ID if necessary
        '''

        if intents is None:
            intents = []

        if tags is None:
            tags = []

        if metadata is None:
            metadata = {}

        if id is None:
            id = f'ex-{hash_string(text)}'

        if id in self.examples:
            return self.examples[id]

        if created_at is None:
            created_at = datetime.datetime.now()

        ex = HFExample(
            text=text,
            id=id,
            created_at=created_at,
            intents=intents,
            tags=tags,
            metadata=metadata,
            context=context,
        )

        self.examples[ex.id] = ex

        return ex

    def add_example(self, example: HFExample):
        '''Add an example to the workspace based on an example created elsewhere using the HFExample constructor
        '''
        assert isinstance(example, HFExample)
        if example.id is None:
            raise HFExxampleIDNotPresentException(
                'All examples must have an id to be included in a workspace?')
        self.examples[example.id] = example

    def get_fully_qualified_intent_name(self, intent_id: str) -> str:
        """Gets fully qualified intent name"""

        working = self.intents_by_id[intent_id]
        fullpath = working.name
        while working.parent_intent_id:
            working = self.intents_by_id[working.parent_intent_id]
            fullpath = f'{working.name}{self.delimiter}{fullpath}'

        return fullpath

    @staticmethod
    def from_json(workspace_input: Union[IO, dict], delimiter: str) -> 'HFWorkspace':
        '''
        Read and validate a HFWorkspace object from a dict of a json (from api)
        or from a json file

        It is required to provide a delimiter for intent name.
        It can be None if there are no child intents, otherwise any other character to separate parent and child intent.
        Most widely used delimiters are / or -
        '''
        if isinstance(workspace_input, IO):
            obj = HFWorkspaceJson.from_json(workspace_input.read(), infer_missing=True) # pylint: disable=no-member
        elif isinstance(workspace_input, dict):
            obj = HFWorkspaceJson.from_json( # pylint: disable=no-member
                json.dumps(workspace_input), infer_missing=True)
        else:
            raise HFInvalidWorkspaceInputTypeException(f"What is this thing of type: {type(workspace_input)}")

        workspace = HFWorkspace()
        workspace.intents = {intent.name: intent for intent in obj.intents}
        workspace.intents_by_id = {intent.id: intent for intent in obj.intents}
        workspace.tags = {tag.id: tag for tag in obj.tags}
        workspace.examples = {example.id: example for example in obj.examples}
        workspace.delimiter = delimiter

        return workspace

    def get_hf_json(self) -> dict:
        '''Returns workspace object into HF format
        '''

        sorted_examples = list(self.examples.values())
        sorted_examples.sort(key=lambda ex: ex.created_at)
        workspace = {
            "$schema": "https://docs.humanfirst.ai/hf-json-schema.json",
            "examples": [ex.to_dict() for ex in sorted_examples],
        }

        if len(self.tags) > 0:
            workspace['tags'] = [tag.to_dict() for tag in self.tags.values()]

        if len(self.intents) > 0:
            list_intents = []
            for intent in self.intents.values():
                intent = intent.to_dict()
                # schema does not accept null parent id
                if intent["parent_intent_id"] is None:
                    del intent["parent_intent_id"]
                list_intents.append(intent)
            workspace['intents'] = list_intents

        return workspace

    def write_json(self, output: IO, jsonl=False, indent=2):
        '''Write workspace object into HF format for uploading to studio
        '''

        workspace = self.get_hf_json()

        if jsonl:
            indent = None

        json.dump(workspace, output, indent=indent)

        if jsonl:
            output.write('\n')


@dataclass_json
@dataclass
class HFWorkspaceJson:
    '''JSON version of the workspace'''
    examples: List[HFExample] = field(default_factory=list)
    intents: List[HFIntent] = field(default_factory=list)
    tags: List[HFTag] = field(default_factory=list)


def hash_string(s: str, prefix: Optional[str] = None) -> str:
    '''Hash a string into a repeatable id with an optional prefix
    lets you build    myprefix-guid from "Blah whatever"
    '''
    hexdigest = hashlib.new('sha256', s.encode('utf-8')).hexdigest()
    if prefix:
        return f'{prefix}-{hexdigest[0:20]}'
    else:
        return f'{hexdigest[0:20]}'

def generate_random_color() -> str:
    """Generates random colour"""
    return '#' + ''.join([random.choice('0123456789ABCDEF') for j in range(6)])

class InvalidFilterLevel(Exception):
    """Exception raised when tag filter value is invalid"""
class InvalidFilterType(Exception):
    """Exception raised when tag filter type is invalid"""
class InvalidTagFilterListFormat(Exception):
    """Exception raised when tag filter list is invalid"""
