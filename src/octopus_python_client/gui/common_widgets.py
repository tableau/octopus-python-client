import copy
import logging
import tkinter as tk
from tkinter import ttk

from octopus_python_client.common import id_key, name_key
from octopus_python_client.utilities.helper import find_item

logger = logging.getLogger(__name__)


class CommonWidgets:
    COMBOBOX_VALUES_KEY = "values"
    HEIGHT_7 = 7
    READ_ONLY = "readonly"
    ROW_0 = 0
    ROW_1 = 1
    ROW_SIZE = 5
    SELECTED = "1"
    SPAN_1 = 1
    SPAN_2 = 2
    SPAN_3 = 3
    UNSELECTED = "0"
    WIDTH_10 = 10
    WIDTH_20 = 20
    WIDTH_40 = 40
    WIDTH_80 = 80
    WIDTH_120 = 120

    # this is for list of strings
    @staticmethod
    def set_radio_names_frame(parent, list_names: list, default_name: str = None, title="Select one: "):
        names_frame = tk.Frame(parent)
        tk.Label(names_frame, text=title, bd=2) \
            .grid(row=CommonWidgets.ROW_0, columnspan=CommonWidgets.ROW_SIZE, sticky=tk.W)
        name_var = tk.StringVar()
        list_names_copy = copy.deepcopy(list_names)
        list_names_copy.sort()
        if default_name and default_name in list_names_copy:
            name_var.set(default_name)
        else:
            name_var.set(list_names_copy[0])
        for index, name in enumerate(list_names_copy):
            tk.Radiobutton(names_frame, text=f"{name}", variable=name_var, value=name, justify=tk.LEFT,
                           command=lambda *args: None) \
                .grid(row=CommonWidgets.ROW_1 + int(index / CommonWidgets.ROW_SIZE),
                      column=index % CommonWidgets.ROW_SIZE, sticky=tk.W)  # , columnspan=1
        names_frame.grid(sticky=tk.W)
        return name_var

    # this is for items like Id: Projects-1234 and Name: ProjectName
    @staticmethod
    def set_radio_items_frame(parent, list_items: list, default_id: str = None, title="Select one: "):
        items_frame = tk.Frame(parent)
        tk.Label(items_frame, text=title, bd=2) \
            .grid(row=CommonWidgets.ROW_0, columnspan=CommonWidgets.ROW_SIZE, sticky=tk.W)
        id_var = tk.StringVar()
        list_items_copy = copy.deepcopy(list_items)
        list_items_copy.sort(key=lambda one_item: one_item.get(name_key).lower())
        item = find_item(lst=list_items_copy, key=id_key, value=default_id)
        if item:
            id_var.set(default_id)
        else:
            id_var.set(list_items_copy[0].get(id_key))
        for index, item in enumerate(list_items_copy):
            tk.Radiobutton(items_frame, text=f"{item.get(name_key)}", variable=id_var, value=item.get(id_key),
                           justify=tk.LEFT, command=lambda *args: None) \
                .grid(row=CommonWidgets.ROW_1 + int(index / CommonWidgets.ROW_SIZE),
                      column=index % CommonWidgets.ROW_SIZE, sticky=tk.W)  # , columnspan=1
        items_frame.grid(sticky=tk.W)
        return id_var

    @staticmethod
    def select_all_or_none(keys_list: list, keys_var_dict: dict, is_select: bool = True):
        for key in keys_list:
            keys_var_dict.get(key).set(CommonWidgets.SELECTED if is_select else CommonWidgets.UNSELECTED)

    @staticmethod
    def set_title_select_deselect_all(parent_frame, keys_list: list, keys_var_dict: dict, title: str = "Select: "):
        tk.Label(parent_frame, text=title, bd=2) \
            .grid(row=CommonWidgets.ROW_0, sticky=tk.W, columnspan=CommonWidgets.SPAN_3)
        tk.Button(
            parent_frame, text='Select all',
            command=lambda: CommonWidgets.select_all_or_none(
                keys_list=keys_list, keys_var_dict=keys_var_dict, is_select=True)) \
            .grid(row=CommonWidgets.ROW_0, column=CommonWidgets.SPAN_3, sticky=tk.W, columnspan=CommonWidgets.SPAN_1)
        tk.Button(
            parent_frame, text='Deselect all',
            command=lambda: CommonWidgets.select_all_or_none(
                keys_list=keys_list, keys_var_dict=keys_var_dict, is_select=False)) \
            .grid(row=CommonWidgets.ROW_0, column=CommonWidgets.SPAN_3 + CommonWidgets.SPAN_1, sticky=tk.W,
                  columnspan=CommonWidgets.SPAN_1)

    @staticmethod
    def set_each_check_box(parent_frame, check_box_name: str, check_box_key: str, keys_var_dict: dict, index: int,
                           default_boxes: list):
        keys_var_dict[check_box_key] = tk.StringVar()
        tk.Checkbutton(parent_frame, text=check_box_name, variable=keys_var_dict.get(check_box_key)) \
            .grid(row=int(CommonWidgets.ROW_1 + index / CommonWidgets.ROW_SIZE),
                  column=index % CommonWidgets.ROW_SIZE, sticky=tk.W)
        if check_box_key in default_boxes:
            keys_var_dict.get(check_box_key).set(CommonWidgets.SELECTED)
        else:
            keys_var_dict.get(check_box_key).set(CommonWidgets.UNSELECTED)

    @staticmethod
    def set_check_names_frame(parent, list_names: list, default_names: list = None, title="Select:"):
        if default_names is None:
            default_names = []
        names_var_dict = {}
        names_frame = tk.Frame(parent)
        list_names_copy = copy.deepcopy(list_names)
        list_names_copy.sort()
        CommonWidgets.set_title_select_deselect_all(
            names_frame, keys_list=list_names_copy, keys_var_dict=names_var_dict, title=title)
        for index, name in enumerate(list_names_copy):
            CommonWidgets.set_each_check_box(
                names_frame, check_box_name=name, check_box_key=name, keys_var_dict=names_var_dict, index=index,
                default_boxes=default_names)
        names_frame.grid(sticky=tk.W)
        return names_var_dict

    @staticmethod
    def set_check_items_frame(parent, items_list: list, default_ids: list = None, title="Select:"):
        if default_ids is None:
            default_ids = []
        ids_var_dict = {}
        items_frame = tk.Frame(parent)
        items_list_copy = copy.deepcopy(items_list)
        items_list_copy.sort(key=lambda one_item: one_item.get(name_key).lower())
        ids_list = [item.get(id_key) for item in items_list_copy]
        CommonWidgets.set_title_select_deselect_all(
            items_frame, keys_list=ids_list, keys_var_dict=ids_var_dict, title=title)
        for index, item in enumerate(items_list_copy):
            CommonWidgets.set_each_check_box(
                items_frame, check_box_name=item.get(name_key), check_box_key=item.get(id_key),
                keys_var_dict=ids_var_dict, index=index, default_boxes=default_ids)
        items_frame.grid(sticky=tk.W)
        return ids_var_dict

    @staticmethod
    def set_combobox_items_frame(parent, texts_list: list, bind_func, default_text: str = None,
                                 title: str = "Select: ", width=WIDTH_80):
        text_var = tk.StringVar()
        if not texts_list:
            return text_var
        items_frame = tk.Frame(parent)
        tk.Label(items_frame, text=title, bd=2).grid(sticky=tk.W)
        item_combobox = ttk.Combobox(items_frame, width=width, textvariable=text_var)
        texts_list_copy = copy.deepcopy(texts_list)
        item_combobox[CommonWidgets.COMBOBOX_VALUES_KEY] = tuple(texts_list_copy)
        default_index = 0
        for index, text in enumerate(texts_list_copy):
            if text == default_text:
                default_index = index
        item_combobox.current(default_index)
        item_combobox.grid(sticky=tk.W)
        item_combobox.bind("<<ComboboxSelected>>", bind_func)
        items_frame.grid(sticky=tk.W)
        return text_var

    @staticmethod
    def directional_separator(parent, title: str):
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(sticky=tk.EW)
        tk.Label(parent, text=f"\u21D3     \u21D3     \u21D3     \u21D3     \u21D3      {title}"
                              f"      \u21D3     \u21D3     \u21D3     \u21D3     \u21D3",
                 bd=2, relief="groove").grid(sticky=tk.EW)
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(sticky=tk.EW)

    @staticmethod
    def set_text_entry(parent, title: str, text_var: tk.StringVar):
        tk.Label(parent, text=title).grid(sticky=tk.W)
        text_entry = tk.Entry(parent, width=CommonWidgets.WIDTH_120, textvariable=text_var)
        text_entry.grid(sticky=tk.W)
        return text_entry
