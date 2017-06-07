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

setup(name='spirack',
      version='0.1.0.dev5',
      description='Drivers for the QuTech SPI-rack',
      url='https://github.com/Rubenknex/SPI-rack',
      download_url='https://github.com/Rubenknex/SPI-rack/archive/0.1.0.dev4.tar.gz',
      author='Marijn Tiggelman',
      author_email='qutechdev@gmail.com',
      license='MIT',
      packages=['spirack'],
      keywords = ['SPI', 'Qcodes', 'SPI-rack'],
      classifiers = [],
      install_requires=[
        'pyserial',
      ],
      package_data={
        '': ['*.cat', '*.inf']
})
