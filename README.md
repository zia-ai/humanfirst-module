# humanfirst-module
Humanfirst module package

# Docker build for this module
* `docker build . -t humanfirst-module:latest --no-cache`
To run the tests for this module we pass through the necessary env variables
`echo $HF_ENVIRONMENT $BASE_URL_TEST $HF_USERNAME $HF_PASSWORD $SKIP_CONFTEST`

```sh
docker run \
-e "HF_ENVIRONMENT=$HF_ENVIRONMENT" \
-e "BASE_URL_TEST=$BASE_URL_TEST" \
-e "HF_USERNAME=$HF_USERNAME" \
-e "HF_PASSWORD=$HF_PASSWORD" \
-e "SKIP_CONFTEST=1" \
--name humanfirst-module-0 \
humanfirst-module \
pytest -s --cov ./humanfirst/ --cov-report term
```

## Virtual Environment
* Remove any previously created virtual env `rm -rf ./venv`
* Create virtualenv & activate `python3 -m venv venv` 
* if bash shell `source venv/bin/activate` **In case of deactivating use "deactivate"**
* Update PiP `python -m pip install --upgrade pip`
* install requirements  `pip install -r requirements.txt --no-cache`

## Using pytest to test everything is working fine

First you need to decide if you are going to test locally or against staging/prod.
Start with staging and production.

Set your HF_USERNAME and HF_PASSWORD env variable to match the environment you wish to test against.

For running against staging or production time synchronisation is not necessary `SKIP_CONFTEST=1` is an environment variable which prevents that running by skipping all of conftest.py.  For running on an AIO container locally it is.

### running on production

This is the default.

`SKIP_CONFTEST=1 pytest --cov ./humanfirst/ --cov-report html --cov-report term`
--cov-report html - produces a report in HTML page
--cov-report term - prints the report in console
--cov-report term:skip-covered - helps to see uncovered parts
SKIP_CONFTEST=1 - prevents slow synchronization with time server which is required only for running AIO containers locally.

### Running on staging

Switch environment variable `HF_ENVIRONMENT` = "staging"

Reset `HF_USERNAME` and `HF_PASSWORD` to be the relevant staging values.

To check are running on staging set `HF_LOG_CONSOLE_ENABLE` = TRUE and `HF_LOG_LEVEL` = DEBUG

Start the test again but with the console output printed
`SKIP_CONFTEST=1 pytest --cov ./humanfirst/ --cov-report html --cov-report term -s`

You should see it calling `https://api-staging.humanfirst.ai:443` in the logs

### Running on AIO container

Doing this requires the ability to run docker commands.  Check docker is working with 
`docker run hello-world` or `sudo docker run hello-world` depending on whether you have a user or root docker setup.

You may need to run this from outside your local academy workbench

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

In development and CI/CD the tests are run against a locally running AIO container with the backend elements of HF solution running.  If external to HF you will not be able to run these steps.

**Caveats**

***1: When running the aio container locally, if tests fail because of "Token used before issued" error, then it is caused by clock skew issue where the client and server time is not synchronised. This happens only locally. The circleci works without any issues.***

***2: If you keeping changing environments between test/staging/prod on WSL ubuntu, then you might face with clock ckew issue while running aio container on test environment. To avoid such scenarios, stick to using WSL ubuntu for running aio container locally on test environement and use academy container where all the dev work on HF SDK happens to run normal pytest commands on staging/prod environments***

***3: Still getting clock skew issue when running aio container locally on test environment (Less likely scenario), don't sweat. Run pytest commands locally on staging (command is given above) and commit your changes to git after all the tests passes. CircleCI would run everything without any issues on test environment on the latest dev branch***



<!-- Steps
TODO: Rremove me moved to Docker
* Open WSL ubuntu
* Make sure docker is working `docker run hello-world`
* Go to humanfirst-module directory
* Create a separate virtualenv & activate `python3 -m venv ubuntu-venv` 
* if bash shell `source venv/bin/activate` **In case of deactivating use "deactivate"**
* Update PiP `python -m pip install --upgrade pip`
* install requirements  `pip install -r requirements.txt --no-cache` -->
* Google SDK + auth - https://github.com/zia-ai/backend/tree/dev/dev#google-sdk--auth
    * Install gcloud - https://cloud.google.com/sdk/docs/install
    * `sudo apt-get install apt-transport-https ca-certificates gnupg curl`
    * `curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg`
    * `echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list`
    * `sudo apt-get update && sudo apt-get install google-cloud-cli`

    * Authenticate - `gcloud auth application-default login`
    * Authenticate for Docker - `gcloud auth configure-docker`
    * Set project using gcloud - `gcloud config set project trial-184203`
    * Set quota for the project - `gcloud auth application-default set-quota-project trial-184203`
    * Get access for embedding service running in staging from dev team 
    * Install gke-gcloud-auth-plugin
    * `sudo apt-get install google-cloud-cli-gke-gcloud-auth-plugin`
    * enable the plugin
    * `echo "export USE_GKE_GCLOUD_AUTH_PLUGIN=True" >> ~/.profile`
    * Get staging cluster credentials and rename its context to 'staging'
    * `sudo apt-get install kubectl`
    * `kubectl config delete-context staging`
    * `gcloud auth login`

TODO: got this far and then couldn't seem to progress.

Have added a deterministic docker build for the Python

Get crednetials and end point
* `gcloud container clusters get-credentials zia-prod-1 --zone us-east1-b --project trial-184203`

Rename to staging.
* `kubectl config rename-context gke_trial-184203_us-east1-b_zia-prod-1 staging`

Check nothing is running 
* To kill existing connections to embedding service - `sudo kill -9 $(sudo lsof -t -i :8501)`

Timeserver
* Install ntpdate. Helps in synchronizing with timeserver - `sudo apt-get install ntpdate`

This runs the container

TODO: confirm this

GEt the aio.sh script here
`git archive --remote=ssh://zia-ai/e2e-testing.git HEAD aio.sh | tar xO`
`git archive --remote=git://git.foo.com/project.git HEAD:path/to/directory filename | tar -x`
`git archive --remote=git@github.com:zia-ai/e2e-testing.git dev:. aio.sh | tar -x`

Old test command
* Run AIO container `sudo timedatectl set-ntp true ; sudo systemctl restart systemd-timesyncd ; EMBEDDINGS_K8S_FORWARD=1 AIO_START=1 ./aio.sh test`

Make sure you have nettools
* `sudo apt-get install net-tools`

Pull the container down and start it the container
* Run AIO container `sudo timedatectl set-ntp true ; sudo systemctl restart systemd-timesyncd ; EMBEDDINGS_K8S_FORWARD=1 AIO_START=1 ./aio.sh start-aio`

TODO: How to know which image it is pulling
aio.sh: "docker pull "gcr.io/trial-184203/backend-aio:$AIO_TAG" # fetch sync"
So have to modify $AIO_TAG - currently "dev" - could also set to any branch
* Just latest from Dev pipeline


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