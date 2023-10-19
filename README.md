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

Install humanfirst module using the following command
`python3 -m pip install -e .`

## Build packages
`python setup.py sdist bdist_wheel`

## Set PYPI password using keyring
Generate API token in PYPI -> Account settings

`keyring set system __token__`

Then Enter your API token

## Publish the package to PYPI
`twine upload dist/*`

Username: `__token__`

Password: `API token`