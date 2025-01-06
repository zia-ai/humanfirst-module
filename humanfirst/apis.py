# pylint: disable=too-many-lines
"""
apis.py

Examples of how to the call the HumanFirst APIs

"""
# *********************************************************************************************************************

# standard imports
import json
import base64
import datetime
import os
from configparser import ConfigParser
import logging
import logging.config
import time # pylint: disable=unused-import

# third party imports
import requests
import requests_toolbelt
from dotenv import load_dotenv, find_dotenv

# custom imports
from .authorization import Authorization

# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

# CONSTANTS
constants = ConfigParser()
path_to_config_file = os.path.join(here,'config','setup.cfg')
constants.read(path_to_config_file)

CLOCK_SYNC_DRIFT_AMBIGUITY = 0

# constants need type conversion from str to int
TIMEOUT = float(constants.get("humanfirst.CONSTANTS","TIMEOUT"))
EXPIRY_ADDITION = int(constants.get("humanfirst.CONSTANTS","EXPIRY_ADDITION"))
VALID = constants.get("humanfirst.CONSTANTS","VALID")
REFRESHING = constants.get("humanfirst.CONSTANTS","REFRESHING")
EXPIRED = constants.get("humanfirst.CONSTANTS","EXPIRED")
# BASE_URL_TEST must be set by environment variable expected of the form BASE_URL_TEST=http://172.17.0.3:8888
BASE_URL_PROD = constants.get("humanfirst.CONSTANTS","BASE_URL_PROD")
BASE_URL_STAGING = constants.get("humanfirst.CONSTANTS","BASE_URL_STAGING")
BASE_URL_QA = constants.get("humanfirst.CONSTANTS","BASE_URL_QA")
BASE_URL_PRE_PROD = constants.get("humanfirst.CONSTANTS","BASE_URL_PRE_PROD")

# locate where we are
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
    path_to_save_log = '/dev/null'  # On Linux/MacOS, this discards logs (Windows: NUL) pylint:disable=invalid-name
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
logger = logging.getLogger('humanfirst.apis')

# ******************************************************************************************************************120
#
# Exceptions
#
# *********************************************************************************************************************
class HFAPIResponseValidationException(Exception):
    """When response validation fails"""

    def __init__(self, url: str, response, payload: dict = None, wantzip: bool = False):
        if payload is None:
            payload = {}
        self.url = url
        self.response = response
        self.payload = payload
        self.wantzip = wantzip
        self.message = f'Did not receive 200 from url: {url} {self.response.status_code} {self.response.text}'
        if self.wantzip:
            self.message = self.message = ' zip expected but not received'
        super().__init__(self.message)

class HFAPIParameterException(Exception):
    """When parameter validation fails"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFEnvironmentException(Exception):
    """When user provides an incorrect environment"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# ******************************************************************************************************************120
# API class containing API call methods
# *********************************************************************************************************************

class HFAPI:
    """HumanFirst API"""

    bearer_token: dict

    def __init__(self, username: str = "",
                 password: str = "",
                 environment: str = "",
                 api_version: str = "",
                 timeout: float = TIMEOUT):
        """
        Initializes bearertoken

        Recommended to store the credentials only as environment variables
        There are 4 ways username and password is passed onto the object
        1. HF_USERNAME and HF_PASSWORD can be set as environment variables.
        2. You can authentivcate using Humanfirst CLI and it will set the CLI specific environment variables for you.
        3. A .env file be placed in the root directory of the project.
        4. username and password can be used while instantiating the object.
        """

        dotenv_path = find_dotenv(usecwd=True)

        # load the environment variables from the .env file if present
        load_dotenv(dotenv_path=dotenv_path)

        if environment == "":
            # this automatically checks if the environment variable is available in CLI first
            # and then checks the .env varaiables
            environment = os.environ.get("HF_ENVIRONMENT")
            if environment is None:
                environment = "prod"
            self.studio_environment = environment

        if api_version == "":
            # this automatically checks if the environment variable is available in CLI first
            # and then checks the .env varaiables
            api_version = os.environ.get("HF_API_VERSION")
            if api_version is None:
                api_version = "v1alpha1"
            self.api_version = api_version

        self.timeout = timeout

        # by default the url points to prod
        # This case section sets the Key used to authenticate with the GCP key issuing server
        # and the URL of the humanfirst environment
        if self.studio_environment == "prod":
            self.base_url = BASE_URL_PROD
        # This option assumes you are running a container locally
        # In this case the IP address must be set as a Env variable
        # BASE_URL_TEST
        elif self.studio_environment == "test":
            self.base_url = os.environ.get("BASE_URL_TEST")
        elif self.studio_environment == "staging":
            self.base_url = BASE_URL_STAGING
        elif self.studio_environment == "qa":
            self.base_url = BASE_URL_QA
        elif self.studio_environment == "pre_prod":
            self.base_url = BASE_URL_PRE_PROD
        else:
            raise HFEnvironmentException(
                "HF_ENVIRONMENT is not set to one of the following - prod, staging, qa, pre_prod")

        # Check if URL ends with /
        if self.base_url[-1] == "/":
            self.base_url = self.base_url[:-1]

        self.auth = Authorization(username=username,
                                  password=password,
                                  environment=self.studio_environment,
                                  timeout=self.timeout)

    def _validate_response(self,
                           response: requests.Response,
                           url: str,
                           field: str = None,
                           payload: dict = None,
                           wantzip: bool = False,
                           wantcsv: bool = False
        ):
        """Validate the response from the API and provide consistent aerror handling"""
        if payload is None:
            payload = {}
        if response.status_code != 200 and response.status_code != 201:
            raise HFAPIResponseValidationException(
                url=url, payload=payload, response=response)

        # if we are looking for a wantzip validate and return
        if wantzip:
            if 'Content-Type' in response.headers and 'application/zip' in response.headers['Content-Type']:
                # the response is a zip file
                return response
            else:
                return HFAPIResponseValidationException(url=url, payload=payload, response=response, wantzip=wantzip)
        elif wantcsv:
            if 'Content-Type' in response.headers and 'text/csv; charset=UTF-8;' in response.headers['Content-Type']:
                return response.text
        # else we assume we are looking for a json object
        else:
            # so if it's a string raise that as an error
            if isinstance(response, str):
                raise HFAPIResponseValidationException(
                url=url, payload=payload, response=response)

            # Check for the passed field or return the full object
            try:
                candidate = response.json()
            except requests.JSONDecodeError as e:
                logging.error('Response Status code: %s \nResponse_text: %s \nError: %s',
                              response.status_code,
                              response.text,
                              e)
                raise
            if candidate:
                if field and field in candidate.keys():
                    return candidate[field]
                else:
                    return candidate
            else:
                return {}

    # *****************************************************************************************************************
    # Tags
    # *****************************************************************************************************************

    def get_tags(self, namespace: str, playbook: str, timeout: float = None) -> dict:
        '''Returns tags'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/tags'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "tags")

    def delete_tag(self, namespace: str, playbook: str, tag_id: str, timeout: float = None) -> dict:
        '''Returns tags'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "tag_id": tag_id
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/tags/{tag_id}'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "DELETE", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def create_tag(self, namespace: str, playbook: str,
                tag_id: str, tag_name: str, tag_color: str,
                timeout: float = None) -> dict:
        '''Create a tag'''

        now = datetime.datetime.now()
        now = now.isoformat()

        tag = {
            "id": tag_id,
            "name": tag_name,
            "color": tag_color
        }

        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "tag":tag
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/tags'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    # *****************************************************************************************************************
    # Playbooks/Workspaces
    # *****************************************************************************************************************

    def create_playbook(self, namespace: str, playbook_name: str, timeout: float = None) -> dict:
        '''
        Creates a playbook in the given namespace

        If the playbook name already exists, that playbook gets deleted and a new one is creates
        '''
        payload = {
            "namespace": namespace,
            "playbook_name": playbook_name,
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "playbooks")

    def list_playbooks(self, namespace: str, timeout: float = None) -> dict:
        '''Returns list of all playbooks for an organisation
        Note namepsace parameter doesn't appear to provide filtering'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "playbooks")

    def get_playbook_info(self, namespace: str, playbook: str, timeout: float = None) -> dict:
        '''Returns metadata of playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/playbooks/{namespace}/{playbook}'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def get_playbook(self,
                    namespace: str,
                    playbook: str,
                    hierarchical_delimiter="-",
                    hierarchical_intent_name_disabled: bool = True,
                    zip_encoding: bool = False,
                    include_negative_phrases: bool = False,
                    timeout: float = None
                    ) -> dict:
        '''Returns the actual training information including where present in the workspace
        * intents
        * examples
        * entities
        * tags
        '''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "format": 7,
            "format_options": {
                "hierarchical_intent_name_disabled": hierarchical_intent_name_disabled,
                "hierarchical_delimiter": hierarchical_delimiter,
                "zip_encoding": zip_encoding,
                "include_negative_phrases": include_negative_phrases
            }
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/intents/export'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        response = self._validate_response(response, url, "data")
        response = base64.b64decode(response)
        response = response.decode('utf-8')
        response_dict = json.loads(response)
        return response_dict

    def delete_playbook(self,
                        namespace: str,
                        playbook_id: str,
                        hard_delete: bool = False,
                        timeout: float = None) -> dict:
        '''
        Delete the playbook provided

        hard_delete - Don't just flag the playbook as deleted, but completely delete it from the database
        '''

        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
            "hard_delete": hard_delete
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook_id}'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "DELETE", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "playbooks")

    # *****************************************************************************************************************
    # Intents
    # *****************************************************************************************************************

    def get_intents(self, namespace: str, playbook: str, timeout: float = None) -> dict:
        '''Get all the intents in a workspace'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/intents'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "intents")


    def get_intent(self, namespace: str, playbook: str, intent_id: str, timeout: float = None) -> dict:
        '''Get the metdata for the intent needed'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/intents/{intent_id}'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)


    def get_revisions(self, namespace: str, playbook: str, timeout: float = None) -> dict:
        '''Get revisions for the namespace and playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/revisions'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "revisions")

    def update_intent(self,
                      namespace: str,
                      playbook: str,
                      intent: dict,
                      update_mask: str,
                      timeout: float = None) -> dict:
        '''Update an intent

        *update_mask = <keywords used in an intent hf format>
        this helps in updating specific keyword
        '''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "intent": intent,
            "update_mask": update_mask
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/intents'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "PUT", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def import_intents(
            self,
            namespace: str, playbook: str,
            workspace_as_dict: dict,
            format_int: int = 7,
            hierarchical_intent_name_disabled: bool = True,
            hierarchical_delimiter: str = "/",
            zip_encoding: bool = False,
            gzip_encoding: bool = False,
            include_negative_phrases: bool = False,
            skip_empty_intents: bool = True,
            clear_intents: bool = False,
            clear_entities: bool = False,
            clear_tags: bool = False,
            merge_intents: bool = False,
            merge_entities: bool = False,
            merge_tags: bool = False,
            # extra_intent_tags: list = None,
            # extra_phrase_tags: list = None,
            override_metadata: bool = True,
            override_name: bool = True,
            timeout: float = None
        ) -> dict:
        """Import intents using multipart assuming an input humanfirst JSON file

        Reference: https://docs.humanfirst.ai/api/import-intents

        How to nest Request object?

        """

        assert isinstance(workspace_as_dict,dict)

        payload = {
            'namespace': namespace,
            'playbook_id': playbook,
            'format': format_int, #', # or 7?
            'format_options': {
                'hierarchical_intent_name_disabled': hierarchical_intent_name_disabled,
                'hierarchical_delimiter': hierarchical_delimiter,
                'zip_encoding': zip_encoding,
                'gzip_encoding': gzip_encoding,
                'include_negative_phrases': include_negative_phrases,
                # intent_tag_predicate: {},
                # phrase_tag_predicate: {},
                'skip_empty_intents': skip_empty_intents
            },
            'import_options': {
                'clear_intents': clear_intents,
                'clear_entities': clear_entities,
                'clear_tags': clear_tags,
                'merge_intents': merge_intents,
                'merge_entities': merge_entities,
                'merge_tags': merge_tags,
                # 'extra_intent_tags': extra_intent_tags,
                # 'extra_phrase_tags': extra_phrase_tags,
                'override_metadata': override_metadata,
                'override_name': override_name
            },
            'data':''
        }

        # The payload needs to be string encoded with the field information - ' turns into "
        payload = json.dumps(payload,indent=2)

        # then the data needs to be bytes to be parsed but stored as string in the URL call
        data_encoded_string = base64.urlsafe_b64encode(json.dumps(workspace_as_dict,indent=2).encode('utf-8')).decode('utf-8') # pylint: disable=line-too-long
        payload = payload.replace('\"data\": \"\"',f'\"data\": \"{data_encoded_string}\"')

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/intents/import'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=effective_timeout)
        return self._validate_response(response, url)

    def import_intents_http(
            self,
            namespace: str, playbook: str,
            workspace_file_path: str, # or union HFWorkspace
            # format_int: int = 7,
            hierarchical_intent_name_disabled: bool = True,
            hierarchical_delimiter: str = "/",
            timeout: float = None
            # zip_encoding: bool = False,
            # gzip_encoding: bool = False,
            # clear_intents: bool = False,
            # clear_entities: bool = False,
            # clear_tags: bool = False,
            # merge_intents: bool = False,
            # merge_entities: bool = False,
            # merge_tags: bool = False,
            # extra_intent_tags: list = None,
            # extra_phrase_tags: list = None,
            # override_metadata: bool = True,
            # override_name: bool = True
        ) -> dict:
        """Import intents using multipart assuming an input humanfirst JSON file

        Reference: https://docs.humanfirst.ai/api/import-intents-http

        How to nest Request object?

        TODO: this doesn't currently work as is - see intents_import option instead

        """

        payload = requests_toolbelt.multipart.encoder.MultipartEncoder(
            fields={
                'file': ("upload_name", workspace_file_path, 'application/json'),
                'format': 'INTENTS_FORMAT_HF_JSON',
                "namespace": namespace,
                "playbook_id": playbook,
                "format_options": str(hierarchical_intent_name_disabled),
                "hierarchical_delimiter": str(hierarchical_delimiter)
                # 'request' : {
                #     "namespace": namespace,
                #     "playbook_id": playbook,
                #     "format": format_int,
                #     "format_options": hierarchical_intent_name_disabled,
                #     "hierarchical_delimiter": hierarchical_delimiter,
                #     "zip_encoding": zip_encoding,
                #     "gzip_encoding": gzip_encoding,
                #     "import_options": {
                #         "clear_intents": clear_intents,
                #         "clear_entities": clear_entities,
                #         "clear_tags": clear_tags,
                #         "merge_intents": merge_intents,
                #         "merge_entities": merge_entities,
                #         "merge_tags": merge_tags,
                #         "extra_intent_tags": extra_intent_tags,
                #         "extra_phrase_tags": extra_phrase_tags,
                #         "override_metadata": override_metadata,
                #         "override_name": override_name
                #     }
                # }
            }
        )

        headers = self._get_headers()

        headers["Content-Type"] = payload.content_type

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/intents/import_http'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=effective_timeout)
        return self._validate_response(response, url)


    # *****************************************************************************************************************
    # Call NLU engines
    # *****************************************************************************************************************

    def get_models(self, namespace: str, timeout: float = None) -> dict:
        '''Get available models for a namespace
        NOTE: THIS IS NOT nlu-id!'''
        payload = {}

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/models'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        models = self._validate_response(response, url, "models")
        namespace_models = []
        for model in models:
            if model["namespace"] == namespace:
                namespace_models.append(model)
        return namespace_models


    def get_nlu_engines(self, namespace: str, playbook: str, timeout: float = None) -> dict:
        '''Get nlu engines for the for the namespace and playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/playbooks/{namespace}/{playbook}/nlu_engines'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "nluEngines")


    def get_nlu_engine(self, namespace: str, playbook: str, nlu_id: str, timeout: float = None) -> dict:
        '''Get nlu engine for the for the namespace and playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "nlu_id": nlu_id
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/playbooks/{namespace}/{playbook}/nlu_engines/{nlu_id}'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def list_trained_nlu(self, namespace: str, playbook: str, timeout: float = None) -> dict:
        '''Get trained run ids for the playbook, then will have to filter by the nlu_engine interested in'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/nlu'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, field="runs")


    def trigger_train_nlu(self, namespace: str, playbook: str, nlu_id: str,
                        force_train: bool = True, skip_train: bool= False,
                        force_infer: bool = False, skip_infer: bool = True,
                        auto: bool = False, timeout: float = None) -> dict:
        '''Trigger training for a workspace here we only allow for one request for
        one engine - but theoretically you can call to trigger many on the same
        playbook

        This example skips the infer by default - override the settings to stop skipping
        if enabled by default, or force it if not enabled by default

        This returns

        '''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "parameters": {
                "engines": [
                    {
                        "nlu_id": nlu_id, # Unique identifier of the NLU engine to train.
                        "force_train": force_train, # Force training an on-demand NLU engine.
                        "skip_train": skip_train, # Skip training of an NLU engine even if it's not on-demand.
                        "force_infer": force_infer, # Force inference of an on-demand NLU engine.
                        "skip_infer": skip_infer # Skip inference of an NLU engine even if it's not on-demand.
                    }
                ],
                "auto": auto # If true, signals that the training is an automatic run.
            }
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/nlu:train'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)

        return self._validate_response(response, url)


    def predict(self, sentence: str, namespace: str, playbook: str,
                model_id: str = None, revision_id: str = None, timeout: float = None) -> dict:
        '''Get response_dict of matches and hier matches for an input
        optionally specify which model and revision ID you want the prediction from
        model_id probably better know as nlu-id
        revision_id probably better known as run_id
        but it needs to be the run_id of the model job not revisions which is showing export job
        TODO: update when updated'''

        headers = self._get_headers()

        payload = {
            "namespace": "string",
            "playbook_id": "string",
            "input_utterance": sentence
        }

        if model_id or revision_id:
            if not model_id or not revision_id:
                raise HFAPIParameterException(
                    "If either specified both model_id and revision_id are required")

        if model_id:
            payload["model_id"] = model_id
        if revision_id:
            payload["revision_id"] = model_id

        url = f'{self.base_url}/{self.api_version}/nlu/predict/{namespace}/{playbook}'
        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)


    def batchPredict(self, sentences: list, # pylint: disable=invalid-name
                     namespace: str,
                     playbook: str,
                     timeout: float = None,
                     model_id: str = "",
                     revision_id: str = "") -> dict:
        '''Get response_dict of matches and hier matches for a batch of sentences
        Accepts an optional model_id and revision_id to run it against a previous
        version of the NLU, if these are not provided it defaults to the latest'''
        payload = {
            "namespace": "string",
            "playbook_id": "string",
            "input_utterances": sentences,
        }
        if model_id != "":
            payload["model_id"] = model_id
        if revision_id != "":
            payload["revision_id"] = revision_id

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/nlu/predict/{namespace}/{playbook}/batch'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "predictions")

    # *****************************************************************************************************************
    # Coverage
    # *****************************************************************************************************************

    def get_intents_coverage_request(self,
                                     namespace: str,
                                     playbook: str,
                                     data_selection: int = 1,
                                     model_id: str = None,
                                     timeout: float = None):
        '''Download a set of coverage histogram data at 0.5 confidence clip intervals
        TODO: this is unvalidated in academy

        data_selection values are:
        DATA_TYPE_DEFAULT = 0
        DATA_TYPE_ALL = 1
        DATA_TYPE_UPLOADED = 2
        DATA_TYPE_GENERATED = 3
        '''

        payload = {
            "namespace": namespace,
            "playbook": playbook,
            "data_selection": data_selection
        }

        if model_id:
            payload["model_id"] = model_id

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/coverage/latest'
        effective_timeout = timeout if timeout is not None else self.timeout
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "report")

    def export_intents_coverage(self,
                                namespace: str,
                                playbook: str,
                                model_id: str = None,
                                confidence_threshold: int = 70, # This is the default in the GUI
                                coverage_type: int = 1, # COVERAGE_TYPE_TOTAL
                                data_selection: int = 1, # DATA_TYPE_ALL
                                timeout: float = None
                                ):
        '''Get the coverage calculation at a certain clip returned as a csv file
        This works the same as downloading the coverage report from the intents tab

        coverage_type
        COVERAGE_TYPE_UNIQUE = 0;
        COVERAGE_TYPE_TOTAL = 1;

        data_selection values are:
        DATA_TYPE_DEFAULT = 0
        DATA_TYPE_ALL = 1
        DATA_TYPE_UPLOADED = 2
        DATA_TYPE_GENERATED = 3
        '''

        payload = {
            "namespace": namespace,
            "playbook": playbook,
            "confidence_threshold": confidence_threshold,
            "coverage_type": coverage_type,
            "data_selection": data_selection
        }

        if model_id:
            payload["model_id"] = model_id

        logger.info('PAYLOAD - %s ', payload)

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/coverage/latest/export'
        params0 = f'?namespace={namespace}&playbook={playbook}&confidence_threshold={confidence_threshold}'
        params1 = f'&coverage_type={coverage_type}&data_selection={data_selection}'
        url = url + params0 + params1

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, wantcsv=True)


    # *****************************************************************************************************************
    # Authorisation
    # *****************************************************************************************************************

    def  _get_headers(self) -> dict:
        """Produce the necessary header"""

        # validate the token
        self.auth.validate_jwt()

        headers = {}
        bearer_string = f'Bearer {self.auth.bearer_token_dict["token"]}'
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'Authorization': bearer_string
        }

        return headers


    # *****************************************************************************************************************
    # Conversation sets
    # *****************************************************************************************************************

    def get_conversation_set_list(self, namespace: str, timeout: float = None) -> tuple:
        """Get all the conversation sets and their info for a namespaces"""

        payload = {}

        headers = self._get_headers()

        url = f"{self.base_url}/{self.api_version}/conversation_sets?namespace={namespace}"

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=effective_timeout)
        conversation_sets = self._validate_response(response=response,url=url,field='conversationSets')

        # make it a list looking up each individual one
        conversation_set_list = []
        for conversation_set in conversation_sets:
            conversation_set_id = conversation_set['id']

            url = f"{self.base_url}/{self.api_version}/conversation_sets/{namespace}/{conversation_set_id}"
            response = requests.request(
                "GET", url, headers=headers, data=payload, timeout=effective_timeout)
            conversation_set = self._validate_response(response=response,url=url)

            if "state" in conversation_set.keys():
                conversation_set["no_data_file_is_uploaded_since_creation"] = False
                if (("jobsStatus" in conversation_set["state"].keys()) and
                        ("jobs" in conversation_set["state"]["jobsStatus"].keys())):
                    jobs_dict = {}
                    jobs = conversation_set["state"]["jobsStatus"]["jobs"]
                    range_end = range(len(jobs))
                    for i in range_end:
                        if jobs[i]["name"] in ["merged", "filtered", "indexed", "embedded"]:
                            jobs_dict[jobs[i]["name"]] = jobs[i]
                            del jobs_dict[jobs[i]["name"]]["name"]
                    conversation_set["is_datafolder_empty"] = False
                    conversation_set["state"]["jobsStatus"]["jobs"] = jobs_dict
                else:
                    conversation_set["is_datafolder_empty"] = True
            else:
                conversation_set["is_datafolder_empty"] = True
                conversation_set["no_data_file_is_uploaded_since_creation"] = True
            conversation_set_list.append(conversation_set)

        return conversation_set_list

    def get_conversation_set(self, namespace: str, conversation_set_id: str, timeout: float = None) -> dict:
        """Get conversation set"""

        headers = self._get_headers()

        payload = {
            "namespace":namespace,
            "conversation_set_id":conversation_set_id
        }
        url = f"{self.base_url}/{self.api_version}/conversation_sets/{namespace}/{conversation_set_id}"

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=effective_timeout)
        return self._validate_response(response=response,url=url)

    def create_conversation_set(self, namespace: str, convoset_name: str, timeout: float = None) -> dict:
        """Creates a conversation set. Returns conversation source ID"""

        payload = {
            "namespace": namespace,
            "conversation_set":{
                "name": convoset_name,
                "description": ""
            }
        }

        headers = self._get_headers()

        url = f"{self.base_url}/{self.api_version}/conversation_sets/{namespace}"

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        create_conversation_response = self._validate_response(response=response, url=url)
        convo_set_id = create_conversation_response["id"]

        # check whether conversation source has been created
        # If not, then create one
        get_convo_set_config_response = self.get_conversation_set_configuration(namespace=namespace,
                                                                                convoset_id=convo_set_id)

        if "sources" in get_convo_set_config_response:
            conversation_source_id = get_convo_set_config_response["sources"][0]["userUpload"]["conversationSourceId"]

        else:
            update_convo_set_config_response = self.update_conversation_set_configuration(namespace=namespace,
                                                                                          convoset_id=convo_set_id)

            conversation_source_id=update_convo_set_config_response["sources"][0]["userUpload"]["conversationSourceId"]

        return conversation_source_id

    def create_conversation_set_with_set_and_src_id(self,
                                                    namespace: str,
                                                    convoset_name: str,
                                                    timeout: float = None) -> dict:
        """Creates a conversation set. Returns both conversation set and source ID"""

        payload = {
            "namespace": namespace,
            "conversation_set":{
                "name": convoset_name,
                "description": ""
            }
        }

        headers = self._get_headers()

        url = f"{self.base_url}/{self.api_version}/conversation_sets/{namespace}"

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        create_conversation_response = self._validate_response(response=response, url=url)
        convo_set_id = create_conversation_response["id"]

        # check whether conversation source has been created
        # If not, then create one
        get_convo_set_config_response = self.get_conversation_set_configuration(namespace=namespace,
                                                                                convoset_id=convo_set_id)

        if "sources" in get_convo_set_config_response:
            conversation_source_id = get_convo_set_config_response["sources"][0]["userUpload"]["conversationSourceId"]

        else:
            update_convo_set_config_response = self.update_conversation_set_configuration(namespace=namespace,
                                                                                          convoset_id=convo_set_id)

            conversation_source_id=update_convo_set_config_response["sources"][0]["userUpload"]["conversationSourceId"]

        conversation_obj = {
            "convoset_id": convo_set_id,
            "convosrc_id": conversation_source_id
        }

        return conversation_obj

    def link_conversation_set(self, namespace: str, playbook_id: str, convoset_id: str, timeout: float = None) -> dict:
        """Link conversation sets"""

        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
            "conversation_sets": [{
                "namespace": namespace,
                "id": convoset_id
            }]
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/conversation_sets/{namespace}:link'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    # TODO: Implement API to get the list of playbook ids a convoset is linked to
    def unlink_conversation_set(self,
                                namespace: str,
                                playbook_id: str,
                                convoset_id: str,
                                timeout: float = None) -> dict:
        """Unlink conversation sets"""

        # TODO: Unlink convoset from all the linked workspaces

        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
            "conversation_sets": [{
                "namespace": namespace,
                "id": convoset_id
            }]
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/conversation_sets/{namespace}:unlink'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def delete_conversation_set(self, namespace: str, convoset_id: str, timeout: float = None) -> dict:
        """Deletes a conversation_set"""

        # TODO: A "force" boolean method parameter
        #       when enabled, the convoset should be unlinked from all the workspaces and deleted

        payload = {
            "namespace": namespace,
            "id": convoset_id
        }

        headers = self._get_headers()

        url = f"{self.base_url}/{self.api_version}/conversation_sets/{namespace}/{convoset_id}"

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "DELETE", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response=response, url=url)

    def get_conversation_set_configuration(self, namespace: str, convoset_id: str, timeout: float = None) -> dict:
        """Gets conversation set configuration"""

        payload = {
            "namespace": namespace,
            "id": convoset_id
        }

        headers = self._get_headers()

        url = f"{self.base_url}/{self.api_version}/conversation_sets/{namespace}/{convoset_id}/config"

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response=response, url=url)

    def list_conversation_src_files(self, namespace: str, conversation_set_src_id: str, timeout: float = None) -> dict:
        """Get the list of conversation files within a convo set."""

        headers = self._get_headers()

        payload = {
            "namespace":namespace,
            "conversation_set_id":conversation_set_src_id
        }
        url = f"{self.base_url}/{self.api_version}/files/{namespace}/{conversation_set_src_id}"

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=effective_timeout)
        return self._validate_response(response=response,url=url,field="files")

    def delete_conversation_file(self,
                                 namespace:str,
                                 conversation_set_src_id: str,
                                 file_name:str,
                                 timeout: float = None,
                                 no_trigger: bool = False):
        """Deletes a specific file within a convo set.
        no_trigger=True prevents indexes from building if passed in case you want to delete
        or upload additional files before triggering them.  If you use this you must 
        upload or delete a final file with no_trigger=False (the default) otherwise the new data in 
        your conversation set will not be available to other processes."""

        headers = self._get_headers()

        # check no trigger        
        if no_trigger:
            str_no_trigger = "true"
        else:
            str_no_trigger = "false"

        payload = {
            "namespace":namespace,
            "no_trigger": no_trigger, # TODO: debugging this should it be a string or a boolean?  json.dumps will change True to true, no quotes
            "filename": file_name,
            "conversation_source_id":conversation_set_src_id
        }
        print(payload)
        url = f"{self.base_url}/{self.api_version}/files/{namespace}/{conversation_set_src_id}/{file_name}"

        effective_timeout = timeout if timeout is not None else self.timeout
        
        print(json.dumps(payload))

        response = requests.request(
            "DELETE", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response=response,url=url)

    def update_conversation_set_configuration(self, namespace: str, convoset_id: str, timeout: float = None) -> dict:
        """Update conversation set configuration"""

        payload = {
            "namespace": namespace,
            "id": convoset_id,
            "config": {
                "namespace": namespace,
                "sources": [
                    {
                        "userUpload": {}
                    }
                ]
            }
        }

        headers = self._get_headers()

        effective_timeout = timeout if timeout is not None else self.timeout

        url = f"{self.base_url}/{self.api_version}/conversation_sets/{namespace}/{convoset_id}/config"
        response = requests.request(
            "PUT", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response=response, url=url)

    # *****************************************************************************************************************
    # Conversation Source - including add files
    # *****************************************************************************************************************

    # TODO: Reference conversation set id using conversation source id
    #       Currently create_conversation_set method returns only conversation_source_id
    #       Implemented a method which returns both convoset and convosrc ids
    #       Meanwhile people who implemented create_conversation_set, need this todo to help them get the convoset id,
    #       which then can be used to delete the set.
    def get_conversation_source(self, namespace: str, conversation_source_id: str, timeout: float = None) -> dict:
        '''Download conversation set'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        # /{self.api_version}/files/{namespace}/{conversation_source_id}/export
        url = f'{self.base_url}/{self.api_version}/files/{namespace}/{conversation_source_id}/export'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "playbooks")

    def upload_json_file_to_conversation_source(self, namespace: str,
                                                conversation_source_id: str,
                                                upload_name: str,
                                                fqfp: str,
                                                timeout: float = None,
                                                no_trigger: bool = False) -> dict:
        '''Upload a JSON file to a conversation source
        no_trigger=True prevents indexes from building if passed in case you want to delete
        or upload additional files before triggering them.  If you use this you must 
        upload or delete a final file with no_trigger=False (the default) otherwise the new data in 
        your conversation set will not be available to other processes.'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        url = f"{self.base_url}/{self.api_version}/files/{namespace}/{conversation_source_id}"

        # file_in = open(fqfp,mode="r",encoding="utf8")
        # json.load(file_in)
        # file_in.close()
        upload_file = open(fqfp, 'rb')
        if no_trigger:
            str_no_trigger = "true"
        else:
            str_no_trigger = "false"
        payload = requests_toolbelt.multipart.encoder.MultipartEncoder(
        fields={
            'format': 'IMPORT_FORMAT_HUMANFIRST_JSON',
            'no_trigger': str_no_trigger, 
            # seem to remember there is a problem with encoding multiple fields in the toolbelt multipart encoder but this seems effective during testing
            # if I remember correctly this is present where the values are subobjects, but this is top level so seems OK?
            'file': (upload_name, upload_file, 'application/json')}
        )
        # This is the magic bit - you must set the content type to include the boundary information
        # multipart encoder makes working these out easier
        headers["Content-Type"] = payload.content_type

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=effective_timeout)
        upload_file.close()
        return self._validate_response(response, url, "playbooks")

    # *****************************************************************************************************************
    # Querying Processed Conversation set data
    # *****************************************************************************************************************

    def query_conversation_set(
            self,
            namespace: str,
            workspace: str,
            search_text: str = "",
            page_size: int = 10,
            convsetsource: str = "",
            next_page_token: str = "",
            start_isodate: str = '1970-01-01T00:00:00Z',
            end_isodate: str = '2049-12-31T23:59:59Z',
            timeout: float = None
            ) -> dict:
        '''This will seach a converation set for converations and return
        the examples threaded along with their data like entropy, margin
        the nearest neighbour weights, the classifications and original
        inputs - on ABCD 20 conversations returns about 28k rows formatted'''
        predicates = []
        if search_text and search_text != '':
            predicates.append({"inputMatch": {"text": search_text}})
        if start_isodate and end_isodate and start_isodate != '' and end_isodate != '':
            predicates.append(
                {
                    "timeRange": {
                        "start": start_isodate,
                        "end": end_isodate
                    }
                }
            )
        predicates.append({"conversation_type": {"type": 0}})
        if convsetsource and convsetsource != "":
            predicates.append(
                {"conversationSet": {"conversationSetIds": [convsetsource]}})
        if next_page_token and next_page_token != "":
            predicates.append({"PageTokenData":{"PageToken":next_page_token}})

        if len(predicates) == 0:
            raise HFAPIParameterException(
                "Must have either text or start and end date predicates." +
                f"search_text: {search_text} start_isodate: {start_isodate} end_isodate: {end_isodate}")

        payload = {
            "predicates": predicates,
            "pageSize": page_size
        }
        # TODO: this gives an error if passed - proto doesn't like PageTokenData\
        # if next_page_token and next_page_token != "":
        #     payload["page_token"] = next_page_token

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/conversations/{namespace}/{workspace}/query'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def export_query_conversation_inputs(
            self,
            namespace: str,
            playbook_id: str,
            pipeline_id: str = "",
            pipeline_step_id: str = "",
            exists_filter_key_name: str = "",
            metadata_predicate: list[dict] = None,
            download_format: int = 1, # 1 = JSON 2 = CSV
            prompt_id: str = "",
            generation_run_id: str = "",
            order_by: int = 1,
            order_direction_asc: bool = True,
            dedup_by_hash: bool = False,
            dedup_by_convo: bool = False,
            exclude_phrase_objects: bool = True, # TODO: unclear why this is set
            source_kind: int = 2, # DEFAULT TO GENERATED
            timeout: float = None
            ) -> dict:
        '''Returns the generated data as as JSON or a as a
        CSV text file
        
        By default waits for the new index to be available if
        one is being downloaded at the moment it is called

        source_kind
        SOURCE_KIND_UNSPECIFIED = 0;
        SOURCE_KIND_UNLABELED = 1;
        SOURCE_KIND_GENERATED = 2;

        metadata_predicate
        [
            {
                "key": "INSERT_KEY_NAME",
                "operator": "EQUALS|NOT_EQUALS|CONTAINS|NOT_CONTAINS|KEY_EXISTS|KEY_NOT_EXISTS|KEY_MATCHES|ANY",
                "value": "VALUE|''"
            },
            #other filters..
        ]
        '''


        if metadata_predicate is None:
            metadata_predicate = []

        # operator 0 EQUALS filter types
        metadata_keys = [
            "pipelineId",
            "pipelineStepId",
            "promptId",
            "generationRunId",
        ]
        metadata_values = [
            pipeline_id,
            pipeline_step_id,
            prompt_id,
            generation_run_id
        ]
        metadata_filters = []
        for i,_ in enumerate(metadata_keys):
            if metadata_values[i] != "":
                metadata_filters.append({
                    "key": metadata_keys[i],
                    "operator": 0, # EQUALS
                    "value": metadata_values[i]
                })
        # operator 4 exists -- older implementation
        if exists_filter_key_name != "":
            exists_filter = {
                "key": exists_filter_key_name,
                "operator": 4, # EXISTS
                "optional": False,
                "value": ""
            }
            metadata_filters.append(exists_filter)

        #Condition dict for filtering
        condition_dict = {
                "EQUALS": 0,
                "NOT_EQUALS": 1,
                "CONTAINS": 2,
                "NOT_CONTAINS": 3,
                "KEY_EXISTS": 4,
                "KEY_NOT_EXISTS": 5,
                "KEY_MATCHES": 6,
                "ANY": 7
        }

        #Map the metadata filters passed in via object
        if len(metadata_predicate) > 0:
            for _, metadata_field in enumerate(metadata_predicate):

                try:
                    #Find matching numerical operator
                    numerical_operator = condition_dict[metadata_field["operator"]]
                except Exception as _:
                    logging.error("Invalid operator %s. Please choose from: "
                            "EQUALS, NOT_EQUALS, CONTAINS, NOT_CONTAINS, "
                            "KEY_EXISTS, KEY_NOT_EXISTS, KEY_MATCHES, ANY", metadata_field['operator'])
                    raise

                #Support for OR query
                if metadata_field.get("optional"):
                    metadata_filters.append({
                        "key": metadata_field['key'],
                        "operator": numerical_operator,
                        "value": metadata_field['value'],
                        "optional": metadata_field['optional'],
                    })
                else:
                    metadata_filters.append({
                        "key": metadata_field['key'],
                        "operator": numerical_operator,
                        "value": metadata_field['value']
                    })


        if order_direction_asc:
            order_direction = 1
        else:
            order_direction = 2
        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
            "input_predicates": [
                {
                    "source": {
                        "source": 1 # TODO: UNKNOWN CURRENTLY
                    }
                },
                {
                    "metadata":{
                        "conditions": metadata_filters
                    }
                },
                {
                    "deduping": {
                        "by_hash": dedup_by_hash,
                        "by_conversation": dedup_by_convo
                    }
                },
                {
                    "trainingPhrase":
                        {
                            "excludePhraseObjects": exclude_phrase_objects
                        }
                }
            ],
            "format": download_format,
            "conversation_predicates": [
                {
                    "conversation_source": {
                        "source_kind": source_kind
                    }
                }
            ],
            "order_by_value": {
                "value": order_by
            },
            "order_direction": order_direction
        }

        headers = self._get_headers()

        base_url = f'{self.base_url}/'
        args_url = f'{self.api_version}/conversations/query/inputs/export'
        url = f'{base_url}{args_url}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        res = self._validate_response(response, url)
        downloadable_url = f'{self.base_url}{res["exportUrlPath"]}'
        return self._download_file_from_url(downloadable_url, download_format)

    def _download_file_from_url(self, url: str, download_format: int, timeout: float = None) -> dict:
        """Download file from url"""
        headers = self._get_headers()

        effective_timeout = timeout if timeout is not None else self.timeout

        downloaded_json = requests.request("GET", url, headers=headers, timeout=effective_timeout)
        if download_format == 1: #JSON
            return downloaded_json.json()
        elif download_format == 2: #CSV
            return downloaded_json.text
        else:
            raise RuntimeError(f'Unrecognised download format: {download_format}')




    # *****************************************************************************************************************
    # Integrations
    # *****************************************************************************************************************

    def get_integrations(self, namespace: str, timeout: float = None):
        '''Returns all the integrations configured for a namespace'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/integrations/{namespace}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "integrations")

    def get_integration_workspaces(self, namespace: str, integration_id: str, timeout: float = None):
        '''Get the integration workspaces for an integration
        i.e call the integration in HF to detect in the integrated NLU
        what target/source workspaces there are.
        i.e in DF case find out what agents there are to import data from'''
        payload = {
            "namespace": namespace,
            "integration_id":integration_id
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/integration_workspaces/{namespace}/{integration_id}/workspaces'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "workspaces")

    def trigger_import_from_df_cx_integration(
            self,
            namespace: str,
            playbook: str,
            integration_id: str,
            integration_workspace_id: str,
            project: str,
            region: str,
            integration_language: str,
            bidirectional_merge: bool = False,
            hierarchical_intent_name_disabled: bool = True,
            hierarchical_delimiter: str = '--',
            zip_encoding: bool = False,
            gzip_encoding: bool = False,
            include_negative_phrases: bool = False,
            skip_empty_intents: bool = True,
            clear_intents: bool = False,
            clear_entities: bool = False,
            clear_tags: bool = False,
            merge_intents: bool = False,
            merge_entities: bool = False,
            merge_tags: bool = False,
            extra_intent_tags: list = None,
            extra_phrase_tags: list = None,
            timeout: float = None
        ):
        '''Triggers import of the wrokspace from the selected integration'''
        if extra_intent_tags is None:
            extra_intent_tags = []
        if extra_phrase_tags is None:
            extra_phrase_tags = []

        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "integration_id": integration_id,
            "integration_workspace_id": integration_workspace_id,
            "integration_location": {
                "project": project,
                "region": region
            },
            "bidirectional_merge": bidirectional_merge,
            "intent_options": {
                "hierarchical_intent_name_disabled": hierarchical_intent_name_disabled,
                "hierarchical_delimiter": hierarchical_delimiter,
                "zip_encoding": zip_encoding,
                "gzip_encoding": gzip_encoding,
                "include_negative_phrases": include_negative_phrases,
                "skip_empty_intents": skip_empty_intents
            },
            "import_options": {
                "clear_intents": clear_intents,
                "clear_entities": clear_entities,
                "clear_tags": clear_tags,
                "merge_intents": merge_intents,
                "merge_entities": merge_entities,
                "merge_tags": merge_tags,
                "extra_intent_tags": extra_intent_tags,
                "extra_phrase_tags": extra_phrase_tags
            },
            "integration_language": integration_language
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/integration_workspaces/{namespace}/{integration_id}/workspaces/{integration_workspace_id}/import' # pylint: disable=line-too-long

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload),timeout=effective_timeout)
        return self._validate_response(response, url)


    # *****************************************************************************************************************
    # Evaluations
    # *****************************************************************************************************************

    def get_evaluation_presets(self, namespace: str, playbook: str, timeout: float = None):
        '''Get the presets to find the evaluation_preset_id to run an evaluation'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/playbooks/{namespace}/{playbook}/presets'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, "presets")

    def trigger_preset_evaluation(
                self,
                namespace: str,
                playbook: str,
                evaluation_preset_id: str,
                name: str = '',
                timeout: float = None):
        '''Start an evaluation based on a preset'''
        if name == '':
            name = f'API triggered: {datetime.datetime.now()}'
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "params": {
                "evaluation_preset_id": evaluation_preset_id
            },
            "name": name
        }

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/workspaces/{namespace}/{playbook}/evaluations'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def get_evaluation_report(self, namespace: str, playbook: str, evaluation_id: str, timeout: float = None) -> dict:
        '''Get the evaluation report as zip'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "evaluation_id": evaluation_id
        }

        headers = self._get_headers()

        base_url = f'{self.base_url}/{self.api_version}/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations/{evaluation_id}/report.zip'
        url = f'{base_url}{args_url}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)

        return self._validate_response(response=response, url=url, wantzip=True)

    def get_evaluation_summary(self, namespace: str, playbook: str, evaluation_id: str, timeout: float = None) -> dict:
        '''Get the evaluation summary as json'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "evaluation_id": evaluation_id
        }

        headers = self._get_headers()

        base_url = f'{self.base_url}/{self.api_version}/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations/{evaluation_id}'
        url = f'{base_url}{args_url}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)

        return self._validate_response(response=response,url=url)

    def list_evaluations(self, namespace: str, playbook: str, timeout: float = None) -> dict:
        '''List all evaluations in the given playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        base_url = f'{self.base_url}/{self.api_version}/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations'
        url = f'{base_url}{args_url}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)

        return self._validate_response(response=response,url=url)

    def get_intent_results(self,
                           namespace: str,
                           playbook: str,
                           evaluation_id: str,
                           intent_id: str,
                           timeout: float = None) -> dict:
        '''Get a list of training phrases that were evaluated'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "evaluation_id": evaluation_id,
            "intent_id": intent_id
        }

        headers = self._get_headers()

        base_url = f'{self.base_url}/{self.api_version}/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations/{evaluation_id}/{intent_id}'
        url = f'{base_url}{args_url}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)

        return self._validate_response(response=response,url=url)


    # *****************************************************************************************************************
    # Subscriptions
    # *****************************************************************************************************************

    def get_plan(self, timeout: float = None):
        '''Get the plan for a subscription'''
        payload = {}

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/subscriptions/plan'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def get_usage(self, timeout: float = None):
        '''Get the usage for a subscription'''
        payload = {}

        headers = self._get_headers()

        url = f'{self.base_url}/{self.api_version}/subscriptions/usage'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    # *****************************************************************************************************************
    # Pipeline
    # *****************************************************************************************************************

    def describe_trigger(self, namespace: str, trigger_id: str, timeout: float = None):
        """Describe Trigger"""
        payload = {
            "namespace": namespace,
            "trigger_id": trigger_id
        }

        headers = self._get_headers()
        url = f'{self.base_url}/{self.api_version}/triggers/{namespace}/{trigger_id}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def trigger_playbook_pipeline(self,
                                  namespace: str,
                                  playbook_id: str,
                                  pipeline_id: str,
                                  timeout: float = None) -> dict:
        '''Triggers a pipeline'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
            "pipeline_id": pipeline_id
        }

        headers = self._get_headers()
        base_url = f'{self.base_url}/{self.api_version}/playbooks'
        args_url = f"/{namespace}/{playbook_id}/pipelines/{pipeline_id}:trigger"
        url = f'{base_url}{args_url}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url)

    def list_playbook_pipelines(self,
                                namespace: str,
                                playbook_id: str,
                                timeout: float = None) -> dict:
        '''List pipelines for a playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
        }

        headers = self._get_headers()
        base_url = f'{self.base_url}/{self.api_version}/playbooks'
        args_url = f"/{namespace}/{playbook_id}/pipelines"
        url = f'{base_url}{args_url}'

        effective_timeout = timeout if timeout is not None else self.timeout

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=effective_timeout)
        return self._validate_response(response, url, field="pipelines")
