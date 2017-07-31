#from distutils.core import setup
from setuptools import setup, find_packages
import os

datadir = 'models'
datafiles = [(d, [os.path.join(d,f) for f in files])
    for d, folders, files in os.walk(datadir)]

with open('requirements.txt', 'r') as f:
    required = f.read().splitlines()


setup(
    name='PCBComponentDetector',
    version='0.1dev0',
    author='Gayathri Mahalingam, Kevin Marshall Gay',
    author_email='mahalingamg@uncw.edu',
    packages=find_packages(),
    package_data={'detector':datafiles},
    include_package_data=True,
    install_requires=required,
    setup_requires=[],
    tests_require=[],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.md').read(),
)
