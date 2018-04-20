from setuptools import setup

setup(name='qw_reports',
      version='0.1',
      description='Tools for preparing water quality reports',
      url='',
      author='Timothy Hodson',
      author_email='thodson@usgs.gov',
      license='MIT',
      packages=['qw_reports'],
      entry_points = {
          'console_scripts': [
              #nutrient_mon_report/__main__.py
              'nutrient_mon_report = nutrient_mon_report.__main__:main',
              #TODO add script for plotting events
              #TODO add script for updating store
          ]
      },
      zip_safe=False)
