"""
setup.py

Helps in building the package with the project metadata
"""

import os
from setuptools import setup, find_packages

# locate where we are.
here = os.path.abspath(os.path.dirname(__file__))

# Reads in the readme file from ./humanfirst as the packaging description
with open(os.path.join(here, "humanfirst", "README.md"), encoding="utf-8") as f:
    long_description = "\n" + f.read()

VERSION = '1.0.4'
DESCRIPTION = 'HumanFirst Package Module'

CLASSIFIERS = [
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ]

# Setting up
setup(
    name="humanfirst",
    version=VERSION,
    author="Mohammed Fayaz Ansar Jelani",
    author_email="fayaz@humanfirst.ai",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    package_data={
        'humanfirst': ['config/*.conf', 'config/*.cfg'],
    },
    install_requires=[
        'numpy',
        'pandas',
        'requests',
        'requests-toolbelt',
        'dataclasses',
        'dataclasses-json',
        'python-dotenv'
    ],
    keywords=['python', 'humanfirst', 'HumanFirst'],
    classifiers=CLASSIFIERS,
    url='https://github.com/zia-ai/humanfirst-module',
    license='MIT',
    python_requires=">=3.11",
    extras_require={
        "dev": [
            "twine==4.0.2",
            "wheel==0.41.2",
            "keyring",
            "keyrings.alt",
            "pylint",
            "git-pylint-commit-hook",
            "numpy",
            "pandas",
            "requests",
            "requests-toolbelt",
            "autopep8",
            "dataclasses",
            "dataclasses-json",
            "pytest",
            "python-dotenv"
        ]
    }
)
