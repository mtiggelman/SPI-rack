import os
import re
from setuptools import setup

def get_version(verbose=0):
    """ Extract version information from source code """

    try:
        if os.path.exists('spirack/version.py'):
            with open('spirack/version.py') as f:
                ln = f.readline()
                v = ln.split('=')
                m = re.search('\'(.*)\'', ln)
                FULLVERSION = (m.group(0)).strip().strip('\'').strip('"')
        else:
            FULLVERSION = '0.0'
    except Exception as E:
        FULLVERSION = '0.0'
    if verbose:
        print('get_version_info: %s' % FULLVERSION)
    return FULLVERSION

with open("README.md", "r") as fh:
    long_description = fh.read()

version = get_version()

setup(name='spirack',
      version=version,
      description='Drivers for the QuTech SPI-rack',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/mtiggelman/SPI-rack',
      author='Marijn Tiggelman',
      author_email='qutechdev@gmail.com',
      license='MIT',
      packages=['spirack'],
      keywords=['SPI', 'Qcodes', 'SPI-rack', 'QuTech', 'TU Delft', 'SPI'],
      classifiers=(
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent"),
      install_requires=[
          'pyserial',
          'numpy'
      ],
      package_data={
          '': ['*.cat', '*.inf']
})
