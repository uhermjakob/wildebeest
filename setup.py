#!/usr/bin/env python

import wildebeest
from pathlib import Path

from setuptools import setup, find_namespace_packages

long_description = Path('README.md').read_text(encoding='utf-8', errors='ignore')

classifiers = [  # copied from https://pypi.org/classifiers/
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Topic :: Utilities',
    'Topic :: Text Processing',
    'Topic :: Text Processing :: General',
    'Topic :: Text Processing :: Filters',
    'Topic :: Text Processing :: Linguistic',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3 :: Only',
]

setup(
    name='wildebeest-nlp',
    version=wildebeest.__version__,
    description=wildebeest.__description__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=classifiers,
    python_requires='>=3.8',
    url='https://github.com/uhermjakob/wildebeest',
    download_url='https://github.com/uhermjakob/wildebeest',
    platforms=['any'],
    author='Ulf Hermjakob',
    author_email='ulf@isi.edu',
    packages=find_namespace_packages(exclude=['aux', 'old']),
    keywords=['machine translation', 'datasets', 'NLP', 'natural language processing,'
                                                        'computational linguistics'],
    entry_points={
        'console_scripts': [
            'wb_normalize.py=wildebeest.wb_normalize:main',
            'wb_analysis.py=wildebeest.wb_analysis:main',
            'wb-norm=wildebeest.wb_normalize:main',
            'wb-ana=wildebeest.wb_analysis:main',
        ],
    },
    install_requires=[
        'regex>=2021.8.3',
        'tqdm>=4.40',
        'unicodeblock>=0.3.1',
        'wheel>=0.38.4',
    ],
    include_package_data=True,
    zip_safe=False,
)
