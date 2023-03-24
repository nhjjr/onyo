''' setup file for installation of onyo '''
from setuptools import setup, find_packages

setup(
    name='onyo',
    version=open("onyo/_version.py").readlines()[-1].split()[-1].strip("\"'"),
    description='Textual inventory system backed by git.',
    author='Tobias Kadelka',
    author_email='t.kadelka@fz-juelich.de',
    packages=find_packages(),
    license='ISC',
    install_requires=[
        'ruamel.yaml',
        'rich~=13.0'
    ],
    extras_require={
        'tests': [
            'flake8',
            'pyre-check',
            'pytest',
            'pytest-cov',
            'pytest-randomly'
        ],
        'docs': [
            'sphinx>=4.3.0',
            'sphinx-argparse',
            'sphinx-rtd-theme>=0.5.2'
        ]
    },
    python_requires=">=3.9",
    entry_points={
        'console_scripts': [
            'onyo=onyo.main:main'
        ],
    },
    include_package_data=True,
)
