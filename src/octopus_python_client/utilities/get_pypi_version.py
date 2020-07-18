import json

import requests

URL_PATTERN = 'https://pypi.python.org/pypi/{package}/json'


def get_version(package, url_pattern=URL_PATTERN):
    """Return version of package on pypi.python.org using json."""
    req = requests.get(url_pattern.format(package=package))
    version = "unknown"
    if req.status_code == requests.codes.ok:
        j = json.loads(req.text.encode(req.encoding or "utf-8"))
        releases = j.get('releases', [])
        for release in releases:
            version = release
    return version


if __name__ == '__main__':
    print("octopus-python-client==%s" % get_version('octopus-python-client'))
