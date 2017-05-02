from setuptools import setup

setup(name='spirack',
      version='0.1.0.dev2',
      description='Drivers for the QuTech SPI-rack',
      url='https://github.com/Rubenknex/SPI-rack',
      download_url='https://github.com/Rubenknex/SPI-rack/archive/0.1.0.dev1.tar.gz',
      author='Marijn Tiggelman',
      author_email='qutechdev@gmail.com',
      license='MIT',
      packages=['spirack'],
      keyword = ['SPI', 'Qcodes'],
      classifiers = [],
      install_requires=[
        'pyserial',
      ],
      package_data={
        '': ['*.cat', '*.inf']
      })
