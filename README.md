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
`SKIP_CONFTEST=1 pytest --cov ./humanfirst/ --cov-report html --cov-report term`
--cov-report html - produces a report in HTML page
--cov-report term - prints the report in console
--cov-report term:skip-covered - helps to see uncovered parts
SKIP_CONFTEST=1 - prevents slow synchronization with time server which is required only for running AIO containers locally.

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
**Wonkies**

***1: When running the aio container locally, if tests fail because of "Token used before issued" error, then it is caused by clock skew issue where the client and server time is not synchronised. This happens only locally. The circleci works without any issues.***

***2: If you keeping changing environments between test/staging/prod on WSL ubuntu, then you might face with clock ckew issue while running aio container on test environment. To avoid such scenarios, stick to using WSL ubuntu for running aio container locally on test environement and use academy container where all the dev work on HF SDK happens to run normal pytest commands on staging/prod environments***

***3: Still getting clock skew issue when running aio container locally on test environment (Less likely scenario), don't sweat. Run pytest commands locally on staging (command is given above) and commit your changes to git after all the tests passes. CircleCI would run everything without any issues on test environment on the latest dev branch***

Steps
* Open WSL ubuntu
* Make sure docker is working
* Go to humanfirst-module directory
* Create virtualenv & activate `python3 -m venv ubuntu-venv` 
* if bash shell `source venv/bin/activate` **In case of deactivating use "deactivate"**
* Update PiP `python -m pip install --upgrade pip`
* install requirements  `pip install -r requirements.txt --no-cache`
* Google SDK + auth - https://github.com/zia-ai/backend/tree/dev/dev#google-sdk--auth
    * Install gcloud - https://cloud.google.com/sdk/docs/install
    * Authenticate - `gcloud auth application-default login`
    * Authenticate for Docker - `gcloud auth configure-docker`
    * Set project using gcloud - `gcloud config set project trial-184203`
    * Set quota for the project - `gcloud auth application-default set-quota-project trial-184203`
    * Get access for embedding service running in staging from dev team 
    * Install gke-gcloud-auth-plugin
        ```
        gcloud components install gke-gcloud-auth-plugin
        echo "export USE_GKE_GCLOUD_AUTH_PLUGIN=True" >> ~/.profile
        ```
    * Get staging cluster credentials and rename its context to 'staging'
        ```
        gcloud components install kubectl
        kubectl config delete-context staging
        gcloud container clusters get-credentials zia-prod-1 --zone us-east1-b --project trial-184203
        kubectl config rename-context gke_trial-184203_us-east1-b_zia-prod-1 staging
        ```
* To kill existing connections to embedding service - `sudo kill -9 $(sudo lsof -t -i :8501)`
* Install ntpdate. Helps in synchronizing with timeserver - `sudo apt-get install ntpdate`
* Run AIO container `sudo timedatectl set-ntp true ; sudo systemctl restart systemd-timesyncd ; EMBEDDINGS_K8S_FORWARD=1 AIO_START=1 ./aio.sh test`


## Log handling
* HF SDK logging offers multiple options. Either can save the logs, print them in the console, do both or none
* To store the logs in a specific directory set HF_LOG_FILE_ENABLE to 'TRUE' and set the directory in HF_LOG_DIR where the log files needs to be stored
* Log file management
    * Rotating File Handler is used
    * When the log file size exceeds 100MB (Hard coded). Automatically a new file is created and old one is saved
    * Can go to upto 4 additional log files
    * If the number of log files exceed the additional log file count + 1, then automatically the oldest log file is gets replaced with new log information
* Can set log levels using HF_LOG_LEVEL. Accepts - 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' 
* To print the logs in console set HF_LOG_CONSOLE_ENABLE to 'TRUE'
* Default - the logs are neither saved nor printed onto console

***Note: Control what files can go into SDK using Manifest.in file***