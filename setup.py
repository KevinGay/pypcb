from distutils.core import setup
#from setuptools import setup, find_packages
import os

datadir = 'detector/models'
datafiles = [(d, [os.path.join(d,f) for f in files])
    for d, folders, files in os.walk(datadir)]

with open('requirements.txt', 'r') as f:
    required = f.read().splitlines()


setup(
    name='PCBComponentDetector',
    version='0.1dev0',
    author='Gayathri Mahalingam, Kevin Marshall Gay',
    author_email='mahalingamg@uncw.edu',
    packages=['detector'],
    package_data={'detector':['models/ic/*', 'models/resistor/*', 'models/capacitor/*']},
    #include_package_data=True,
    data_files=datafiles,
    #install_requires=required,
    #setup_requires=[],
    #tests_require=[],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.md').read(),
)
