#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# 读取README文件作为long_description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    with open(readme_path, 'r', encoding='utf-8') as f:
        return f.read()

# 读取requirements文件
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                requirements.append(line)
        return requirements

setup(
    name='c-static-analyzer',
    version='1.0.0',
    description='Industrial-grade C language static analysis system using Python and Clang/AST',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='CodeAnalysis Team',
    author_email='team@codeanalysis.com',
    url='https://github.com/codeanalysis/c-static-analyzer',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.8',
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.8.0',
            'mypy>=0.991',
            'black>=22.0.0',
            'flake8>=5.0.0',
        ],
        'docs': [
            'sphinx>=5.0.0',
            'sphinx-rtd-theme>=1.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'c-analyzer=src.analyzer:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
    ],
    keywords='static-analysis clang ast cfg pdg dataflow c-language',
    project_urls={
        'Bug Reports': 'https://github.com/codeanalysis/c-static-analyzer/issues',
        'Documentation': 'https://c-static-analyzer.readthedocs.io/',
        'Source': 'https://github.com/codeanalysis/c-static-analyzer',
    },
)