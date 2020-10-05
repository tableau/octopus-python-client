import json
from os.path import dirname, abspath

from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

requirements = ["requests>=2.20.0", "PyYAML>=5.1", "urllib3"]

LIBRARY_NAME_KEY = "library_name"
PACKAGE_NAME_KEY = "package_name"
PACKAGE_VERSION_KEY = "package_version"

with open(f"{dirname(abspath(__file__))}/src/octopus_python_client/configurations/system_config.json") as fp:
    system_config = json.load(fp)
setup(
    name=system_config.get(PACKAGE_NAME_KEY),
    version=system_config.get(PACKAGE_VERSION_KEY),
    author="Tony Li",
    author_email="tonybest@gmail.com",
    description="Python script & GUI to manage Octopus deploy servers through the Octopus Restful APIs",
    long_description=readme,
    long_description_content_type="text/markdown",
    url=f"https://github.com/tableau/{system_config.get(PACKAGE_NAME_KEY)}",
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=requirements,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            f"{system_config.get(LIBRARY_NAME_KEY)} = {system_config.get(LIBRARY_NAME_KEY)}.main:main",
            f"{system_config.get(LIBRARY_NAME_KEY)}_gui = {system_config.get(LIBRARY_NAME_KEY)}.gui.main_gui:main"
        ]
    }
)
