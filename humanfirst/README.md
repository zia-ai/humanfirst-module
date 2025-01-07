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

```python
import humanfirst

# Step 1 : Initialize the API
# Authorization is performed during the initialization of API
# username and password can directly be passed or can be set as environment variables - HF_USERNAME and HF_PASSWORD
hf_api = humanfirst.apis.HFAPI()

# Step 2: Perform an API call (e.g., fetching a list of projects)
playbook_list = hf_api.list_playbooks(namespace="<namespace>")

print(playbook_list)
```

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

## ⚙️ Development Setup
For contributors and developers, you can set up the package locally by cloning the repository and installing the necessary dependencies:

```bash
# Clone the repo
git clone https://github.com/zia-ai/humanfirst-module.git

# Navigate into the project directory
cd humanfirst-module

# Install dependencies
pip install -r requirements.txt

# Setup env variables
export HF_USERNAME="Humanfirst username"
export HF_PASSWORD="Humanfirst password" 

# Run tests
pytest
```

For more details on developer setup visit Developer [REAME.md](https://github.com/zia-ai/humanfirst-module/blob/master/README.md)

---

## 📢 Changelog
See the [CHANGELOG](https://pypi.org/project/humanfirst/#history) for details on the latest updates and changes to the package.

---

## 🔗 Links
🌐 Official Website: https://www.humanfirst.ai

📚 Documentation: https://docs.humanfirst.ai/docs

🐙 GitHub Repo: https://github.com/zia-ai/humanfirst-module

🐞 Issue Tracker: https://github.com/zia-ai/humanfirst-module/issues

---
Made with ❤️ by HumanFirst
