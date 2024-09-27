# humanfirst-module
Humanfirst module package

## Class List
HelloWorld

## Virtual Environment
* Remove any previously created virtual env `rm -rf ./venv`
* Create virtualenv & activate `python3 -m venv venv` 
* if bash shell `source venv/bin/activate` **In case of deactivating use "deactivate"**
* Update PiP `python -m pip install --upgrade pip`
* install requirements  `pip install -r requirements.txt --no-cache`

## Using pytest to test everything is working fine
Before using `pytest` command 

## Build packages

### Wipe your build dir first to be sure
`rm -rf ./build ./dist`

### Then build
`python setup.py sdist bdist_wheel`

## Test packages before uploading
Packages can be tested using TestPYPI before uploading to PYPI - https://packaging.python.org/en/latest/guides/using-testpypi/

Register in TestPYPI - https://test.pypi.org/account/register/

Enable 2 factor authentication and generate API token using Account settings

### Set TestPYPI password using keyring
`keyring set system __token__`

It'll prompt for a password - give it the API key
Theoretically this stops you having to put in your username and password each time.

Then Enter your TestPYPI API token

### Publish the package to TestPYPI
`twine upload --repository testpypi dist/*`

Username: `__token__`

Password: `API token`

### Using TestPyPI with pip
`pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ <your-package>`

## Upload packages to PYPI
Register in PYPI - https://pypi.org/account/register/

Enable 2 factor authentication and generate API token using Account settings

### Set PYPI password using keyring
`keyring set system __token__`

Then Enter your PYPI API token

### Publish the package to PYPI
`twine upload dist/*`

Username: `__token__`

Password: `API token`

## To install humanfirst package locally into academy

`python -m pip install -e ../humanfirst-module/`

## To install humanfirst package locally into humanfirst-module

`python3 -m pip install -e .`

## To install humanfirst package locally into humanfirst-module using the dist

`pip install dist/humanfirst-<version number>.tar.gz --no-cache`

or from academy example change the version number and the path...

`pip install ../humanfirst-module/dist/humanfirst-1.1.3.tar.gz --no-cache`

### CHECKS

make sure any last minute build changes committed!
pytest in academy

## Run AIO container Locally
* Open WSL ubuntu
* Make sure docker is working
* Go to humanfirst-module directory
* Create virtualenv & activate `python3 -m venv ubuntu-venv` 
* if bash shell `source venv/bin/activate` **In case of deactivating use "deactivate"**
* Update PiP `python -m pip install --upgrade pip`
* install requirements  `pip install -r requirements.txt --no-cache`
* Install gcloud - https://cloud.google.com/sdk/docs/install
* Authenticate - `gcloud auth application-default login`
* Authenticate for Docker - `gcloud auth configure-docker`
* Run AIO container `./aio.sh test`


## Log handling
* By default everything gets logged in SDK
* To store the logs in a specific directory set the directory to HF_LOG_DIR
* Can set log levels using HF_LOG_LEVEL. Accepts - 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' 
* If want to do both - store the logs in a file as well as print them in the console set HF_LOG_CONSOLE_ENABLE to 'TRUE'

***Note: Control what files can go into SDK using Manifest.in file***