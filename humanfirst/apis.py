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

# third party imports
import requests
import requests_toolbelt
from dotenv import load_dotenv, find_dotenv

# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

# CONSTANTS
constants = ConfigParser()
path_to_config_file = os.path.join(here,'config','setup.cfg')
constants.read(path_to_config_file)

# constants need type conversion from str to int
TIMEOUT = int(constants.get("humanfirst.CONSTANTS","TIMEOUT"))
EXPIRY_ADDITION = int(constants.get("humanfirst.CONSTANTS","EXPIRY_ADDITION"))
VALID = constants.get("humanfirst.CONSTANTS","VALID")
REFRESHING = constants.get("humanfirst.CONSTANTS","REFRESHING")
EXPIRED = constants.get("humanfirst.CONSTANTS","EXPIRED")

# locate where we are
path_to_log_config_file = os.path.join(here,'config','logging.conf')

# Load logging configuration
logging.config.fileConfig(path_to_log_config_file)

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

class HFAPIAuthException(Exception):
    """When authorization validation fails"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class HFCredentialNotAvailableException(Exception):
    """When username/password not provided by the user"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# ******************************************************************************************************************120
# API class containing API call methods
# *********************************************************************************************************************

class HFAPI:
    """HumanFirst API"""

    bearer_token: dict

    def __init__(self, username: str = "", password: str = ""):
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

        if username == "":
            # this automatically checks if the environment variable is available in CLI first
            # and then checks the .env varaiables
            username = os.environ.get("HF_USERNAME")
            if username is None:
                raise HFCredentialNotAvailableException("HF_USERNAME is not set as environment variable")

        if password == "":
            # this automatically checks if the environment variable is available in CLI first
            # and then checks the .env varaiables
            password = os.environ.get("HF_PASSWORD")
            if password is None:
                raise HFCredentialNotAvailableException("HF_PASSWORD is not set as environment variable")

        self.bearer_token = {
            "bearer_token": "",
            "refresh_token": "",
            "expires_in": 3600,
            "datetime": datetime.datetime.now(),
            "status": EXPIRED
        }
        auth_response = self._authorize(username=username, password=password)
        self.bearer_token = {
            "bearer_token": auth_response["idToken"],
            "refresh_token": auth_response["refreshToken"],
            "expires_in": int(auth_response["expiresIn"]),
            "datetime": datetime.datetime.now(),
            "status": VALID
        }

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
            candidate = response.json()
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

    def get_tags(self, namespace: str, playbook: str) -> dict:
        '''Returns tags'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/tags'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "tags")

    def delete_tag(self, namespace: str, playbook: str, tag_id: str) -> dict:
        '''Returns tags'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "tag_id": tag_id
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/tags/{tag_id}'
        response = requests.request(
            "DELETE", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def create_tag(self, namespace: str, playbook: str,
                tag_id: str, tag_name: str, tag_color: str) -> dict:
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/tags'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    # *****************************************************************************************************************
    # Playbooks/Workspaces
    # *****************************************************************************************************************

    def create_playbook(self, namespace: str, playbook_name: str) -> dict:
        '''
        Creates a playbook in the given namespace

        If the playbook name already exists, that playbook gets deleted and a new one is creates
        '''
        payload = {
            "namespace": namespace,
            "playbook_name": playbook_name,
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "playbooks")

    def list_playbooks(self, namespace: str) -> dict:
        '''Returns list of all playbooks for an organisation
        Note namepsace parameter doesn't appear to provide filtering'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "playbooks")

    def post_playbook(self, namespace: str, name: str) -> dict:
        '''Create a playbook'''
        payload = {
            "namespace": namespace, # namespace of the playbook in the pipeline metastore
            "playbook_name": name # not currently honored - fix under way
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def get_playbook_info(self, namespace: str, playbook: str) -> dict:
        '''Returns metadata of playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/playbooks/{namespace}/{playbook}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def get_playbook(self,
                    namespace: str,
                    playbook: str,
                    hierarchical_delimiter="-",
                    hierarchical_intent_name_disabled: bool = True,
                    zip_encoding: bool = False,
                    include_negative_phrases: bool = False
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/intents/export'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        response = self._validate_response(response, url, "data")
        response = base64.b64decode(response)
        response = response.decode('utf-8')
        response_dict = json.loads(response)
        return response_dict

    def delete_playbook(self, namespace: str, playbook_id: str, hard_delete: bool = False) -> dict:
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook_id}'
        response = requests.request(
            "DELETE", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "playbooks")

    # *****************************************************************************************************************
    # Intents
    # *****************************************************************************************************************

    def get_intents(self, namespace: str, playbook: str) -> dict:
        '''Get all the intents in a workspace'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/intents'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "intents")


    def get_intent(self, namespace: str, playbook: str, intent_id: str) -> dict:
        '''Get the metdata for the intent needed'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/intents/{intent_id}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)


    def get_revisions(self, namespace: str, playbook: str,) -> dict:
        '''Get revisions for the namespace and playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/revisions'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "revisions")

    def update_intent(self, namespace: str, playbook: str, intent: dict, update_mask: str) -> dict:
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/intents'
        response = requests.request(
            "PUT", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
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
            override_name: bool = True
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/intents/import'
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=TIMEOUT)
        return self._validate_response(response, url)

    def import_intents_http(
            self,
            namespace: str, playbook: str,
            workspace_file_path: str, # or union HFWorkspace
            # format_int: int = 7,
            hierarchical_intent_name_disabled: bool = True,
            hierarchical_delimiter: str = "/"
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/intents/import_http'
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=TIMEOUT)
        return self._validate_response(response, url)


    # *****************************************************************************************************************
    # Call NLU engines
    # *****************************************************************************************************************

    def get_models(self, namespace: str) -> dict:
        '''Get available models for a namespace
        NOTE: THIS IS NOT nlu-id!'''
        payload = {}

        headers = self._get_headers()

        url = 'https://api.humanfirst.ai/v1alpha1/models'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        models = self._validate_response(response, url, "models")
        namespace_models = []
        for model in models:
            if model["namespace"] == namespace:
                namespace_models.append(model)
        return namespace_models


    def get_nlu_engines(self, namespace: str, playbook: str) -> dict:
        '''Get nlu engines for the for the namespace and playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/playbooks/{namespace}/{playbook}/nlu_engines'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "nluEngines")


    def get_nlu_engine(self, namespace: str, playbook: str, nlu_id: str) -> dict:
        '''Get nlu engine for the for the namespace and playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "nlu_id": nlu_id
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/playbooks/{namespace}/{playbook}/nlu_engines/{nlu_id}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def list_trained_nlu(self, namespace: str, playbook: str) -> dict:
        '''Get trained run ids for the playbook, then will have to filter by the nlu_engine interested in'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/nlu'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, field="runs")


    def trigger_train_nlu(self, namespace: str, playbook: str, nlu_id: str,
                        force_train: bool = True, skip_train: bool= False,
                        force_infer: bool = False, skip_infer: bool = True,
                        auto: bool = False) -> dict:
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/nlu:train'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)

        return self._validate_response(response, url)


    def predict(self, sentence: str, namespace: str, playbook: str,
                model_id: str = None, revision_id: str = None) -> dict:
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
                raise HFAPIAuthException(
                    "If either specified both model_id and revision_id are required")

        if model_id:
            payload["model_id"] = model_id
        if revision_id:
            payload["revision_id"] = model_id

        url = f'https://api.humanfirst.ai/v1alpha1/nlu/predict/{namespace}/{playbook}'

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)


    def batchPredict(self, sentences: list, 
                     namespace: str, 
                     playbook: str,
                     timeout: int = TIMEOUT) -> dict:  # pylint: disable=invalid-name
        '''Get response_dict of matches and hier matches for a batch of sentences
        TODO: model version changes'''
        payload = {
            "namespace": "string",
            "playbook_id": "string",
            "input_utterances": sentences
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/nlu/predict/{namespace}/{playbook}/batch'

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=timeout)
        return self._validate_response(response, url, "predictions")

    # *****************************************************************************************************************
    # Coverage
    # *****************************************************************************************************************

    def get_intents_coverage_request(self,
                                     namespace: str,
                                     playbook: str,
                                     data_selection: int = 1,
                                     model_id: str = None):
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/coverage/latest'

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "report")

    def export_intents_coverage(self,
                                namespace: str,
                                playbook: str,
                                model_id: str = None,
                                confidence_threshold: int = 70, # This is the default in the GUI
                                coverage_type: int = 1, # COVERAGE_TYPE_TOTAL
                                data_selection: int = 1 # DATA_TYPE_ALL
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

        print(payload)

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/coverage/latest/export'
        params0 = f'?namespace={namespace}&playbook={playbook}&confidence_threshold={confidence_threshold}'
        params1 = f'&coverage_type={coverage_type}&data_selection={data_selection}'
        url = url + params0 + params1

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, wantcsv=True)


    # *****************************************************************************************************************
    # Authorisation
    # *****************************************************************************************************************

    def  _get_headers(self) -> dict:
        """Produce the necessary header"""

        now = datetime.datetime.now()
        time_diff = now - self.bearer_token["datetime"]

        assert isinstance(time_diff, datetime.timedelta)

        logger.info("Current time: %s",now)
        logger.info('Token Creation time: %s',self.bearer_token["datetime"])
        logger.info("Time Difference: %s",time_diff)
        logger.info('Token status: %s',self.bearer_token["status"])
        time_diff = time_diff.seconds + EXPIRY_ADDITION

        # adding 60 sec to the time difference to check if ample amount of time is left for using the token
        if time_diff >= self.bearer_token["expires_in"] and self.bearer_token["status"] == VALID:
            logger.info("Refreshing Token")
            self.bearer_token["status"] = REFRESHING
            refresh_response = self._refresh_bearer_token()
            self.bearer_token = {
                "bearer_token": refresh_response["id_token"],
                "refresh_token": refresh_response["refresh_token"],
                "expires_in": int(refresh_response["expires_in"]),
                "datetime": datetime.datetime.now(),
                "status": VALID
            }

        if self.bearer_token["status"] == REFRESHING or self.bearer_token["status"] == EXPIRED:
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json'
            }
        if self.bearer_token["status"] == VALID:
            bearer_string = f'Bearer {self.bearer_token["bearer_token"]}'
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json',
                'Authorization': bearer_string
            }

        return headers


    def _authorize(self, username: str, password: str) -> dict:
        '''Get bearer token for a username and password'''

        key = 'AIzaSyA5xZ7WCkI6X1Q2yzWHUrc70OXH5iCp7-c'
        base_url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key='
        auth_url = f'{base_url}{key}'

        headers = self._get_headers()

        auth_body = {
            "email": username,
            "password": password,
            "returnSecureToken": True
        }

        auth_response = requests.request(
            "POST", auth_url, headers=headers, data=json.dumps(auth_body), timeout=TIMEOUT)
        if auth_response.status_code != 200:
            raise HFAPIAuthException(
                f'Not authorised, google returned {auth_response.status_code} {auth_response.json()}')
        return auth_response.json()

    def _refresh_bearer_token(self):
        """refreshes bearer token"""

        key = 'AIzaSyA5xZ7WCkI6X1Q2yzWHUrc70OXH5iCp7-c'
        base_url = 'https://securetoken.googleapis.com/v1/token?key='
        auth_url = f'{base_url}{key}'

        headers = self._get_headers()

        auth_body = {
            "refresh_token": self.bearer_token["refresh_token"],
            "grant_type": "refresh_token"
        }
        auth_response = requests.request(
            "POST", auth_url, headers=headers, data=json.dumps(auth_body), timeout=TIMEOUT)
        if auth_response.status_code != 200:
            raise HFAPIAuthException(
                f'Not authorised, google returned {auth_response.status_code} {auth_response.json()}')
        return auth_response.json()

    # def process_auth(self, bearertoken: str = '', username: str = '', password: str = '') -> dict:
    #     '''Validate which authorisation method using and return the headers'''

    #     if bearertoken == '':
    #         for arg in ['username', 'password']:
    #             if arg == '':
    #                 raise HFAPIAuthException(
    #                     'If bearer token not provided, must provide username and password')
    #         return self._authorize(username, password)
    #     else:
    #         return self._get_headers()

    # *****************************************************************************************************************
    # Conversation sets
    # *****************************************************************************************************************

    def get_conversation_set_list(self, namespace: str) -> tuple:
        """Get all the conversation sets and their info for a namespaces"""

        payload = {}

        headers = self._get_headers()

        url = f"https://api.humanfirst.ai/v1alpha1/conversation_sets?namespace={namespace}"
        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=TIMEOUT)
        conversation_sets = self._validate_response(response=response,url=url,field='conversationSets')

        # make it a list looking up each individual one
        conversation_set_list = []
        for conversation_set in conversation_sets:
            conversation_set_id = conversation_set['id']

            url = f"https://api.humanfirst.ai/v1alpha1/conversation_sets/{namespace}/{conversation_set_id}"
            response = requests.request(
                "GET", url, headers=headers, data=payload, timeout=TIMEOUT)
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

    def get_conversation_set(self, namespace: str, conversation_set_id: str) -> dict:
        """Get conversation set"""

        headers = self._get_headers()

        payload = {
            "namespace":namespace,
            "conversation_set_id":conversation_set_id
        }
        url = f"https://api.humanfirst.ai/v1alpha1/conversation_sets/{namespace}/{conversation_set_id}"
        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=TIMEOUT)
        return self._validate_response(response=response,url=url)

    def create_conversation_set(self, namespace: str, convoset_name: str) -> dict:
        """Creates a conversation set. Returns conversation source ID"""

        payload = {
            "namespace": namespace,
            "conversation_set":{
                "name": convoset_name,
                "description": ""
            }
        }

        headers = self._get_headers()

        url = f"https://api.humanfirst.ai/v1alpha1/conversation_sets/{namespace}"
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
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

    # Not currently exposed - requested 2024-08-13
    # def delete_conversation_set(self, namespace: str, convoset_id: str) -> dict:
    #     """Deletes a conversation_set"""

    #     payload = {
    #         "namespace": namespace,
    #         "conversation_set":{
    #             "name": convoset_name,
    #             "description": ""
    #         }
    #     }

    #     headers = self._get_headers()

    #     url = f"https://api.humanfirst.ai/v1alpha1/conversation_sets/{namespace}/{convo_set_id}"
    #     response = requests.request(
    #         "DELETE", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
    #     return self._validate_response(response=response, url=url)

    def get_conversation_set_configuration(self, namespace: str, convoset_id: str) -> dict:
        """Gets conversation set configuration"""

        payload = {
            "namespace": namespace,
            "id": convoset_id
        }

        headers = self._get_headers()

        url = f"https://api.humanfirst.ai/v1alpha1/conversation_sets/{namespace}/{convoset_id}/config"
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response=response, url=url)

    def list_conversation_src_files(self, namespace: str, conversation_set_src_id: str) -> dict:
        """Get the list of conversation files within a convo set."""

        headers = self._get_headers()

        payload = {
            "namespace":namespace,
            "conversation_set_id":conversation_set_src_id
        }
        url = f"https://api.humanfirst.ai/v1alpha1/files/{namespace}/{conversation_set_src_id}"
        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=TIMEOUT)
        return self._validate_response(response=response,url=url,field="files")

    def delete_conversation_file(self, namespace:str,conversation_set_src_id: str,file_name:str):
        """Deletes a specific file within a convo set."""

        headers = self._get_headers()

        payload = {
            "namespace":namespace,
            "filename": file_name,
            "conversation_set_id":conversation_set_src_id
        }
        url = f"https://api.humanfirst.ai/v1alpha1/files/{namespace}/{conversation_set_src_id}/{file_name}"


        response = requests.request(
            "DELETE", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response=response,url=url)

    def update_conversation_set_configuration(self, namespace: str, convoset_id: str) -> dict:
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

        url = f"https://api.humanfirst.ai/v1alpha1/conversation_sets/{namespace}/{convoset_id}/config"
        response = requests.request(
            "PUT", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response=response, url=url)

    # *****************************************************************************************************************
    # Conversation Source - including add files
    # *****************************************************************************************************************

    def get_conversation_source(self, namespace: str, conversation_source_id: str) -> dict:
        '''Download conversation set'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        # /v1alpha1/files/{namespace}/{conversation_source_id}/export
        url = f'https://api.humanfirst.ai/v1alpha1/files/{namespace}/{conversation_source_id}/export'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "playbooks")

    def upload_json_file_to_conversation_source(self, namespace: str,
                                                conversation_source_id: str,
                                                upload_name: str,
                                                fqfp: str) -> dict:
        '''Upload a JSON file to a conversation source'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        url = f"https://api.humanfirst.ai/v1alpha1/files/{namespace}/{conversation_source_id}"

        # file_in = open(fqfp,mode="r",encoding="utf8")
        # json.load(file_in)
        # file_in.close()
        upload_file = open(fqfp, 'rb')
        payload = requests_toolbelt.multipart.encoder.MultipartEncoder(
        fields={
            'format': 'IMPORT_FORMAT_HUMANFIRST_JSON',
            'file': (upload_name, upload_file, 'application/json')}
        )
        # This is the magic bit - you must set the content type to include the boundary information
        # multipart encoder makes working these out easier
        headers["Content-Type"] = payload.content_type
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=TIMEOUT)
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
            end_isodate: str = '2049-12-31T23:59:59Z'
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

        url = f'https://api.humanfirst.ai/v1alpha1/conversations/{namespace}/{workspace}/query'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def export_query_conversation_inputs(
            self,
            namespace: str,
            playbook_id: str,
            pipeline_id: str = "",
            pipeline_step_id: str = "",
            exists_filter_key_name: str = "",
            metadata_predicate: list[dict] = [],
            download_format: int = 1, # 1 = JSON 2 = CSV
            prompt_id: str = "",
            generation_run_id: str = "",
            order_by: int = 1,
            order_direction_asc: bool = True,
            dedup_by_hash: bool = False,
            dedup_by_convo: bool = False,
            exclude_phrase_objects: bool = True, # TODO: unclear why this is set
            source_kind: int = 2 # DEFAULT TO GENERATED
            ) -> dict:
        '''Returns the generated data as as JSON or a as a
        CSV text file

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
            for index, metadata_field in enumerate(metadata_predicate):

                try:
                    #Find matching numerical operator
                    numerical_operator = condition_dict[metadata_field["operator"]]
                except Exception as e:
                    raise ValueError(f"Invalid operator '{metadata_field['operator']}'. Please choose from: "
                            "EQUALS, NOT_EQUALS, CONTAINS, NOT_CONTAINS, "
                            "KEY_EXISTS, KEY_NOT_EXISTS, KEY_MATCHES, ANY")

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

        base_url = 'https://api.humanfirst.ai/'
        args_url = 'v1alpha1/conversations/query/inputs/export'
        url = f'{base_url}{args_url}'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        res = self._validate_response(response, url)
        downloadable_url = f'https://api.humanfirst.ai{res["exportUrlPath"]}'
        return self._download_file_from_url(downloadable_url, download_format)

    def _download_file_from_url(self, url: str, download_format: int) -> dict:
        """Download file from url"""
        headers = self._get_headers()
        downloaded_json = requests.request("GET", url, headers=headers, timeout=TIMEOUT)
        if download_format == 1: #JSON
            return downloaded_json.json()
        elif download_format == 2: #CSV
            return downloaded_json.text
        else:
            raise RuntimeError(f'Unrecognised download format: {download_format}')




    # *****************************************************************************************************************
    # Integrations
    # *****************************************************************************************************************

    def get_integrations(self, namespace: str):
        '''Returns all the integrations configured for a namespace'''
        payload = {
            "namespace": namespace
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/integrations/{namespace}'

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "integrations")

    def get_integration_workspaces(self, namespace: str, integration_id: str):
        '''Get the integration workspaces for an integration
        i.e call the integration in HF to detect in the integrated NLU
        what target/source workspaces there are.
        i.e in DF case find out what agents there are to import data from'''
        payload = {
            "namespace": namespace,
            "integration_id":integration_id
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/integration_workspaces/{namespace}/{integration_id}/workspaces'

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
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
            extra_phrase_tags: list = None
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

        url = f'https://api.humanfirst.ai/v1alpha1/integration_workspaces/{namespace}/{integration_id}/workspaces/{integration_workspace_id}/import' # pylint: disable=line-too-long

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload),timeout=TIMEOUT)
        return self._validate_response(response, url)


    # *****************************************************************************************************************
    # Evaluations
    # *****************************************************************************************************************

    def get_evaluation_presets(self, namespace: str, playbook: str):
        '''Get the presets to find the evaluation_preset_id to run an evaluation'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        url = f'https://api.humanfirst.ai/v1alpha1/playbooks/{namespace}/{playbook}/presets'

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, "presets")

    def trigger_preset_evaluation(
                self,
                namespace: str,
                playbook: str,
                evaluation_preset_id: str,
                name: str = ''):
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

        url = f'https://api.humanfirst.ai/v1alpha1/workspaces/{namespace}/{playbook}/evaluations'

        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def get_evaluation_report(self, namespace: str, playbook: str, evaluation_id: str) -> dict:
        '''Get the evaluation report as zip'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "evaluation_id": evaluation_id
        }

        headers = self._get_headers()

        base_url = 'https://api.humanfirst.ai/v1alpha1/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations/{evaluation_id}/report.zip'
        url = f'{base_url}{args_url}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)

        return self._validate_response(response=response, url=url, wantzip=True)

    def get_evaluation_summary(self, namespace: str, playbook: str, evaluation_id: str) -> dict:
        '''Get the evaluation summary as json'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "evaluation_id": evaluation_id
        }

        headers = self._get_headers()

        base_url = 'https://api.humanfirst.ai/v1alpha1/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations/{evaluation_id}'
        url = f'{base_url}{args_url}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)

        return self._validate_response(response=response,url=url)

    def list_evaluations(self, namespace: str, playbook: str) -> dict:
        '''List all evaluations in the given playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook
        }

        headers = self._get_headers()

        base_url = 'https://api.humanfirst.ai/v1alpha1/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations'
        url = f'{base_url}{args_url}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)

        return self._validate_response(response=response,url=url)

    def get_intent_results(self, namespace: str, playbook: str, evaluation_id: str, intent_id: str) -> dict:
        '''Get a list of training phrases that were evaluated'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook,
            "evaluation_id": evaluation_id,
            "intent_id": intent_id
        }

        headers = self._get_headers()

        base_url = 'https://api.humanfirst.ai/v1alpha1/workspaces'
        args_url = f'/{namespace}/{playbook}/evaluations/{evaluation_id}/{intent_id}'
        url = f'{base_url}{args_url}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)

        return self._validate_response(response=response,url=url)


    # *****************************************************************************************************************
    # Subscriptions
    # *****************************************************************************************************************

    def get_plan(self):
        '''Get the plan for a subscription'''
        payload = {}

        headers = self._get_headers()

        url = 'https://api.humanfirst.ai/v1alpha1/subscriptions/plan'

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def get_usage(self):
        '''Get the usage for a subscription'''
        payload = {}

        headers = self._get_headers()

        url = 'https://api.humanfirst.ai/v1alpha1/subscriptions/usage'

        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    # *****************************************************************************************************************
    # Pipeline
    # *****************************************************************************************************************

    def trigger_playbook_pipeline(self,
                                  namespace: str,
                                  playbook_id: str,
                                  pipeline_id: str) -> dict:
        '''Triggers a pipeline'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
            "pipeline_id": pipeline_id
        }

        headers = self._get_headers()
        base_url = 'https://api.humanfirst.ai/v1alpha1/playbooks'
        args_url = f"/{namespace}/{playbook_id}/pipelines/{pipeline_id}:trigger"
        url = f'{base_url}{args_url}'
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url)

    def list_playbook_pipelines(self,
                                namespace: str,
                                playbook_id: str) -> dict:
        '''List pipelines for a playbook'''
        payload = {
            "namespace": namespace,
            "playbook_id": playbook_id,
        }

        headers = self._get_headers()
        base_url = 'https://api.humanfirst.ai/v1alpha1/playbooks'
        args_url = f"/{namespace}/{playbook_id}/pipelines"
        url = f'{base_url}{args_url}'
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT)
        return self._validate_response(response, url, field="pipelines")
