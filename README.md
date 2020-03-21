# octopus-python-client

![As-Is](https://img.shields.io/badge/Support%20Level-As--Is-e8762c.svg)

Python script to manage Octopus deploy servers through the Octopus Restful APIs

* [Why octopus-python-client?](#why-octopus-python-client)
* [Example](#example)
* [Get started](#get-started)
	* [Prerequisites](#prerequisites)
	* [Configuration](#configuration)
	* [Installation](#installation)
* [Run octopus-python-client](#run-octopus-python-client)
* [Contributions](#contributions)

# Why octopus-python-client?

This project programmatically manage Octopus server through Restful APIs.
* Managing Octopus server through UI does not fit all situations.
* In the market, we have only PowerShell and C# client tools to manage Octopus server through APIs. We want a client tool which is across the different platform/OS to manage Octopus server through APIs. 
* A Octopus server/space migration tool is missing on the market. See the complaints
https://github.com/OctopusDeploy/Issues/issues/5451
https://help.octopus.com/t/how-do-i-transfer-or-clone-a-project-to-a-different-space-in-octopus-cloud/23333
https://help.octopus.com/t/octopus-migration-import-api-does-not-honor-space-id/24287/4

# Example
get all configurations and settings from all spaces at https://demo.octopusdeploy.com/api/
```
octopus_python_client -a=get_spaces
```

# Get started

This section describes how to install and configure octopus-python-client.


## Prerequistes

To work with octopus-python-client, you need the following:

* Windows, MacOS, Linux
* [requests >= 2.20.0](https://pypi.org/project/requests/)
* [PyYAML>=5.1](https://pypi.org/project/PyYAML/)
* python >= 3.6


## Configuration

After you've cloned octopus-python-client, configure it by following these steps before installation

* open src/octopus_python_client/configurations/configuration.jason
* change the endpoint, folder name; user_name and password or api_key is needed, not both

## Installation

* To install octopus-python-client, run

```
pip install .
```

* To uninstall octopus-python-client, run

```
pip uninstall octopus-python-client
```

# Run octopus-python-client

Please check the [wiki](https://github.com/tableau/octopus-python-client/wiki) for more details

# Contributions

Code contributions and improvements by the community are welcomed!
See the LICENSE file for current open-source licensing and use information.

Before we can accept pull requests from contributors, we require a signed [Contributor License Agreement (CLA)](http://tableau.github.io/contributing.html),
