"""
authorization.py

Manages HF authorization
"""
# *********************************************************************************************************************


# standard imports
import json
import time
import os
from configparser import ConfigParser
import logging
import logging.config
from datetime import datetime, timezone # pylint:disable=unused-import

# 3rd Party imports
import requests
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError
from jwt.algorithms import RSAAlgorithm
from dotenv import load_dotenv, find_dotenv


# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

# CONSTANTS
constants = ConfigParser()
path_to_config_file = os.path.join(here,'config','setup.cfg')
constants.read(path_to_config_file)

# Timeouts
TIMEOUT = int(constants.get("humanfirst.CONSTANTS","TIMEOUT"))

# Audiences
STAGING_AUDIENCE = constants.get("humanfirst.CONSTANTS","STAGING_AUDIENCE")
PROD_AUDIENCE = constants.get("humanfirst.CONSTANTS","PROD_AUDIENCE")
QA_AUDIENCE = constants.get("humanfirst.CONSTANTS","QA_AUDIENCE")
PRE_PROD_AUDIENCE = constants.get("humanfirst.CONSTANTS","PRE_PROD_AUDIENCE")
LOCAL_AUDIENCE = constants.get("humanfirst.CONSTANTS","LOCAL_AUDIENCE")
TEST_AUDIENCE = constants.get("humanfirst.CONSTANTS","TEST_AUDIENCE")

# Google serts
GOOGLE_CERTS_URL = constants.get("humanfirst.CONSTANTS","GOOGLE_CERTS_URL")

# API keys (which are validated by config call)
TEST_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","TEST_SIGN_IN_API_KEY")
PROD_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","PROD_SIGN_IN_API_KEY")
STAGING_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","STAGING_SIGN_IN_API_KEY")
QA_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","QA_SIGN_IN_API_KEY")
PRE_PROD_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","PRE_PROD_SIGN_IN_API_KEY")

# BASE_URL_TEST must be set by environment variable expected of the form BASE_URL_TEST=http://172.17.0.3:8888
BASE_URL_PROD = constants.get("humanfirst.CONSTANTS","BASE_URL_PROD")
BASE_URL_STAGING = constants.get("humanfirst.CONSTANTS","BASE_URL_STAGING")
BASE_URL_QA = constants.get("humanfirst.CONSTANTS","BASE_URL_QA")
BASE_URL_PRE_PROD = constants.get("humanfirst.CONSTANTS","BASE_URL_PRE_PROD")
BASE_URL_LOCAL = constants.get("humanfirst.CONSTANTS","BASE_URL_LOCAL")

# others
LOCAL_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","LOCAL_SIGN_IN_API_KEY")
TOKEN_REVALIDATE_WAIT_TIME = float(constants.get("humanfirst.CONSTANTS","TOKEN_REVALIDATE_WAIT_TIME"))

# token refresh
PREEMPTIVE_REFRESH_SECONDS_DEFAULT = int(constants.get("humanfirst.CONSTANTS","PREEMPTIVE_REFRESH_SECONDS_DEFAULT"))
HUMANFIRST_TOKEN_TTL_SECONDS = int(constants.get("humanfirst.CONSTANTS","HUMANFIRST_TOKEN_TTL_SECONDS"))

# locate where we are
path_to_log_config_file = os.path.join(here,'config','logging.conf')

# Get the current date and time
current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

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
logger = logging.getLogger('humanfirst.authorization')

class HFAPIAuthException(Exception):
    """When authorization validation fails"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class HFEnvironmentException(Exception):
    """When user provides an incorrect environment"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class HFCredentialNotAvailableException(Exception):
    """When username/password not provided by the user"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class Authorization:
    """HF Authorization"""

    bearer_token_dict: dict
    timeout: float
    audience: str
    identity_api_key: str

    def __init__(self, 
                 username: str = "",
                 password: str = "",
                 environment: str = "",
                 timeout: float = TIMEOUT,
                 min_expires_in_seconds: int = PREEMPTIVE_REFRESH_SECONDS_DEFAULT):
        """
        Initializes bearertoken
        
        min_expires_in_seconds can be overriden to ensure that each call there is at least a minimum amount
        of seconds before token expiry.
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

        if environment == "":
            # this automatically checks if the environment variable is available in CLI first
            # and then checks the .env varaiables
            environment = os.environ.get("HF_ENVIRONMENT")
            if environment is None:
                environment = "prod"

        # This case section sets the Key used to authenticate with the GCP key issuing server
        # and the URL of the humanfirst environment
        if environment == "prod":
            self.audience = PROD_AUDIENCE
            self.identity_api_key = PROD_SIGN_IN_API_KEY
            self.base_url = BASE_URL_PROD
        elif environment == "test":
            self.audience = TEST_AUDIENCE
            self.identity_api_key = TEST_SIGN_IN_API_KEY
            self.base_url = os.getenv("BASE_URL_TEST",None)
            if self.base_url == None:
                raise RuntimeError(f'If using test environment must provide BASE_URL_TEST to call as an env variable')
        elif environment == "staging":
            self.audience = STAGING_AUDIENCE
            self.identity_api_key = STAGING_SIGN_IN_API_KEY
            self.base_url = BASE_URL_STAGING
        elif environment == "qa":
            self.audience = QA_AUDIENCE
            self.identity_api_key = QA_SIGN_IN_API_KEY
            self.base_url = BASE_URL_QA
        elif environment == "pre_prod":
            self.audience = PRE_PROD_AUDIENCE
            self.identity_api_key = PRE_PROD_SIGN_IN_API_KEY
            self.base_url = BASE_URL_PRE_PROD
        elif environment == "local":
            self.audience = LOCAL_AUDIENCE
            self.identity_api_key = LOCAL_SIGN_IN_API_KEY
            self.base_url = BASE_URL_LOCAL
        else:
            raise HFEnvironmentException(
                "HF_ENVIRONMENT is not set to one of the following - prod, test, staging, qa, pre_prod")

        self.bearer_token_dict = {
            "token" : "",
            "refresh_token" : "",
            "decoded_token": {},
            "client_time": "",
            "environment": environment
        }
        
        self.min_expires_in_seconds = min_expires_in_seconds

        self.timeout = timeout
        
        self._validate_config()

        self._authorize(username=username,
                        password=password)

    def _validate_config(self):
        """Calls the config end point for that URL
        /v1alpha1/config/environment
        and checks whether the 
        values in the config file match what is there
        
        if environment=test tries to validate against
        staging assuming your test env is using staging
        authorisation
        """
        url = f'{self.base_url}/v1alpha1/config/environment'
        
        # this end point doesn't require authorisation 
        # as it provides the config for authorisation so unique headers
        payload = {}
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json'
        }
        response = requests.request(
            "GET", url, headers=headers, data=json.dumps(payload))
        if response.status_code != 200 and response.status_code != 201:
            raise RuntimeError(f'Couldn\'t verify config from: {url}')       
        cfg = response.json()
        
        # Previously these were all just stored locally so validating the local value against the API rather than just
        # taking from the API.
        logger.debug(cfg)
        if cfg["firebase"]["apiKey"] != self.identity_api_key:
            raise RuntimeError(f'cfg file provides: {self.identity_api_key} but config URL returns {cfg["firebase"]["apiKey"]}')
        
        # some environments may need a tennant id
        self.tenant_id = None
        if "firebase" in cfg:
            if "defaultTenantId" in cfg["firebase"]:
                self.tenant_id = cfg["firebase"]["defaultTenantId"]
        
        # if we have an audience in the config validate it against the config values
        if "firebase" in cfg:
            if "audience" in cfg["firebase"]:
                if self.audience != cfg["firebase"]["audience"]:
                    raise RuntimeError(f'Audience in cfg file: {self.audience} doesn\'t match api config: {cfg["firebase"]["audience"]}')

    def _authorize(self, 
                   username: str, 
                   password: str,
                   timeout: float = None) -> dict:
        '''Get bearer token for a username and password
        
        Premptively refresh the token is there is less than 
        max_expires_in_seconds left'''

        base_url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key='
        auth_url = f'{base_url}{self.identity_api_key}'

        headers = self._get_headers()

        auth_body = {
            "email": username,
            "password": password,
            "returnSecureToken": True
        }
        
        # If we have a tennant ID add it to the auth body
        if self.tenant_id:
            logger.info(f'tenantId: {self.tenant_id}')
            auth_body["tenantId"] = self.tenant_id
            
        effective_timeout = timeout if timeout is not None else self.timeout
        auth_response = requests.request(
            "POST", auth_url, headers=headers, data=json.dumps(auth_body), timeout=effective_timeout)

        if auth_response.status_code != 200:
            raise HFAPIAuthException(
                f'Not authorized, Google returned {auth_response.status_code} {auth_response.json()}')

        # Previously this was where there was a wait duration was used to allow for virualisation/internet clock drift
        # this is now handled by decoding the JWT token and allowing the inbuilt PyJWT Leeway functions on both
        # SDK and product side.  If you encounter "token used before issued" issues it is normally to do with some aspect
        # of internet deployment or virtualisation and clock drift.  Turn on DEBUG level logging to get full detailed
        # information of the internal token times to be able to resolve where the issue lies.

        self.bearer_token_dict["token"] = auth_response.json().get("idToken")
        self.bearer_token_dict["refresh_token"] = auth_response.json().get("refreshToken")
        
        # Now validate the JWT token
        if self.bearer_token_dict["token"]:
            self.validate_jwt()
        else:
            raise HFAPIAuthException("No ID Token received during initial authorization")
        return

    def _refresh_token(self, refresh_token: str, timeout: float = None) -> dict:
        '''Get a new ID token using the refresh token'''

        base_url = 'https://securetoken.googleapis.com/v1/token?key='
        refresh_url = f'{base_url}{self.identity_api_key}'

        headers = self._get_headers()

        refresh_body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        effective_timeout = timeout if timeout is not None else self.timeout
        refresh_response = requests.request(
            "POST", refresh_url, headers=headers, data=json.dumps(refresh_body), timeout=effective_timeout)

        if refresh_response.status_code != 200:
            raise HFAPIAuthException(
                f'Failed to refresh token, Google returned {refresh_response.status_code} {refresh_response.json()}')

        return refresh_response.json()

    def _get_headers(self):
        # Function to return headers for your request
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json'
        }
        return headers

    def validate_jwt(self, 
                     timeout: float = None) -> dict:
        """Validate the JWT token using Google's public keys"""

        # Get Google Public Keys for RS256 validation
        effective_timeout = timeout if timeout is not None else self.timeout
        try:
            response = requests.get(GOOGLE_CERTS_URL, timeout=effective_timeout)
            if response.status_code != 200:
                raise HFAPIAuthException(f"Failed to get Google public keys. Status code: {response.status_code}")

            google_public_keys = response.json()["keys"]

            # Since Google provides several keys, we need to use the one specified in the JWT header
            unverified_header = jwt.get_unverified_header(self.bearer_token_dict["token"])

            key_id = unverified_header.get("kid")


            if not key_id:
                raise HFAPIAuthException("Invalid token header. No key ID (kid) found.")

            # Find the key that matches the key ID from the token header
            public_key_data = None
            for key in google_public_keys:
                if key["kid"] == key_id:
                    public_key_data = key
                    break

            if not public_key_data:
                raise HFAPIAuthException("Invalid token header. No matching key found.")

            # Convert the public key data to an RSA public key
            public_key = RSAAlgorithm.from_jwk(json.dumps(public_key_data))

            # Decode the token using the public key
            refresh_attempts = 0
            validation_attempts = 0
            while True:
                # First case is where it decodes and is not expired in which case
                # we make an additional check how much time is left on the token
                try:
                    decoded_token = jwt.decode(
                        jwt=self.bearer_token_dict["token"],
                        key=public_key,
                        algorithms=["RS256"],
                        audience=self.audience,
                        issuer="https://securetoken.google.com/" + self.audience,
                        options={
                            "verify_signature": True,
                            "require":["exp", "iat"], # "nbf" is not provided by HF authentication
                            "verify_aud":True,
                            "verify_iss":True,
                            "verify_exp":True,
                            "verify_iat":True,
                            "strict_aud":True
                            },
                        leeway=5*60 # Leeway is set to 5 mins.
                        #  5 mins leeway is used in HF backend. Hence using the same here
                        # this helps in handling clock synchronization issues
                        )
                    self.bearer_token_dict["client_time"]  = int(time.time())

                    # Token is valid
                    logger.debug("Valid Token: %s", decoded_token)
                    
                    # The timestamp is in unix format -  convert unix to utc format
                    decoded_token_iat = datetime.fromtimestamp(decoded_token['iat'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    decoded_token_exp = datetime.fromtimestamp(decoded_token['exp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

                    # Extract the expiration time from the JWT token
                    self.bearer_token_dict["decoded_token"] = decoded_token

                    # Calculate the difference between current time and expiration time in Unix timestamp
                    time_diff = self.bearer_token_dict["client_time"] - self.bearer_token_dict["decoded_token"]["iat"]
                    
                    # Determine if want to pre-emptively refresh token
                    if (HUMANFIRST_TOKEN_TTL_SECONDS-time_diff) <= self.min_expires_in_seconds: 
                        logger.info(f"Pre-emptively refresh token at client_time: {decoded_token_iat} as seconds to expiry: {HUMANFIRST_TOKEN_TTL_SECONDS-time_diff} less than min: {self.min_expires_in_seconds} for expiry time {decoded_token_exp} ")
                        refresh_response = self._refresh_token(self.bearer_token_dict["refresh_token"])
                        self.bearer_token_dict["token"] = refresh_response.get("id_token")
                        self.bearer_token_dict["refresh_token"] = refresh_response.get("refresh_token")
                        if not self.bearer_token_dict["token"]:
                            logger.error("Failed to refresh the token. No new ID token received.")
                            time.sleep(TOKEN_REVALIDATE_WAIT_TIME)
                            # only need another attempt and continue if we didn't get the token pre-emptively refreshed
                            refresh_attempts = refresh_attempts + 1
                            continue
                        # refreshed the token
                        return
                    else:
                        logger.debug(f"Didn't refresh token as seconds to expiry: {HUMANFIRST_TOKEN_TTL_SECONDS-time_diff} > than min: {self.min_expires_in_seconds} client_time: {decoded_token_iat} expiry_time: {decoded_token_exp}")
                        
                    
                    # So we had a valid token and didn't need to refresh it
                    return

                # in the case the token has expired already.
                except ExpiredSignatureError:
                    if refresh_attempts >= 5:
                        logger.error("Refresh attempts exceeded 5 or more times")
                        raise
                    logger.info("The token has expired. Attempting to refresh token...")
                    refresh_response = self._refresh_token(self.bearer_token_dict["refresh_token"])
                    self.bearer_token_dict["token"] = refresh_response.get("id_token")
                    self.bearer_token_dict["refresh_token"] = refresh_response.get("refresh_token")
                    if not self.bearer_token_dict["token"]:
                        logger.error("Failed to refresh the token. No new ID token received.")
                        time.sleep(TOKEN_REVALIDATE_WAIT_TIME)
                    refresh_attempts = refresh_attempts + 1
                    continue
                
                # In the case that the token can't be decoded.
                except DecodeError:
                    logger.error("DecodeError failed to decode token")
                    raise
                
                # In the case 
                except InvalidTokenError as e:
                    logger.info("Token validation error: %s",str(e))
                    if validation_attempts >= 5:
                        logger.error("Validation attempts exceeded 5 or more times")
                        raise
                    logger.info(f"Validation attempt: {validation_attempts} validating again after a wait of: {TOKEN_REVALIDATE_WAIT_TIME}")
                    time.sleep(TOKEN_REVALIDATE_WAIT_TIME)
                    validation_attempts = validation_attempts + 1
                    continue
                
                # So token here is valid and decoded
        except requests.exceptions.RequestException as e:
            logger.error("An error occurred while retrieving Google's public keys: %s",str(e))
            raise

