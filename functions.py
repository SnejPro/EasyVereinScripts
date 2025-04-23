import json
import datetime
import os

def selective_merge(base_obj, delta_obj):
    if not isinstance(base_obj, dict):
        return delta_obj
    common_keys = set(base_obj).intersection(delta_obj)
    new_keys = set(delta_obj).difference(common_keys)
    for k in common_keys:
        base_obj[k] = selective_merge(base_obj[k], delta_obj[k])
    for k in new_keys:
        base_obj[k] = delta_obj[k]
    return base_obj

def config_get():
    with open("conf.defaults.json", "r") as config_defaults_file:
        config = json.loads(config_defaults_file.read())

    if os.path.exists("conf.json"):
        with open("conf.json", "r") as config_custom_file:
            config_custom = json.loads(config_custom_file.read())
            config = selective_merge(config, config_custom)
    
    return config