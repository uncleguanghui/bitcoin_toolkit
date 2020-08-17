#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.command.clean import clean
import subprocess
import os
import shutil
import re

from setuptools.command.install import install
from setuptools.command.test import test
from setuptools import setup, find_packages


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


def get_version():
    with open('bitcoin_toolkit/__init__.py', 'r') as file:
        version = '0.0.0'
        for line in file.readlines():
            results = re.findall("__version__ = '(.*)'", line.replace("\"", '\''))
            if results:
                version = results[0]
                break
    return version


class ActionOnInstall(install):
    def run(self):
        install.run(self)


class ActionOnTest(test):
    def run(self):
        test.run(self)


class CleanHook(clean):
    def run(self):
        clean.run(self)

        def maybe_rm(path):
            if os.path.exists(path):
                shutil.rmtree(path)

        maybe_rm('bitcoin_toolkit.egg-info')
        maybe_rm('.pytest_cache')
        maybe_rm('build')
        maybe_rm('dist')
        maybe_rm('.eggs')
        maybe_rm('htmlcov')
        subprocess.call('rm -rf .coverage', shell=True)
        subprocess.call('rm -rf *.egg', shell=True)
        subprocess.call('rm -f datastore.db', shell=True)
        subprocess.call(r'find . -name "*.pyc" -exec rm -rf {} \;',
                        shell=True)


setup(
    name="bitcoin_toolkit",  # 应用名
    version=get_version(),  # 版本号
    packages=find_packages(),  # 指定子目录的python包
    install_requires=[  # 依赖列表
        'redis>=3.2.1',
        'psutil>=5.7.0',
        'blockchain-parser>=0.1.4',
        'networkx>=2.4',
        'matplotlib>=3.0.3',
        'pygraphviz>=1.5',
    ],
    tests_require=[
        'pytest >= 4.4.1',
        'pytest-cov >= 2.7.1',
        'pytest-pep8 >= 1.0.6',
        'pytest-flakes >= 4.0.0',
    ],
    include_package_data=True,  # 启用清单文件MANIFEST.in
    cmdclass={
        'clean': CleanHook,  # python setup.py clean 清理工作区
        'test': ActionOnTest,  # python setup.py test 测试
        'install': ActionOnInstall  # python setup.py install 安装
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: MacOS X",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Chinese (Simplified)",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
    ],
    # 其他描述信息
    author='guanghui.zhang',
    author_email='415558663@qq.com',
    description="bitcoin toolkit",
    keywords=['toolkit', 'bitcoin', 'blockchain', 'block', 'analysis', ''],
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    python_requires='>=3',
    license="MIT",
    url='https://github.com/uncleguanghui/bitcoin_toolkit'
)
