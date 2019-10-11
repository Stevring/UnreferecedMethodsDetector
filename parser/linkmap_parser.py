import re
import utils.global_variables as var
from utils.global_variables import NL, CL, CF, ObjectEntity
from collections import defaultdict
import logging
from typing import List, Set

object_file_start_line = "#Objectfiles:"
sections_start_line = "#Sections:"
symbols_start_line = '#Symbols:'

logger = logging.getLogger("linkmap_parser")
logger.setLevel(logging.INFO)

class LinkMapObjectEntity(ObjectEntity):

    def __init__(self, file_num: str, file_name, base_method_list=None):

        super().__init__(file_name, base_method_list)
        self.file_num = file_num


def parse_object_files(pod=None) -> List:
    object_file_line_pattern = re.compile("\[\s*(?P<file_num>\d+)\]\s+.+?\.a\((?P<file_name>\S+)\.o\)")
    var.get(NL)
    file_num_belongs_to_pod = []
    current_line = var.get(CL)  # type:str
    while current_line:
        if current_line.startswith("#"):
            break
        if pod and pod not in current_line:
            pass
        else:
            m = object_file_line_pattern.match(current_line)
            if m:
                file_num_belongs_to_pod.append(m.group('file_num'))
        var.get(NL)
        current_line = var.get(CL)
    return file_num_belongs_to_pod


def parse_symbols(file_num_to_consider:List[str]) -> Set[str]:
    var.get(NL)
    current_line = var.get(CL)
    assert current_line == "# Address	Size    	File  Name"
    var.get(NL)
    symbol_line_pattern = re.compile(".*?\[\s*(?P<file_num>\d+)\]\s*[\+-]\[(?P<obj_name>\S+)\s+(?P<method_name>\S+?)\]")
    current_line = var.get(CL)
    objects_name = set()
    while current_line:
        if current_line.startswith("#"):
            break
        else:
            m = symbol_line_pattern.match(current_line)
            if m and m.group('file_num') in file_num_to_consider:
                objects_name.add(m.group('obj_name'))
        var.get(NL)
        current_line = var.get(CL)
    return objects_name


def parse_link_map(lp, pod=None):
    var.set(CF, open(lp, 'r'))
    var.get(NL)
    current_line = var.get(CL) #type:str
    file_num_to_consider = None
    object_names = None

    while current_line:
        if current_line.startswith("#"):
            if current_line.replace(" ", '') == object_file_start_line:
                file_num_to_consider = parse_object_files(pod=pod)
            elif current_line.replace(" ", '') == symbols_start_line:
                assert file_num_to_consider
                object_names = parse_symbols(file_num_to_consider)
            else:
                var.get(NL)
        else:
            var.get(NL)
        current_line = var.get(CL)

    assert object_names
    return object_names


