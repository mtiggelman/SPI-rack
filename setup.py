from setuptools import setup

setup(name='spirack',
      version='0.1.0.dev1',
      description='Drivers for the QuTech SPI-rack',
      url='https://github.com/Rubenknex/SPI-rack',
      author='Marijn Tiggelman',
      author_email='qutechdev@gmail.com',
      license='MIT',
      packages=['spirack',
                'spirack/drivers'
                'tests'],
      install_requires=[
        'serial',
      ],
      package_data={
        '': ['*.cat', '*.inf']
      })
