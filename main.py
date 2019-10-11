
import sys
from os.path import abspath, expanduser, exists
import logging
from typing import List, Dict
from collections import defaultdict
import json


from parser.otool_parser import parse_class_list, parse_referenced_methods
import utils.global_variables as var
from utils.global_variables import ObjectEntity, EP

# TODO: 过滤 delegate [系统+项目] 的方法
# TODO:

def pick_out_unreferenced(class_objects:Dict[str, ObjectEntity], referenced_methods):
    methods_to_class = defaultdict(list)
    for key, value in class_objects.items():
        for method in value.base_method_list:
            methods_to_class[method].append(key)
            value.unreferenced_method_list = []
    implemented_methods = set(methods_to_class.keys())
    referenced_methods = set(referenced_methods)
    unreferenced_methods = implemented_methods.difference(referenced_methods)
    result = defaultdict(list)
    for unreferenced_method in unreferenced_methods:
        for class_name in methods_to_class[unreferenced_method]:
            result[class_name].append(unreferenced_method)
    return result

def synthesizeProperty(some_obj):
    for x in some_obj.property_list:
        flag = False
        get_method = x
        set_method = 'set' + x[0].upper() + x[1:] + ':'
        if get_method in some_obj.base_method_list:
            yield get_method
            flag = True
        if set_method in some_obj.base_method_list:
            yield set_method
            flag = True
        if not flag:
            logging.info(f'property {x} is not synthesized for {some_obj.name}')


def remove_empty(name_to_unreferenced:Dict[str, List[str]]):
    to_remove_keys = []
    for key, value in name_to_unreferenced.items():
        if len(value) == 0:
            to_remove_keys.append(key)
    for key in to_remove_keys:
        name_to_unreferenced.pop(key, None)


def post_process(name_to_unreferenced:Dict[str, List[str]]):
    import re
    if args['ignore_method_file']:
        with open(args['ignore_method_file'], 'r') as f:
            for line in f.readlines():
                line = line.strip()
                p = re.compile(line)
                for key, value in name_to_unreferenced.items():
                    name_to_unreferenced[key] = [x for x in value if not p.match(x)]
    if args['ignore_class_file']:
        to_remove_keys = []
        with open(args['ignore_class_file'], 'r') as f:
            for line in f.readlines():
                line = line.strip()
                p = re.compile(line)
                for key in name_to_unreferenced.keys():
                    if p.match(key):
                        to_remove_keys.append(key)
        for key in to_remove_keys:
            name_to_unreferenced.pop(key, None)

    remove_empty(name_to_unreferenced)
    return name_to_unreferenced


def process_file_path(file_path:str, not_provided_msg=None, invalid_msg=None):
    if not_provided_msg:
        assert file_path, not_provided_msg
    if file_path:
        file_path = abspath(expanduser(file_path))
        if invalid_msg:
            assert exists(file_path), invalid_msg
    return file_path

def remove_delegate_methods(objects:Dict[str, ObjectEntity]):
    pass

def main():
    from parser.linkmap_parser import parse_link_map
    otool_class_objects = parse_class_list(args['macho_file']) #type:Dict[str, ObjectEntity]
    pod_objects_name = parse_link_map(args['linkmap_file'], args['pod'])
    referenced = parse_referenced_methods(args['macho_file'])
    # remove objects not in pods
    object_names_to_remove = set(otool_class_objects.keys()).difference(pod_objects_name)
    for object_name_to_remove in object_names_to_remove:
        otool_class_objects.pop(object_name_to_remove)
    # remove getter and setter methods
    for obj_name in pod_objects_name:
        if obj_name in otool_class_objects:
            for property_method in synthesizeProperty(otool_class_objects[obj_name]):
                try:
                    otool_class_objects[obj_name].base_method_list.remove(property_method)
                except:
                    logging.info(f"{property_method} in otool, not in linkmap")
    r = pick_out_unreferenced(otool_class_objects, referenced)
    remove_delegate_methods(otool_class_objects)
    post_process(r)
    print("total class num: ", len(r))
    print("total method num: ", sum([len(method_list) for method_list in r.values()]))
    json.dump(r, open(args['output_file'] or "unreferenced.json", 'w'), indent=4)

if __name__ == '__main__':
    with open("configuration/config.json", 'r') as f:
        args = json.load(f)

    args['macho_file'] = process_file_path(args['macho_file'], not_provided_msg="Please set a macho file to analyze",
                                           invalid_msg="Please set a valid macho file")
    args['linkmap_file'] = process_file_path(args['linkmap_file'], not_provided_msg="Please set a link map file to analyze",
                                              invalid_msg="Please set a valid link map file")
    args['ignore_method_file'] = process_file_path(args['ignore_method_file'])
    args['ignore_class_file'] = process_file_path(args['ignore_class_file'])
    args['output_file'] = process_file_path(args['output_file'], not_provided_msg="Please specify an output file")

    var._init()
    var.set(EP, args['macho_file'])
    main()
