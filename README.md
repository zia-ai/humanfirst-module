# humanfirst-module
Humanfirst module package

## Create Virtual Environment to do any dev work and perform pytest work
* Remove any previously created virtual env `rm -rf ./venv`
* Create virtualenv & activate `python3 -m venv venv` 
* if bash shell `source venv/bin/activate` **In case of deactivating use "deactivate"**
* Update PiP `python -m pip install --upgrade pip`
* install requirements  `pip install -r requirements.txt --no-cache`

## Using pytest to test everything is working fine

First you need to decide if you are going to test locally or against staging/prod.
Start with staging and production.

Set your HF_USERNAME and HF_PASSWORD env variable to match the environment you wish to test against.

### Running on production

This is the default.

`pytest --cov ./humanfirst/ --cov-report html --cov-report term`
--cov-report html - produces a report in HTML page
--cov-report term - prints the report in console
--cov-report term:skip-covered - helps to see uncovered parts

### Running on staging
**Note: Staging access is available only for internal team members**

Switch environment variable `HF_ENVIRONMENT` = "staging"

Reset `HF_USERNAME` and `HF_PASSWORD` to be the relevant staging values.

To check are running on staging set `HF_LOG_CONSOLE_ENABLE` = TRUE and `HF_LOG_LEVEL` = DEBUG

Start the test again but with the console output printed
`pytest --cov ./humanfirst/ --cov-report html --cov-report term -s`

You should see it calling `https://api-staging.humanfirst.ai:443` in the logs

### Running on AIO container locally

In development and CI/CD the tests are run against a locally running AIO container with the backend elements of HF solution running. If external to HF you will not be able to run these steps.

* Google SDK + auth - https://github.com/zia-ai/backend/tree/dev/dev#google-sdk--auth
    * Following commands are executed in ubuntu. For a different system, find the commands here - https://cloud.google.com/sdk/docs/install
    * Install gcloud - https://cloud.google.com/sdk/docs/install
        * `sudo apt-get update`
        * `sudo apt-get install apt-transport-https ca-certificates gnupg curl`
        * `curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg`
        * `echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list`
        * `sudo apt-get update && sudo apt-get install google-cloud-cli`
        * `gcloud init`
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

Get crednetials and end point
* `gcloud container clusters get-credentials zia-prod-1 --zone us-east1-b --project trial-184203`

Rename to staging.
* `kubectl config rename-context gke_trial-184203_us-east1-b_zia-prod-1 staging`

Check nothing is running 
* To kill existing connections to embedding service - `sudo kill -9 $(sudo lsof -t -i :8501)`

Timeserver
* Install ntpdate. Helps in synchronizing with timeserver - `sudo apt-get install ntpdate`

Install nettools
* `sudo apt-get install net-tools`

Pull down just the container running script from e2e-testing

```
git config --global init.defaultBranch dev && \
git init e2e-testing && \
cd e2e-testing && \
git remote add origin git@github.com:zia-ai/e2e-testing.git && \
git config core.sparseCheckout true && \
echo "aio.sh" >> .git/info/sparse-checkout && \
git pull origin dev && \
mkdir src && \
mkdir src/logs/
```

Pull the container down, start the container and run pytest
* Run AIO container `CI=true EMBEDDINGS_K8S_FORWARD=1 AIO_START=1 ./aio.sh start`
* Get IP address - `docker inspect aio`
* Set enviroment variable BASE_URL_TEST `export BASE_URL_TEST=http://172.17.0.3:8888`. Replace 172.17.0.3 with your IP address.
* Run Pytest - `pytest --cov ./humanfirst/ --cov-report html --cov-report term`
* Stop AIO container `CI=true ./aio.sh stop`

How to know which image it is pulling
* aio.sh: "docker pull "gcr.io/trial-184203/backend-aio:$AIO_TAG" # fetch sync"
* So have to modify $AIO_TAG - currently "dev" - could also set to any branch
* Just latest from Dev pipeline


### Testing using Docker build for this module
**Note: Doing this requires the ability to run docker commands. You may need to run this from outside your local academy workbench** 

Check docker is working with `docker run hello-world` or `sudo docker run hello-world` depending on whether you have a user or root docker setup.

* `docker build . -t humanfirst-module:latest --no-cache`
To run the tests for this module we pass through the necessary env variables
`echo $HF_ENVIRONMENT $BASE_URL_TEST $HF_USERNAME $HF_PASSWORD`

```sh
docker run \
-e "HF_ENVIRONMENT=$HF_ENVIRONMENT" \
-e "BASE_URL_TEST=$BASE_URL_TEST" \
-e "HF_USERNAME=$HF_USERNAME" \
-e "HF_PASSWORD=$HF_PASSWORD" \
--name humanfirst-module-0 \
humanfirst-module \
pytest -s --cov ./humanfirst/ --cov-report term
```

## Build Package

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

## Log handling
* HF SDK logging offers multiple options. Either can save the logs, print them in the console, do both or none
* To store the logs in a specific directory set HF_LOG_FILE_ENABLE to 'TRUE' and set the directory in HF_LOG_DIR where the log files needs to be stored.
* Log file management
    * Rotating File Handler is used
    * When the log file size exceeds 100MB (Hard coded). Automatically a new file is created and old one is saved
    * Can go to upto 4 additional log files
    * If the number of log files exceed the additional log file count + 1, then automatically the oldest log file is gets replaced with new log information
* Can set log levels using HF_LOG_LEVEL. Accepts - 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' 
* To print the logs in console set exp to 'TRUE'
* Default - the logs are neither saved nor printed onto console

***Note: Control what files can go into SDK using Manifest.in file***