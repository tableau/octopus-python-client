import json
import logging
from types import SimpleNamespace

import requests
import urllib3

from octopus_python_client.utilities.helper import log_raise_value_error

operation_delete = "delete"
operation_get = "get"
operation_post = "post"
operation_put = "put"

application_json = "application/json"
content_type_key = "Content-Type"
login_payload_password_key = "Password"
login_payload_user_name_key = "Username"
users_login_url_suffix = "users/login"
x_octopus_api_key_key = "X-Octopus-ApiKey"

logger = logging.getLogger(__name__)


def call_octopus(config, url_suffix=None, operation=None, payload=None):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = config.endpoint + url_suffix if url_suffix else config.endpoint
    operation = operation if operation else operation_get
    with requests.Session() as session:
        if config.api_key:
            headers = {content_type_key: application_json, x_octopus_api_key_key: config.api_key}
        elif config.user_name and config.password:
            headers = {content_type_key: application_json}
            login_url = config.endpoint + users_login_url_suffix
            login_payload = {login_payload_user_name_key: config.user_name, login_payload_password_key: config.password}
            session.post(login_url, json=login_payload, headers=headers, verify=config.pem)
        else:
            log_raise_value_error(local_logger=logger, err=f"either api_key or user_name and password are required")
        try:
            logger.info(f"{operation}: " + url)
            if operation.lower() == operation_post:
                session_response = session.post(url, json=payload, headers=headers, verify=config.pem)
            elif operation.lower() == operation_get:
                session_response = session.get(url, params=payload, headers=headers, verify=config.pem)
            elif operation.lower() == operation_put:
                session_response = session.put(url, json=payload, headers=headers, verify=config.pem)
            elif operation.lower() == operation_delete:
                session_response = session.delete(url, headers=headers, verify=config.pem)
            else:
                log_raise_value_error(local_logger=logger, err=f"Invalid operation: {operation}; only post, get, put "
                                                               f"and delete are supported")
            logger.info("response status code: " + str(session_response.status_code))
            response_json = ""
            if session_response.text:
                response_json = session_response.json()
            if session_response.status_code < 200 or session_response.status_code > 299:
                log_raise_value_error(local_logger=logger,
                                      err=f"Error code: {session_response.status_code}; Reason: "
                                          f"{session_response.reason}; {response_json}")
            return response_json
        except requests.exceptions.RequestException as e:
            log_raise_value_error(local_logger=logger, err=e)


# TODO for testing purpose, to be removed
def run():
    print("==================== test octopus http requests ===================")
    octopus_config = {"endpoint": "https://demo.octopusdeploy.com/api/", "api_key": None, "user_name": "guest",
                      "password": "guest"}
    response = call_octopus(config=SimpleNamespace(**octopus_config), url_suffix="Spaces-1/environments")
    print(json.dumps(response))


if __name__ == "__main__":
    run()
