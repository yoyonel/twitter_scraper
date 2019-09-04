#!/usr/bin/env python
"""The setup script."""
from distutils.command.build_py import build_py as _build_py
from distutils.command.sdist import sdist as _sdist
from itertools import chain
from pathlib import Path
from typing import Dict, List

import setuptools
from setuptools import find_packages
from setuptools import setup
from setuptools.command.develop import develop as _develop

# Parse requirements files
REQS = {
    pip_name: pip_lines
    for pip_name, pip_lines in map(
        lambda p: (p.stem.upper(), p.open().read().splitlines()),
        Path().glob(pattern="requirements/*.pip"),
    )
}  # type: Dict[str, List[str]]
# TODO: perform more complex substitution/eval (regexp, jinja, ...)
# https://stackoverflow.com/questions/952914/how-to-make-a-flat-list-out-of-list-of-lists
# https://stackoverflow.com/a/952952
# https://docs.python.org/2/library/itertools.html#itertools.chain.from_iterable
REQS["BASE_ALL"] = list(
    chain.from_iterable([REQS[k] for k in filter(lambda k: "BASE" in k, REQS)])
)

path_dependency_links = Path("requirements/dependency_links")
DEPENDENCY_LINKS = path_dependency_links.open().read().splitlines() if path_dependency_links.exists() else []

long_description = Path("README.md").read_text()


setup(
    name="twitter_scraper",
    author="Lionel ATTY",
    author_email="yoyonel@hotmail.com",
    url="https://github.com/yoyonel/twitter_scraper/",
    use_scm_version=True,
    description="",
    long_description=long_description,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={"": ["*.json", "*.csv", "*.proto"]},
    include_package_data=True,
    install_requires=REQS["BASE_ALL"],
    setup_requires=REQS["SETUP"],
    extras_require={
        "test": REQS["BASE_ALL"] + REQS["TEST"],
        "develop": REQS["BASE_ALL"] + REQS["TEST"] + REQS["DEV"] + REQS['TWITTER'],
        "setup": REQS["TEST"] + REQS["DEV"] + REQS["SETUP"],
        "docs": REQS["DOCS"],
        # requirements for entry_points by
    },
    dependency_links=DEPENDENCY_LINKS,
    classifiers=[
        "Programming Language :: Python :: 3.7",
    ],
    python_requires=">=3.7",
    cmdclass={},
    entry_points={"console_scripts": []},
    # https://github.com/pypa/sample-namespace-packages/issues/6
    zip_safe=False,
)
