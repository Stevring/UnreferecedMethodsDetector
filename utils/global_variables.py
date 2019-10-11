from collections import defaultdict

EP = "executable_path"
CL = "current_line"
CF = "current_file"
NL = "next_line"

class ObjectEntity(object):

    def __init__(self, name:str, base_method_list=None, base_property_list=None, base_protocol_list=None):
        self.name = name
        self.base_method_list = base_method_list or []
        self.property_list = base_property_list or []
        self.base_protocol_list = base_protocol_list or []

def _init():
    global _global_dict
    _global_dict = defaultdict(None)

def set(key:str, value):
    _global_dict[key] = value

def get(key:str):
    if(key == NL):
        _next_line()
    else:
        return _global_dict[key]

def _next_line():
    current_file = _global_dict.get(CF)
    if current_file:
        while True:
            try:
                line = current_file.readline()
                if not line:
                    _global_dict[CL] = None
                    break
                try:
                    _global_dict[CL] = line.decode('utf-8').strip()
                except:
                    _global_dict[CL] = line.strip()
                break
            except Exception as e:
                print(e)

    else:
        _global_dict[CL] = None