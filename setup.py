from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

requirements = ["requests>=2.20.0", "PyYAML>=5.1", "urllib3"]

setup(
    name="octopus-python-client",
    version="2.1.0",
    author="Tony Li",
    author_email="tonybest@gmail.com",
    description="Python script to manage Octopus deploy servers through the Octopus Restful APIs",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/tableau/octopus-python-client",
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=requirements,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'octopus_python_client = octopus_python_client.main:main'
        ]
    }
)
