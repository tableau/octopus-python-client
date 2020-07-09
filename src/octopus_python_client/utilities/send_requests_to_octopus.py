import logging

import requests
import urllib3

from octopus_python_client.config import Config
from octopus_python_client.utilities.helper import log_raise_value_error

operation_delete = "delete"
operation_get = "get"
operation_post = "post"
operation_put = "put"
operation_get_file = "get_file"
operation_post_file = "post_file"

application_json = "application/json"
content_type_key = "Content-Type"
login_payload_password_key = "Password"
login_payload_user_name_key = "Username"
users_login_url_suffix = "users/login"
x_octopus_api_key_key = "X-Octopus-ApiKey"

logger = logging.getLogger(__name__)


def call_octopus(config: Config, url_suffix=None, operation=None, payload=None, files=None):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = config.endpoint + url_suffix if url_suffix else config.endpoint
    operation = operation if operation else operation_get
    with requests.Session() as session:
        headers = {} if operation == operation_post_file else {content_type_key: application_json}
        if config.api_key:
            headers[x_octopus_api_key_key] = config.api_key
        elif config.user_name and config.password:
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
            elif operation.lower() == operation_get_file:
                session_response = session.get(url, headers=headers, verify=config.pem)
                if session_response.status_code == 200:
                    logger.info("response headers: " + str(session_response.headers))
                    return session_response.content, session_response.headers
            elif operation.lower() == operation_post_file:
                session_response = session.post(url, files=files, headers=headers, verify=config.pem)
            else:
                log_raise_value_error(local_logger=logger,
                                      err=f"Invalid operation: {operation}; only post, get, put, delete, get_file, "
                                          f"post_file are supported")
            logger.info("response status code: " + str(session_response.status_code))
            logger.info("response headers: " + str(session_response.headers))
            response_json = ""
            if session_response.text:
                response_json = session_response.json()
            if session_response.status_code < 200 or session_response.status_code > 299:
                log_raise_value_error(local_logger=logger,
                                      err=f"Error code: {session_response.status_code}; Reason: "
                                          f"{session_response.reason}; {response_json}")
            return response_json, session_response.headers
        except requests.exceptions.RequestException as e:
            log_raise_value_error(local_logger=logger, err=e)


# TODO for testing purpose, to be removed
def run():
    print("==================== test octopus http requests ===================")
    # octopus_config = {"endpoint": "https://demo.octopusdeploy.com/api/", "api_key": None, "user_name": "guest",
    #                   "password": "guest", "pem": False}
    response, headers = call_octopus(config=Config(), url_suffix="Spaces-1/environments")
    print(response)
    package_name_version = "SampleFunction.1.0.1"
    response, headers = \
        call_octopus(config=Config(), url_suffix=f"Spaces-1/packages/packages-{package_name_version}")
    package_dict = response
    print()
    print(package_dict)
    file_name = f"{package_dict.get('PackageId')}.{package_dict.get('Version')}{package_dict.get('FileExtension')}"
    print(file_name)
    content, headers = \
        call_octopus(config=Config(),
                     url_suffix=f"Spaces-1/packages/packages-{package_name_version}/raw",
                     operation=operation_get_file)
    print(len(content))

    dst_octopus_config = Config()
    dst_octopus_config.endpoint = "http://localhost/api/"
    dst_octopus_config.api_key = "API-XXX"

    upload_response, headers = \
        call_octopus(config=dst_octopus_config,
                     url_suffix="Spaces-1/packages/raw?overwriteMode=OverwriteExisting",
                     # IgnoreIfExists
                     operation=operation_post_file,
                     files={"file": (file_name, content)})
    print(upload_response)

    file = open(file_name, "wb")
    file.write(content)
    file.close()
    upload_response = call_octopus(config=Config(),
                                   url_suffix="Spaces-1/packages/raw?overwriteMode=IgnoreIfExists",
                                   operation=operation_post_file,
                                   files={"file": (file_name, open(file_name, 'rb'))})
    print(upload_response)


if __name__ == "__main__":
    run()
