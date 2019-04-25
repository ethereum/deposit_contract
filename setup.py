#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


deps = {
    'test': [
        "tox==3.0.0",
        "eth-tester[py-evm]==0.1.0b29",
        "vyper==0.1.0b9",
        "web3==4.8.3",
        "pytest==3.6.1",
    ],
    'lint': [
        "flake8==3.5.0",
        "isort>=4.2.15,<5",
    ],
    'doc': [
        "Sphinx>=1.6.5,<2",
        "sphinx_rtd_theme>=0.1.9",
    ],
}


deps['dev'] = (
    deps['test'] +
    deps['lint'] +
    deps['doc']
)

setup(
    name='deposit_contract',
    # *IMPORTANT*: Don't manually change the version here. Use `make bump`, as described in readme
    version='0.1.0-alpha.0',
    description='',
    url='https://github.com/ethereum/deposit_contract',
    packages=find_packages(
        exclude=[
            "tests",
            "tests.*",
        ]
    ),
    python_requires='>=3.6.*',
    extras_require=deps,
    py_modules=['deposit_contract'],
    license="MIT",
    setup_requires=['setuptools-markdown'],
    long_description_markdown_filename='README.md',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
    ],
)
