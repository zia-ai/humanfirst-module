# 🚀 HumanFirst SDK (humanfirst-module)

---
The **HumanFirst SDK (humanfirst-module)** is a Python package that simplifies the integration and interaction with the [HumanFirst platform](https://www.humanfirst.ai/) - It is a no-code tool specializing in Data Engineering, Prompt Engineering, Context Engineering, Conversational AI and NLU.

SDK provides a set of tools, helper classes, and API methods to streamline working with the **HumanFirst JSON format**, **API endpoints**, and **Secure authorization**.

---

## 🎯 Key Features
* **HumanFirst Objects**: Helper classes to describe, validate, and manipulate the core data structures used in the HumanFirst platform.
* **HumanFirst APIs**: A streamlined way to interact with the HumanFirst APIs for managing datasets, labels, prompts, pipelines and more.
* **Secure Authorization**: Simplified handling of secure API authentication and token management.

---

## 📦 Installation

Install the package using `pip`:

```bash
pip install humanfirst
```

---

## 🧩 Components Overview
1. **humanfirst.objects**: A set of helper classes and methods for describing, validating, and interacting with HFObjects that make up the HumanFirst JSON format.

    * Validate and manipulate HumanFirst objects.
    * Convert between Python objects and HumanFirst JSON structures.

2. **humanfirst.apis**: Helper classes to interact with the HumanFirst APIs.

    * Perform CRUD operations on datasets and projects.
    * Easily integrate HumanFirst functionalities into your applications.

3. **humanfirst.authorization**: Handles secure authorization for interacting with HumanFirst APIs.

    * Manage API keys and tokens.
    * Ensure secure communication with the HumanFirst platform.

---

## 📖 Usage Example
Here's a basic example of how to use the HumanFirst SDK to connect to the HumanFirst API and perform operations:

Follow the authentication steps given in the development setup below.

```python
import humanfirst

# Step 1 : Initialize the API
hf_api = humanfirst.apis.HFAPI()

# Step 2: Perform an API call (e.g., fetching a list of projects)
playbook_list = hf_api.list_playbooks(namespace="<namespace>")

print(playbook_list)
```

---

## ⚙️ Development Setup
For contributors and developers, you can set up the package locally by cloning the repository and installing the necessary dependencies:

```bash
# Clone the repo
git clone https://github.com/zia-ai/humanfirst-module.git

# Navigate into the project directory
cd humanfirst-module
```

### Create Virtual Environment to do any dev work and perform pytest work
* Remove any previously created virtual env `rm -rf ./venv`
* Create virtualenv & activate `python3 -m venv venv` 
* if bash shell `source venv/bin/activate` **In case of deactivating use "deactivate"**
* Update PiP `python -m pip install --upgrade pip`
* install requirements  `pip install -r requirements.txt --no-cache`

### Authentication
1. Either use firebase authentication
    * Set your HF_USERNAME and HF_PASSWORD env variable
2. Or use HumanFirst API Key
    * Set HF_API_KEY env variable
    * Follow the steps [here](https://api-keys.humanfirst-docs.pages.dev/docs/api/) to get API key

### Log handling
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

### Using pytest to test everything is working fine
#### Running on production

This is the default.

`pytest --cov ./humanfirst/ --cov-report html --cov-report term`
* --cov-report html - produces a report in HTML page
* --cov-report term - prints the report in console
* --cov-report term:skip-covered - helps to see uncovered parts

#### Testing using Docker build for this module

Check docker is working with `docker run hello-world` or `sudo docker run hello-world` depending on whether you have a user or root docker setup.

* `docker build . -t humanfirst-module:latest --no-cache`
To run the tests for this module we pass through the necessary env variables
`echo $HF_ENVIRONMENT $BASE_URL_TEST $HF_USERNAME $HF_PASSWORD`

```sh
docker run \
-e "HF_USERNAME=$HF_USERNAME" \
-e "HF_PASSWORD=$HF_PASSWORD" \
--name humanfirst-module-0 \
humanfirst-module \
pytest -s --cov ./humanfirst/ --cov-report term
```

### To install humanfirst package locally

`pip install dist/humanfirst-<version number>.tar.gz --no-cache`

For more details on developer setup visit Developer [README.md](https://github.com/zia-ai/humanfirst-module/blob/master/humanfirst/README.md)

---
## 🔧 Configuration Files
The package includes configuration files located in the config/ directory. 

```bash
config/
│
├── logging.conf
└── setup.cfg
```
* logging.conf - contains all the logging related configurations
* setup.cfg - contains all important default constants

---

## 📚 API Reference
For detailed API reference, visit the official documentation:

📖 Documentation: https://docs.humanfirst.ai/docs/api/

📂 Source Code APIs: https://github.com/zia-ai/humanfirst-module/blob/master/humanfirst/apis.py

---

## 🤝 Contributing
We welcome contributions to the HumanFirst SDK! If you find a bug or have a feature request, please open an issue on GitHub.

### Steps to Contribute:
* Fork the repository.
* Create a new branch for your feature/bugfix.
* Submit a pull request.

---

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/zia-ai/humanfirst-module/blob/master/LICENSE) file for more details.

---

## 💬 Support
If you have any questions or need support, feel free to reach out:

📧 Email: fayaz@humanfirst.ai

💻 GitHub Issues: https://github.com/zia-ai/humanfirst-module/issues

---

## 🔗 Links
🌐 Official Website: https://www.humanfirst.ai

📚 Documentation: https://docs.humanfirst.ai/docs

🐙 GitHub Repo: https://github.com/zia-ai/humanfirst-module

🐞 Issue Tracker: https://github.com/zia-ai/humanfirst-module/issues

---