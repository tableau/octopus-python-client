import sys
from types import SimpleNamespace

import requests

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


def call_octopus(config=None, url_suffix=None, operation=None, payload=None):
    url = config.octopus_endpoint + url_suffix if url_suffix else config.octopus_endpoint
    operation = operation if operation else operation_get
    with requests.Session() as session:
        if config.api_key:
            headers = {content_type_key: application_json, x_octopus_api_key_key: config.api_key}
        elif config.user_name and config.password:
            headers = {content_type_key: application_json}
            login_url = config.octopus_endpoint + users_login_url_suffix
            login_payload = {login_payload_user_name_key: config.user_name, login_payload_password_key: config.password}
            session.post(login_url, json=login_payload, headers=headers)
        else:
            raise ValueError(f"either api_key or user_name and password are required")
        try:
            print(f"{operation}: " + url)
            if operation.lower() == operation_post:
                response = session.post(url, json=payload, headers=headers)
            elif operation.lower() == operation_get:
                response = session.get(url, params=payload, headers=headers)
                # TODO bug https://help.octopus.com/t/504-gateway-time-out-on-getting-all-variables/24732
                if response.status_code == 504:
                    print(response.text)
                    return {}
            elif operation.lower() == operation_put:
                response = session.put(url, json=payload, headers=headers)
            elif operation.lower() == operation_delete:
                response = session.delete(url, headers=headers)
                # when deleting an item referenced by other items, ignore the error and continue to delete other items
                if response.status_code == 400:
                    print(response.text)
                    return response.text
            else:
                err = f'Wrong operation: {operation}; only post, get, put and delete are supported'
                raise ValueError(err)
            print("response status code: " + str(response.status_code))
            # print("response headers: " + str(response.headers))
            response_json = ""
            if response.text:
                response_json = response.json()
            # if permission is denied, continue with other operations
            if response.status_code == 403:
                print(response_json)
            elif response.status_code < 200 or response.status_code > 299:
                raise ValueError('request failed: ' + str(response_json))
            return response_json
        except requests.exceptions.RequestException as e:
            print(e)
            sys.exit(1)


# TODO for testing purpose, to be removed
if __name__ == "__main__":
    octopus_config = {"octopus_endpoint": "https://demo.octopusdeploy.com/api/", "api_key": None, "user_name": "guest",
                      "password": "guest"}
    response = call_octopus(config=SimpleNamespace(**octopus_config), url_suffix="Spaces-1/environments")
    print(response)
