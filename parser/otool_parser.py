from collections import namedtuple
import re
import logging
from typing import List
import subprocess
import os.path

import utils.global_variables as var
from utils.global_variables import CL, CF, NL, ObjectEntity



isa = "isa"
superClass = "superClass"
cache = "cache"
vtable = "vtable"
data = "data"
if data:
    # inside data
    data_Swift = "Swift"
    data_flags = "flags"
    data_RO_META = "RO_META"
    data_RO_ROOT = "RO_ROOT"
    data_RO_HAS_CXX_STRUCTORS = "RO_HAS_CXX_STRUCTORS"
    data_instanceStart = "instanceStart"
    data_instanceSize = "instanceSize"
    data_ivarLayout = "ivarLayout"
    data_name = "name"
    data_baseMethods = "baseMethods"
    data_baseProtocols = "baseProtocols"
    if data_baseProtocols:
        data_baseProtocols_count = "count"
        data_baseProtocols_list = "list"
        data_baseProtocols_isa = "isa"
        data_baseProtocols_name = "name"
        data_baseProtocols_protocols = "protocols"
        data_baseProtocols_instanceMethods = "instanceMethods"
        data_baseProtocols_classMethods = "classMethods"
        data_baseProtocols_optionalInstanceMethods = "instanceMethods"
        data_baseProtocols_optionalClassMethods = "classMethods"
        data_baseProtocols_instanceProperties = "instanceProperties"
ivars = 'ivars'
weakIvarLayout = "weakIvarLayout"
baseProperties = "baseProperties"


# general

#layout map
layout_map = "layout map:"

# method_list
method_list_entsize = "entsize"
method_list_count = "count"
# inside a single method
method_list_name = "name"
method_list_types = "types"
method_list_imp = "imp"

# ivar_list
ivar_entsize = "entsize"
ivar_count = "count"
# inside a single ivar
ivar_offset = "offset"
ivar_name = "name"
ivar_type = "type"
ivar_alignment = "alignment"
ivar_size = "size"

# property_list
property_list_entsize = "entsize"
property_list_count = "count"
# inside a single property
property_list_name = 'name'
property_list_attributes = "attributes"


property_line_pattern = re.compile("^[a-zA-Z]+?Properties")
new_section_pattern = re.compile("^Contents of \((?P<segname>.*?),(?P<sectname>.*?)\) section$")
new_class_pattern = re.compile("[0-9a-f]{16} 0x[0-9a-f]{9}")


def _move_to_seg_and_sect(seg, sect):
    current_line = var.get(CL)
    while current_line:
        m = new_section_pattern.match(current_line)
        if m and m.group('segname') == seg and m.group('sectname') == sect:
            var.get(NL)
            return
        var.get(NL)
        current_line = var.get(CL)
    raise Exception(f'segment: {seg} section: {sect} not found')


def _parse_method_list(class_name) -> list:
    current_line = var.get(CL)
    r = []
    if current_line.startswith("entsize"):
        var.get(NL)
        current_line = var.get(CL)
        assert current_line.startswith("count")
        count = int(current_line.split(" ")[-1])
        var.get(NL)
        while count > 0:
            current_line = var.get(CL)
            assert current_line.startswith("name"), f"error with class {class_name}"
            method_name = current_line.split()[-1]
            r.append(method_name)
            var.get(NL)
            assert var.get(CL).startswith("types"), f"error with class {class_name}"
            var.get(NL)
            assert var.get(CL).startswith("imp"), f"error with class {class_name}"
            var.get(NL)
            count -= 1
    return r


def _parse_property_list(class_name) -> List:
    current_line = var.get(CL)
    r = []
    if current_line.startswith("entsize"):
        var.get(NL)
        current_line = var.get(CL)
        assert current_line.startswith("count")
        count = int(current_line.split(" ")[-1])
        var.get(NL)
        while count > 0:
            current_line = var.get(CL)
            assert current_line.startswith("name"), f"error with class {class_name}"
            property_name = current_line.split(' ')[-1]
            r.append(property_name)
            var.get(NL)
            assert var.get(CL).startswith("attributes"), f"error with class {class_name}"
            var.get(NL)
            count -= 1
    return r


def _parse_protocol_list(class_name: object) -> object:
    current_line = var.get(CL)
    r = []
    if not current_line.startswith(data_baseProtocols_count):
        return r
    count = int(current_line.split(' ')[-1])
    var.get(NL)
    while count > 0:
        var.get(NL)
        var.get(NL)
        current_line = var.get(CL)
        assert current_line.startswith(data_baseProtocols_name)
        r.append(current_line.split(' ')[-1])
        while not current_line.startswith(data_baseProtocols_instanceProperties):
            var.get(NL)
            current_line = var.get(CL)
        var.get(NL)
        current_line = var.get(CL)
        count -= 1
    assert current_line.startswith(ivars)
    return r


def _parse_implemented_class() -> ObjectEntity:

    var.get(NL)
    name = None
    base_method_list = []
    base_properties = []
    base_protocols = []
    while True:
        current_line = var.get(CL) #type:str
        if (not name) and current_line.startswith("name"):
            name = current_line.split(' ')[-1]
            var.get(NL)
        elif current_line.startswith("baseMethods"):
            assert name, f"error with line {current_line}"
            var.get(NL)
            base_method_list += _parse_method_list(name)
        elif current_line.startswith("baseProperties"):
            assert name, f"error with line {current_line}"
            var.get(NL)
            base_properties += _parse_property_list(name)
        elif current_line.startswith(data_baseProtocols):
            var.get(NL)
            base_protocols = _parse_protocol_list(name)
        elif new_class_pattern.match(current_line) or new_section_pattern.match(current_line):
            break
        else:
            var.get(NL)
    return ObjectEntity(name=name,
                        base_method_list=base_method_list,
                        base_property_list=base_properties,
                        base_protocol_list=base_protocols)



def parse_class_list(ep) -> dict:
    current_file = subprocess.Popen(['otool', '-oV', ep],
                                    stdout=subprocess.PIPE).stdout
    var.set(CF, current_file)
    var.get(NL)
    _move_to_seg_and_sect('__DATA', '__objc_classlist')
    class_objects = {}
    current_line = var.get(CL)
    while current_line:
        if new_class_pattern.match(current_line):
            class_object = _parse_implemented_class()
            class_objects[class_object.name] = class_object
        elif new_section_pattern.match(current_line):
            break
        else:
            var.get(NL)
        current_line = var.get(CL)
    return class_objects


def parse_referenced_methods(ep) -> List:
    current_file = subprocess.Popen(['otool', '-v', '-s', '__DATA', '__objc_selrefs', ep],
                                    stdout=subprocess.PIPE).stdout
    var.set(CF, current_file)
    var.get(NL)
    _move_to_seg_and_sect('__DATA', '__objc_selrefs')
    referenced_methods = []
    pattern = re.compile("[0-9a-f]{16}\s*__TEXT:__objc_methname:(?P<method>\S+)")
    current_line = var.get(CL)
    while current_line:
        m = pattern.match(current_line)
        if m:
            referenced_methods.append(m.group("method"))
            # logger.info(f"method {referenced_methods[-1]} referenced")
        var.get(NL)
        current_line = var.get(CL)
    return referenced_methods





