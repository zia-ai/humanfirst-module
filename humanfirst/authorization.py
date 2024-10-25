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
from datetime import datetime, timezone # pylint:disable=unused-import

# 3rd Party imports
import requests
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError
from jwt.algorithms import RSAAlgorithm


# locate where we are
here = os.path.abspath(os.path.dirname(__file__))

# CONSTANTS
constants = ConfigParser()
path_to_config_file = os.path.join(here,'config','setup.cfg')
constants.read(path_to_config_file)

TIMEOUT = int(constants.get("humanfirst.CONSTANTS","TIMEOUT"))
STAGING_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","STAGING_SIGN_IN_API_KEY")
PROD_SIGN_IN_API_KEY = constants.get("humanfirst.CONSTANTS","PROD_SIGN_IN_API_KEY")
STAGING_AUDIENCE = "trial-184203"
PROD_AUDIENCE = "zia-firebase"
STAGING_PASSWORD = constants.get("humanfirst.CONSTANTS","STAGING_PASSWORD")
PROD_PASSWORD = constants.get("humanfirst.CONSTANTS","PROD_PASSWORD")
GOOGLE_CERTS_URL = constants.get("humanfirst.CONSTANTS","GOOGLE_CERTS_URL")
USERNAME = ""
PASSWORD = PROD_PASSWORD
SIGN_IN_API_KEY = PROD_SIGN_IN_API_KEY
AUDIENCE = PROD_AUDIENCE

class HFAPIAuthException(Exception):
    """When authorization validation fails"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class Authorization:
    """HF Authorization"""

    def authorize(self, username: str, password: str) -> dict:
        '''Get bearer token for a username and password'''

        base_url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key='
        auth_url = f'{base_url}{SIGN_IN_API_KEY}'

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
                f'Not authorized, Google returned {auth_response.status_code} {auth_response.json()}')

        # sleep for a 10th of a second to account for slight clock drifts with the GCP server
        time.sleep(0.01)
        return auth_response.json()

    def _refresh_token(self, refresh_token: str) -> dict:
        '''Get a new ID token using the refresh token'''

        base_url = 'https://securetoken.googleapis.com/v1/token?key='
        refresh_url = f'{base_url}{SIGN_IN_API_KEY}'

        headers = self._get_headers()

        refresh_body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        refresh_response = requests.request(
            "POST", refresh_url, headers=headers, data=json.dumps(refresh_body), timeout=TIMEOUT)

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

    def validate_jwt(self, token: str, refresh_token: str) -> dict:
        """Validate the JWT token using Google's public keys"""

        # Get Google Public Keys for RS256 validation
        try:
            response = requests.get(GOOGLE_CERTS_URL, timeout=TIMEOUT)
            if response.status_code != 200:
                raise HFAPIAuthException(f"Failed to get Google public keys. Status code: {response.status_code}")

            # print(response.json())

            google_public_keys = response.json()["keys"]

            # Since Google provides several keys, we need to use the one specified in the JWT header
            unverified_header = jwt.get_unverified_header(token)
            # print(unverified_header)
            key_id = unverified_header.get("kid")
            # print(key_id)

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
                try:
                    decoded_token = jwt.decode(
                        jwt=token,
                        key=public_key,
                        algorithms=["RS256"],
                        audience=AUDIENCE,
                        issuer="https://securetoken.google.com/" + AUDIENCE,
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
                    # Token is valid
                    print("Token is valid")
                    print("Decoded payload:", decoded_token)
                    # The timestamp is in unix format. Uncomment below to convert unix to utc format
                    # decoded_token['iat'] = datetime.fromtimestamp(
                    #     decoded_token['iat'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    # decoded_token['exp'] = datetime.fromtimestamp(
                    #     decoded_token['exp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    # print("Decoded payload:", decoded_token)
                    return decoded_token

                except ExpiredSignatureError:
                    if refresh_attempts >= 5:
                        print("Refresh attempts exceeded 5 or more times")
                        break
                    print("The token has expired. Attempting to refresh token...")
                    refresh_response = self._refresh_token(refresh_token)
                    token = refresh_response.get("id_token")
                    refresh_token = refresh_response.get("refresh_token")
                    if not token:
                        print("Failed to refresh the token. No new ID token received.")
                        time.sleep(1)
                    refresh_attempts = refresh_attempts + 1
                    continue
                except DecodeError:
                    print("The token is invalid.")
                    break
                except InvalidTokenError as e:
                    if validation_attempts >= 5:
                        print("Validation attempts exceeded 5 or more times")
                        break
                    print(f"Token validation error: {str(e)}")
                    print("Validating again...")
                    time.sleep(1)
                    validation_attempts = validation_attempts + 1
                    continue
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while retrieving Google's public keys: {str(e)}")

# Example usage
auth = Authorization()

# First, authorize and get the token
auth_res = auth.authorize(username=USERNAME, password=PASSWORD)
id_token = auth_res.get("idToken")  # The JWT token is usually in `idToken`
refresh_tk = auth_res.get("refreshToken")  # The refresh token
# print(id_token)
# print()
# print(refresh_token)

# Now validate the JWT token
if id_token:
    auth.validate_jwt(id_token, refresh_tk)
else:
    print("No ID Token received.")
