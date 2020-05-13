import ast
import copy
import json
import logging
from pathlib import Path
from pprint import pformat

import yaml

yaml_exts = (".yaml", ".yml")
json_ext = ".json"

logger = logging.getLogger(__name__)


def find_index(lst=None, key=None, value=None):
    logger.info(f"searching the first occurrence of {key} = {value} in the list and return the index...")
    for i, dic in enumerate(lst):
        if dic.get(key) == value:
            logger.info(f"found the first occurrence at index {i}")
            return i
    logger.warning(f"no matched item found")
    return -1


def find_item(lst=None, key=None, value=None):
    logger.info(f"searching the first occurrence of {key} = {value} in the list and return the item...")
    index = find_index(lst, key, value)
    if index < 0:
        return {}
    return lst[index]


# TODO Octopus treats string case insensitive for item names
def find_matched_sub_list(lst=None, match_dict=None, ignore_case=False):
    logger.info(f"Try to find the matched sub-list for a list against {match_dict}...")
    list_copy = copy.deepcopy(lst)
    # we must do reversely to avoid unexpected result on deleting by index
    for index in range(len(list_copy) - 1, -1, -1):
        # logger.info(f"working on the index {index} of the input list")
        dic = list_copy[index]
        for match_key, match_value in match_dict.items():
            if ignore_case and dic.get(match_key) != match_value and dic.get(match_key).lower() == match_value.lower():
                logger.warning(f"for key {match_key}, value of the {index}th item in the list is {dic.get(match_key)}, "
                               f"and value of the match dict is {match_value}. They are case insensitively same")
            elif not ignore_case and dic.get(match_key) != match_value \
                    or ignore_case and dic.get(match_key).lower() != match_value.lower():
                del list_copy[index]
                break
    if list_copy:
        logger.info(f"{len(list_copy)} matched items are found from the input list.")
    else:
        logger.info(f"no matched items are found from the input list.")
    return list_copy


def replace_list_new_value(lst=None, match_dict=None, replace_dict=None):
    logger.info(f"replace with {replace_dict} in list matching the input {match_dict}")
    for index, dic in enumerate(lst):
        # logger.info(f"working on the index {index} of the input list")
        match = True
        for match_key, match_value in match_dict.items():
            if dic.get(match_key) != match_value:
                match = False
                break
        if match:
            logger.info(f"index at {index} is a match; replace with {replace_dict}")
            for replace_key, replace_value in replace_dict.items():
                dic[replace_key] = replace_value


def load_json_file(file_path_name=None):
    logger.info(f"loading {file_path_name} ...")
    if Path(file_path_name).is_file():
        with open(file_path_name) as f:
            return json.load(f)
    log_raise_value_error(err=f"File {file_path_name} does not exit")


def save_json_file(file_path_name=None, content=None):
    logger.info(f"writing {file_path_name} ...")
    make_dir(file_path_name=file_path_name)
    with open(file_path_name, 'w', newline='\n') as fp:
        json.dump(content, fp, indent=2)


def load_yaml_file(file_path_name=None):
    logger.info(f"loading {file_path_name} ...")
    if Path(file_path_name).is_file():
        with open(file_path_name, 'r') as stream:
            return yaml.safe_load(stream)
    log_raise_value_error(err=f"File {file_path_name} does not exit")


def save_yaml_file(file_path_name=None, content=None):
    logger.info(f"writing {file_path_name} ...")
    make_dir(file_path_name=file_path_name)
    with open(file_path_name, 'w', newline='\n') as outfile:
        yaml.safe_dump(content, outfile, default_flow_style=False, sort_keys=False)


def make_dir(file_path_name=None):
    if not file_path_name:
        log_raise_value_error(err=f"file path cannot be empty")
    p = Path(file_path_name).parent
    p.mkdir(parents=True, exist_ok=True)


# compare two lists, same returns True, otherwise returns False
def compare_lists(list1, list2):
    pairs = zip(list1, list2)
    diff = [(x, y) for x, y in pairs if x != y]
    logger.info('List difference: ' + str(diff))
    return not diff


# compare two dictionaries, same returns True, otherwise returns False
def compare_dicts(dict1, dict2):
    diff1 = {k: dict1[k] for k in dict1 if k not in dict2 or dict1[k] != dict2[k]}
    diff2 = {k: dict2[k] for k in dict2 if k not in dict1 or dict1[k] != dict2[k]}
    logger.info('Dict difference: ' + str([diff1, diff2]))
    return dict1 == dict2


def compare_overwrite(data=None, local_file=None):
    logger.info(f"comparing and save local file {local_file}...")
    if not Path(local_file).is_file():
        logger.info(f"{local_file} does not exist, so just write it")
        save_file(file_path_name=local_file, content=data)
        return
    logger.info(f"{local_file} already exists, so compare and write it")
    local = None
    if local_file.endswith(json_ext):
        local = load_json_file(local_file)
    elif local_file.endswith(yaml_exts):
        local = load_yaml_file(local_file)
    else:
        log_raise_value_error(err=f"The file to be compared must be either {yaml_exts} or {json_ext} file. "
                                  f"Your file {local_file} is not one of them")
    if isinstance(data, list):
        is_sync = compare_lists(local, data)
    elif isinstance(data, dict):
        is_sync = compare_dicts(local, data)
    else:
        is_sync = str(local) == str(data)
    if not is_sync:
        overwrite = input('The remote data is different from your local data. ' +
                          f'Do you want to overwrite your local file {local_file} [Y/n]: ')
        if overwrite == 'Y':
            logger.info(f'Writing your local file {local_file} with the remote data...')
            save_file(file_path_name=local_file, content=data)
        else:
            logger.info('No overwritten happens')


def load_file(file_path_name=None):
    if file_path_name.endswith(json_ext):
        return load_json_file(file_path_name=file_path_name)
    elif file_path_name.endswith(yaml_exts):
        return load_yaml_file(file_path_name=file_path_name)
    else:
        log_raise_value_error(err=f"The file to be loaded must be either {yaml_exts} or {json_ext} file. "
                                  f"Your file {file_path_name} is not one of them")


def save_file(file_path_name=None, content=None):
    logger.info(f"writing a new local file {file_path_name}...")
    if file_path_name.endswith(json_ext):
        save_json_file(file_path_name=file_path_name, content=content)
    elif file_path_name.endswith(yaml_exts):
        save_yaml_file(file_path_name=file_path_name, content=content)
    else:
        log_raise_value_error(err=f"The file to be saved must be either {yaml_exts} or {json_ext} file. Your file "
                                  f"{file_path_name} is not one of them")


def parse_string(local_logger=logger, string=None):
    local_logger.info(f"parse str {string}...")
    try:
        python_structure = ast.literal_eval(string)
    except Exception as err:
        local_logger.warning(err)
        local_logger.info("string is not a python structure")
        return string
    local_logger.info("string is a python structure:")
    local_logger.info(pformat(python_structure))
    return python_structure


def log_raise_value_error(local_logger=logger, item=None, err=None):
    local_logger.error(err)
    if item:
        local_logger.info(pformat(item))
    raise ValueError(err)


# check if the local item file is the same as the item on Octopus server
# the remote item is an input
def is_local_same_as_remote2(remote_item, local_item_file):
    if not remote_item or not local_item_file:
        raise ValueError('remote_item and local_item_file must not be empty')
    local_item = load_file(local_item_file)
    return compare_dicts(local_item, remote_item), local_item


def write_binary_file(local_file, content):
    logger.info(f"writing a binary file {local_file}...")
    with open(local_file, "wb") as file:
        file.write(content)
