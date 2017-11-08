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

class StoreTemplateKeyValuePairsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if self.nargs is None:
            values = [values]
        for value in values:
            try:
                key, value = value.split("=")
                if getattr(namespace, self.dest) is None:
                    setattr(namespace, self.dest, {})
                getattr(namespace, self.dest)[key] = value
            except ValueError as e:
                setattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR, value)

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="root of config directory")
    parser.add_argument("action", metavar="single|group", nargs=2,
        help="produce a marathon config json file containing either a "
            "single application or a hierarchy of groups. \"single\" takes "
            "an instance json file and \"group\" takes a name for the "
            "top-level group as argument")
    parser.add_argument("-o", "--output",
        help="file to write resulting config json to, defaults to standard out",
        default="-")
    parser.add_argument("--template-keys", nargs="+",
        action=StoreTemplateKeyValuePairsAction,
        help="templated keys to replace with a given value. "
        "e.g. `--template-keys key=value` will replace ${key} with value")
    parser.add_argument("--flatten_hierarchy", action="store_true",
        help="flatten the hierarchy when producing a group json file. "
            "/parent/child/grandchild becomes parent-child-grandchild")
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

def merge_lists(src, dest):
    if not (isinstance(src, list) and isinstance(dest, list)):
        raise ConfigException("both source and destination must be lists.\n"
            "source type: {}\ndestination type: {}".format(type(src),
            type(dest)))
    new_dest = copy.deepcopy(dest)
    for element in src:
        # if the given element is an object with an override key, look for
        # an object in the destination list with a keyname corresponding to
        # the value specified by the override key and exchange the value of
        # the "value" field in the destination object with the value of the
        # "value" field in the source object.
        if isinstance(element, dict) and "override" in element:
            for dest_element in new_dest:
                if element["override"] in dest_element and dest_element[
                        element["override"]] == element[element["override"]]:

                    if not ("value" in element and "value" in dest_element):
                        raise ConfigException("source contains \"override\" "
                            "but \"value\" not found in either source or "
                            "destination.\nsrc: {}\ndest: {}".format(str(
                            element), str(dest_element)))

                    dest_element["value"] = element["value"]
                    break
        else:
            try:
                new_dest.index(element)
            except ValueError:
                # element is not in list
                new_dest.append(element)
    return new_dest

def merge(src, dest):
    new_dest = copy.deepcopy(dest)
    for key in src:
        if key in dest:
            if isinstance(src[key], dict) and isinstance(dest[key], dict):
                new_dest[key] = merge(src[key], dest[key])
            elif isinstance(src[key], list) and isinstance(dest[key], list):
                new_dest[key] = merge_lists(src[key], dest[key])
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

def make_config_json(root, config_file_path):
    try:
        config_stack = iterate_extend_hierarchy(root, config_file_path)
        config_json = merge_config_stack(config_stack)
        return config_json
    except json.decoder.JSONDecodeError as e:
        raise ConfigException("error decoding json file {}: {}".format(
            config_file_path, e))

def collect_instance_files(group_name, root_dir, template_keys=None,
        flat_hierarchy_compatibility=False):
    instances = []
    for root, _, files in os.walk(root_dir):
        for f_path in files:
            if f_path[-9:] == ".instance":
                instance = make_config_json(root_dir, os.path.join(root,
                    f_path))
                instances.append(instance)
    return make_hierarchy_dict(group_name, instances,
        flat_hierarchy_compatibility)

def make_hierarchy_dict(base, instances, flat_hierarchy_compatibility=False):
    group_dict = {"id": base, "groups": []}
    base_len = len([b for b in base.split("/") if b])
    for instance in instances:
        # keep track of where we are in the group dictionary object
        pos = group_dict

        # perhaps because of a bug in marathon, deployments of nested groups
        # doesn't seem to work. this could be related:
        # https://jira.mesosphere.com/browse/MARATHON-7433?page=com.atlassian.jira.plugin.system.issuetabpanels%3Aall-tabpanel
        # therefore, slashes are replaced with dashes to flatten the hierarchy
        if flat_hierarchy_compatibility:
            instance["id"] = replace_path_slashes(instance["id"])
            if "dependencies" in instance:
                instance["dependencies"] = [replace_path_slashes(d)
                    for d in instance["dependencies"]]
            base_len = 0

        id_parts = [i for i in instance["id"].split("/") if i][base_len:]
        parts_len = len(id_parts)
        # iterate over each level in the path to find if it already has a
        # group in the dictionary instance
        for i in range(parts_len):
            group_ids = [j["id"] for j in pos["groups"]]
            instance_id = id_parts[i]
            # if current path level is not in group dict and is not the
            # last part of the path
            if instance_id not in group_ids and i < parts_len - 1:
                new_group = {"id": id_parts[i], "groups": []}
                pos["groups"].append(new_group)
                pos = new_group
            # if current path level is the last part of the path
            elif instance_id not in group_ids and i == parts_len - 1:
                if "apps" not in pos:
                    pos["apps"] = [instance]
                else:
                    pos["apps"].append(instance)
            elif instance_id in group_ids:
                for group in pos["groups"]:
                    if instance_id == group["id"]:
                        pos = group
                        break
    return group_dict

def replace_path_slashes(app_id):
    return app_id.replace("/", "-").lstrip("-")

def format_output(config_json, template_keys=None):
    json_output = "{}\n".format(json.dumps(config_json, sort_keys=True,
        indent=4))
    if template_keys is not None:
        json_output = fill_template(json_output, **template_keys)
    return json_output

def main():
    args = setup_args()
    try:
        config_json = None
        if args.action[0] == "group":
            config_json = collect_instance_files(args.action[1], args.root,
                args.template_keys, args.flatten_hierarchy)
        elif args.action[0] == "single":
            if not os.path.isfile(args.action[1]):
                config_file = get_config_file(args.root, args.action[1])
                if config_file is None:
                    print("couldn't find config {}".format(config_file),
                        file=sys.stderr)
                    sys.exit(1)
                args.action[1] = config_file
            config_json = make_config_json(args.root, args.action[1])
        if config_json is None:
            print("couldn't make config json", file=sys.stderr)
            sys.exit(1)
        json_output = format_output(config_json, args.template_keys)
        if args.output == "-":
            sys.stdout.write(json_output)
        else:
            with open(args.output, "w") as output_file:
                output_file.write(json_output)
    except ConfigException as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
