#!/usr/bin/env python3
# Copyright Dansk Bibliotekscenter a/s. Licensed under GPLv3
# See license text at https://opensource.dbc.dk/licenses/gpl-3.0

import argparse
import copy
import json
import os
import re
import sys

class ConfigException(Exception):
    pass

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="root of config directory")
    parser.add_argument("config_file", help="marathon json file")
    args = parser.parse_args()
    return args

def get_config_file(root_dir, config_name, exts=[".template", ".instance"]):
    for root, _, files in os.walk(root_dir):
        for f_path in files:
            for ext in exts:
                if f_path == config_name + ext:
                    return os.path.join(root, f_path)
    return None

def get_extending_config_data(root_dir, instance_json_data):
    if "extends" not in instance_json_data:
        return None
    extending_path = get_config_file(root_dir, instance_json_data["extends"])
    if extending_path is None:
        raise ConfigException("couldn't find template {} in root {}".format(
            instance_json_data["extends"], root_dir))
    with open(extending_path) as f:
        return json.load(f)

def iterate_extend_hierarchy(root_dir, config_path):
    with open(config_path) as f:
        json_data = json.load(f)
        extending_data = get_extending_config_data(root_dir, json_data)
        config_stack = []
        config_stack.append(json_data)
        while(extending_data is not None):
            config_stack.append(extending_data)
            extending_data = get_extending_config_data(root_dir, extending_data)
        return config_stack

def merge(src, dest):
    new_dest = copy.deepcopy(dest)
    for key in src:
        if key in dest:
            if isinstance(src[key], dict) and isinstance(dest[key], dict):
                new_dest[key] = merge(src[key], dest[key])
            else:
                new_dest[key] = src[key]
        else:
            new_dest[key] = src[key]
    return new_dest

def merge_config_stack(config_stack):
    dest = {}
    for data in config_stack[::-1]:
        if "changes" in data:
            dest = merge(data["changes"], dest)
        else:
            dest = merge(data, dest)
    return dest

def fill_template(template, **kwargs):
    for key, value in kwargs.items():
        # replace ${key} -> value
        template = re.sub("\${{{}}}".format(key), value, template)
    return template
