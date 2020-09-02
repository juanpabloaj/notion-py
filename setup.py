from setuptools import setup, find_packages

from notion import (
    __name__,
    __version__,
    __author__,
    __author_email__,
    __description__,
    __url__,
)

with open("README.md") as file:
    long_description = file.read()

with open("requirements.txt") as file:
    r = file.read().split("\n")
    r = map(lambda l: l.strip(), filter(len, r))
    r = filter(lambda l: not l.startswith("-"), r)
    r = filter(lambda l: not l.startswith("#"), r)
    install_requires = list(r)
    packages = find_packages(include=["notion*"])

setup(
    url=__url__,
    name=__name__,
    version=__version__,
    author=__author__,
    author_email=__author_email__,
    maintainer=__author__,
    maintainer_email=__author_email__,
    description=__description__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requires,
    include_package_data=True,
    packages=packages,
    python_requires=">=3.6",
    keywords=["python3", "notion", "api-client"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
