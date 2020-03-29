import copy
import json
import logging
from pathlib import Path

import yaml

yaml_exts = (".yaml", ".yml")
json_ext = ".json"

logger = logging.getLogger(__name__)


def find_index(lst=None, key=None, value=None):
    for i, dic in enumerate(lst):
        if dic.get(key) == value:
            return i
    return -1


def find_item(lst=None, key=None, value=None):
    index = find_index(lst, key, value)
    if index < 0:
        return {}
    return lst[index]


def find_matched_sub_list(lst=None, match_dict=None):
    print(f"Try to find the matched sub-list for a list against {match_dict}...")
    list_copy = copy.deepcopy(lst)
    # we must do reversely to avoid unexpected result on deleting by index
    for index in range(len(list_copy) - 1, -1, -1):
        print(f"working on the index {index} of the input list")
        dic = list_copy[index]
        for match_key, match_value in match_dict.items():
            if dic.get(match_key) != match_value:
                del list_copy[index]
                break
    if list_copy:
        print(f"{len(list_copy)} matched items are found from the input list.")
    else:
        print(f"no matched items are found from the input list.")
    return list_copy


def replace_list_new_value(lst=None, match_dict=None, replace_dict=None):
    logger.info(f"replace with {replace_dict} in list matching the input {match_dict}")
    for index, dic in enumerate(lst):
        logger.info(f"working on the index {index} of the input list")
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
    raise ValueError('file does not exist')


def save_json_file(file_path_name=None, content=None):
    print(f"writing {file_path_name} ...")
    make_dir(file_path_name=file_path_name)
    with open(file_path_name, 'w', newline='\n') as fp:
        json.dump(content, fp, indent=2)


def load_yaml_file(file_path_name=None):
    print(f"loading {file_path_name} ...")
    if Path(file_path_name).is_file():
        with open(file_path_name, 'r') as stream:
            return yaml.safe_load(stream)
    raise ValueError('file does not exist')


def save_yaml_file(file_path_name=None, content=None):
    print(f"writing {file_path_name} ...")
    make_dir(file_path_name=file_path_name)
    with open(file_path_name, 'w', newline='\n') as outfile:
        yaml.safe_dump(content, outfile, default_flow_style=False, sort_keys=False)


def make_dir(file_path_name=None):
    if not file_path_name:
        raise ValueError('file_path_name cannot be empty')
    p = Path(file_path_name).parent
    p.mkdir(parents=True, exist_ok=True)


# compare two lists, same returns True, otherwise returns False
def compare_lists(list1, list2):
    pairs = zip(list1, list2)
    # print(list(pairs))
    diff = [(x, y) for x, y in pairs if x != y]
    print('List difference: ' + str(diff))
    return not diff


# compare two dictionaries, same returns True, otherwise returns False
def compare_dicts(dict1, dict2):
    diff1 = {k: dict1[k] for k in dict1 if k not in dict2 or dict1[k] != dict2[k]}
    diff2 = {k: dict2[k] for k in dict2 if k not in dict1 or dict1[k] != dict2[k]}
    print('Dict difference: ' + str([diff1, diff2]))
    return dict1 == dict2


def compare_overwrite(data=None, local_file=None):
    if not Path(local_file).is_file():
        save_file(file_path_name=local_file, content=data)
        return
    if local_file.endswith(json_ext):
        local = load_json_file(local_file)
    elif local_file.endswith(yaml_exts):
        local = load_yaml_file(local_file)
    else:
        print(f'The file to be compared must be either {yaml_exts} or {json_ext} file. '
              f'Your file {local_file} is not one of them')
        return
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
            save_file(file_path_name=local_file, content=data)
            print(f'Your local file {local_file} was overwritten with the remote data')
        else:
            print('No overwritten happens')


def load_file(file_path_name=None):
    if file_path_name.endswith(json_ext):
        return load_json_file(file_path_name=file_path_name)
    elif file_path_name.endswith(yaml_exts):
        return load_yaml_file(file_path_name=file_path_name)
    else:
        print(f'The file to be loaded must be either {yaml_exts} or {json_ext} file. '
              f'Your file {file_path_name} is not one of them')


def save_file(file_path_name=None, content=None):
    if file_path_name.endswith(json_ext):
        save_json_file(file_path_name=file_path_name, content=content)
    elif file_path_name.endswith(yaml_exts):
        save_yaml_file(file_path_name=file_path_name, content=content)
    else:
        print(f'The file to be saved must be either {yaml_exts} or {json_ext} file.'
              f'Your file {file_path_name} is not one of them')
        return
    print(f'A new local file {file_path_name} was written')
