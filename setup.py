from setuptools import setup,find_packages


setup(
    name="PyGo",
    version="0.0.1",
    author="carlitador",
    author_email="ch.dhainaut@gmail.com",
    description="",
    packages=find_packages(),
    entry_points = {
              'console_scripts': [
                  'pygo = pygo.go_sniff:main',                  
              ],              
    },
)