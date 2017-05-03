from setuptools import setup

import os
import subprocess

path = os.path.join(os.getcwd(), 'spirack', 'drivers', 'SPI_Rack_Controller.inf')

cmd = 'C:\\Windows\\System32\\PNPUTIL.exe -i -a {}'
proc = subprocess.Popen([cmd.format(path)], stdout=subprocess.PIPE, shell=True)
out, err = proc.communicate()

print(out)

setup(name='spirack',
      version='0.1.0.dev2',
      description='Drivers for the QuTech SPI-rack',
      url='https://github.com/Rubenknex/SPI-rack',
      download_url='https://github.com/Rubenknex/SPI-rack/archive/0.1.0.dev1.tar.gz',
      author='Marijn Tiggelman',
      author_email='qutechdev@gmail.com',
      license='MIT',
      packages=['spirack', 'spirack/drivers'],
      keyword = ['SPI', 'Qcodes'],
      classifiers = [],
      install_requires=[
        'pyserial',
      ],
      package_data={
        '': ['*.cat', '*.inf']
      })
