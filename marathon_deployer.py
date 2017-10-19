#!/usr/bin/env python3
# Copyright Dansk Bibliotekscenter a/s. Licensed under GNU GPL v3
# See license text at https://opensource.dbc.dk/licenses/gpl-3.0
#
# -*- coding: utf-8 -*-
# -*- mode: python -*-

import argparse
import copy
import json
import logging
import sys
import time
import warnings

import os
import requests
from requests.packages.urllib3 import exceptions

logging.getLogger('Marathon').addHandler(logging.NullHandler())

class MarathonException(Exception):
    pass

class Marathon:
    """ Class for Mesos application orchestration using Marathon

        This class logs through a logger named 'Marathon'
    """

    def __init__(self, baseurl, access_token):
        self.baseurl = baseurl
        """ Marathon service base URL """
        self.cookies = {'access_token': access_token}
        """ Marathon service access token """
        self.logger = logging.getLogger('Marathon')

    def deploy(self, application):
        self.logger.debug("Deploying application with id '%s'", application['id'])
        current = self._get_application(application['id'])
        if current is None:
            self._create_application(application)
        else:
            # find resulting number of instances
            num_instances = self._get_number_of_expected_instances(application, current)
            if Marathon.is_update(application, current['app']):
                self._update_application(application, current['app']['version'],
                                         num_instances,
                                         scale_only=Marathon.is_scale_only_update(application, current['app']))
            else:
                self.logger.debug("comparison indicates that given %s causes no update of current %s", application,
                                  current['app'])
                self._restart_application(application, current['app']['version'], num_instances)
        self._wait_while_app_is_affected_by_deployment(application['id'])
        self.logger.info("deployment operation finished for %s", application['id'])

    def deploy_group(self, applications):
        if 'apps' not in applications or type(applications['apps']) != list:
            self.deploy(applications)
        else:
            for application in applications['apps']:
                application["id"] = self._merge_group_id_and_app_id(applications["id"], application["id"])
                self.logger.debug("Rewriting application id to: " + application['id'])
                self.deploy(application)

    def delete_group(self, group_name):
        response = http_get("/".join([self.baseurl, "v2",
            "groups", group_name]), self.cookies)
        try:
            js = response.json()
            if "groups" not in js:
                raise MarathonException("no groups found in reponse")
            stack = [js["groups"]]
            groups_to_delete = [group_name]
            while stack:
                groups = stack.pop()
                for group in groups:
                    if "groups" in group:
                        groups_to_delete.append(group["id"])
                        stack.append(group["groups"])
            for group in groups_to_delete[::-1]:
                # writing an empty group is necessary since marathon cannot
                # delete groups with content
                js = json.loads("{{\"id\": \"{}\", \"apps\": []}}".format(group))
                response = http_put("/".join([self.baseurl, "v2", "groups"]), js,
                    self.cookies, {"force": "true"})
                if response.status_code != requests.codes.OK:
                    raise MarathonException("{} error while deploying "
                        "empty group {} - {}".format(response.status_code,
                        group, response.text))
                response = http_delete("/".join([self.baseurl, "v2", "groups",
                    group]), self.cookies)
                if response.status_code != requests.codes.OK:
                    raise MarathonException("{} error while deleting group "
                        "{} - {}".format(response.status_code, group,
                        response.text))
        except ValueError as e:
            raise MarathonException("caught exception deleting group: {}"
                .format(str(e)))

    def _merge_group_id_and_app_id(self, group_id, application_id):
        self.logger.debug("Merging group id '%s' with application id '%s'", group_id, application_id)
        new_app_id = group_id
        if not new_app_id.endswith("/"):
            new_app_id += "/"
        slash_idx = application_id.rfind("/")
        if slash_idx > -1:
            new_app_id += application_id[slash_idx + 1:]
        else:
            new_app_id += application_id
        self.logger.debug("New application id '%s'", new_app_id)
        return new_app_id

    def _get_number_of_expected_instances(self, application, current):
        if 'instances' in application:
            num_instances = application['instances']
        else:
            num_instances = current['app']['instances']
        return num_instances

    def _wait_while_app_is_affected_by_deployment(self, application_id):
        self.logger.info("Waiting for app to be unaffected by deployments")
        affected = True
        while affected:
            response = http_get("/".join([self.baseurl, 'v2', 'deployments']), self.cookies)
            status_code = response.status_code
            if status_code != requests.codes.OK:
                raise Exception("{} error while fetching application {} - {}"
                                .format(status_code, application_id, response.text))
            active_deployments = json.loads(response.text)

            # Assume the app is not affected by any deployments
            affected = False
            # set boolean if the app actually is affected by a deployment
            for deployment in active_deployments:
                if application_id in deployment['affectedApps']:
                    affected = True
            time.sleep(1)
        return

    def _get_application(self, application_id):
        response = http_get("/".join([self.baseurl, 'v2', 'apps', application_id]), self.cookies)
        status_code = response.status_code
        if status_code == requests.codes.OK:
            return json.loads(response.text)
        elif status_code == requests.codes.NOT_FOUND:
            return None
        else:
            raise Exception("{} error while fetching application {} - {}"
                            .format(status_code, application_id, response.text))

    def _create_application(self, application):
        application_id = application['id']
        self.logger.info("creating application %s", application_id)
        response = http_post("/".join([self.baseurl, 'v2', 'apps']), application, self.cookies)
        status_code = response.status_code
        if status_code == requests.codes.OK or status_code == requests.codes.CREATED:
            deployment = json.loads(response.text)
            self._wait_for_new_application_version(application_id, deployment['version'])
            self._wait_for_application_instances(application_id, deployment['version'], application['instances'])
        else:
            raise Exception("{} error during creation of application {} - {}"
                            .format(status_code, application_id, response.text))

    def _update_application(self, application, old_version, num_instances, scale_only=False):
        application_id = application['id']
        self.logger.info("updating version '%s' of application %s. Scale_only: %s",
                         old_version, application_id, scale_only)
        response = http_put("/".join([self.baseurl, 'v2', 'apps', application['id']]), application,
                                     self.cookies)
        status_code = response.status_code
        if status_code == requests.codes.OK:
            deployment = json.loads(response.text)
            self._wait_for_new_application_version(application_id, deployment['version'])
            self._wait_for_application_instances(application_id, deployment['version'],
                                                 num_instances, scale_only)
        else:
            raise Exception("{} error during update of application {} - {}"
                            .format(status_code, application_id, response.text))

    def _restart_application(self, application, old_version, num_instances):
        application_id = application['id']
        self.logger.info("restarting version '%s' of application %s", old_version, application_id)
        response = http_post("/".join([self.baseurl, 'v2', 'apps', application['id'], 'restart']), None,
                                      self.cookies)
        status_code = response.status_code
        if status_code == requests.codes.OK:
            deployment = json.loads(response.text)
            self._wait_for_new_application_version(application_id, deployment['version'])
            self._wait_for_application_instances(application_id, deployment['version'], num_instances)
        else:
            raise Exception("{} error during restart of application {} - {}"
                            .format(status_code, application_id, response.text))

    def _wait_for_new_application_version(self, application_id, application_version):
        self.logger.info("waiting for version '%s' of application %s", application_version, application_id)
        while True:
            current = self._get_application(application_id)
            if current is not None and current['app']['version'] >= application_version:
                break
        return current

    def _wait_for_application_instances(self, application_id, application_version, application_instances,
                                        scale_only=False):
        self.logger.info("waiting for %s running instance(s) of application %s",
                         application_instances, application_id)
        while True:
            current = self._get_application(application_id)
            # If there are a different number of tasks than expected instances we are clearly not done.
            if len(current['app']['tasks']) != int(application_instances):
                time.sleep(1)
                continue
            instances_ok = 0
            for task in current['app']['tasks']:
                version_ok = True if scale_only else task['version'] >= application_version
                if task['appId'].startswith(application_id) \
                        and task['state'] == 'TASK_RUNNING' \
                        and Marathon.is_healthy(task) \
                        and version_ok:
                    instances_ok += 1
            if instances_ok == int(application_instances):
                break
            time.sleep(1)
        return current

    @staticmethod
    def is_scale_only_update(application, current):
        if 'instances' in application:
            if application['instances'] == current['instances']:
                return False
        else:
            return False
        application_copy = copy.deepcopy(application)
        application_copy['instances'] = current['instances']
        return not Marathon.is_update(application_copy, current)

    @staticmethod
    def is_update(application, current_app):
        app_copy = copy.deepcopy(application)
        if Marathon.is_port_update(app_copy, current_app):
            return True

        if 'ports' in app_copy:
            del app_copy['ports']
        if 'portDefinitions' in app_copy:
            del app_copy['portDefinitions']

        current_copy = copy.deepcopy(current_app)
        combined = Marathon.combine_dicts(current_copy, app_copy)
        return current_app != combined

    @staticmethod
    def is_port_update(application, current_app):
        if 'ports' in application:
            if 'ports' not in current_app:
                return True
            if len(application['ports']) != len(current_app['ports']):
                return True
            if application['ports'] != current_app['ports']:
                for (app_port, current_port) in zip(application['ports'], current_app['ports']):
                    if app_port != 0 and app_port != current_port:
                        return True
        if 'portDefinitions' in application:
            if 'portDefinitions' not in current_app:
                return True
            if len(application['portDefinitions']) != len(current_app['portDefinitions']):
                return True
            if application['portDefinitions'] != current_app['portDefinitions']:
                for (app_def, current_def) in zip(application['portDefinitions'], current_app['portDefinitions']):
                    app_def_copy = copy.deepcopy(app_def)
                    current_def_copy = copy.deepcopy(current_def)
                    if 'port' in app_def_copy and app_def_copy['port'] == 0:
                        app_def_copy['port'] = current_def_copy['port']
                    if current_def != Marathon.combine_dicts(current_def_copy, app_def_copy):
                        return True
        return False

    @staticmethod
    def combine_dicts(dst, src):
        """ combines src into dst """

        for key in src:
            if key in dst:
                if isinstance(dst[key], dict) and isinstance(src[key], dict):
                    Marathon.combine_dicts(dst[key], src[key])
                elif isinstance(dst[key], list) and isinstance(src[key], list):
                    dst[key] = Marathon.combine_lists(dst[key], src[key])
                else:
                    dst[key] = src[key]
            else:
                dst[key] = src[key]
        return dst

    @staticmethod
    def combine_lists(a_list, b_list):
        """ combines a and b lists into new list """

        if len(a_list) != len(b_list):
            return b_list
        combined = []
        for (a, b) in zip(a_list, b_list):
            if isinstance(a, dict) and isinstance(a, dict):
                combined.append(Marathon.combine_dicts(a, b))
            elif isinstance(a, list) and isinstance(b_list, list):
                combined.append(Marathon.combine_lists(a, b))
            else:
                combined.append(b)
        return combined

    @staticmethod
    def is_healthy(task):
        if 'healthCheckResults' in task:
            for result in task['healthCheckResults']:
                if not result['alive']:
                    return False
        return True

def http_post(url, json_data, cookies):
    return base_http_method(requests.post, url, cookies=cookies,
        json=json_data, verify=False, headers={'content-type':
        'application/json'})

def http_put(url, json_data, cookies, params=None):
    return base_http_method(requests.put, url, cookies=cookies,
        json=json_data, verify=False, params=params)

def http_get(url, cookies):
    return base_http_method(requests.get, url, cookies=cookies,
        verify=False)

def http_delete(url, cookies):
    return base_http_method(requests.delete, url, cookies=cookies,
        verify=False)

def base_http_method(method, url, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", exceptions.InsecureRequestWarning)
        return method(url, **kwargs)

def parse_args():
    parser = argparse.ArgumentParser(description='Script for Mesos application orchestration using Marathon')
    parser.add_argument('-b', '--baseurl', required=True, help='base URL of marathon service')
    parser.add_argument('-a', '--access-token', required=True, help='cookie for authentication on marathon')
    parser.add_argument("action", metavar="deploy|delete",
        help="\"deploy\" takes a marathon json file to deploy and "
            "\"delete\" takes a group name to delete as argument", nargs=2)
    return parser.parse_args()


def create_logger():
    logger = logging.getLogger('Marathon')
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to console handler
    console_handler.setFormatter(formatter)

    # add console_handler to logger
    logger.addHandler(console_handler)
    return logger


def main():
    args = parse_args()
    logger = create_logger()

    try:
        marathon = Marathon(args.baseurl, args.access_token)
        if args.action[0] == "deploy":
            with open(args.action[1]) as json_file:
                json_data = json.load(json_file)
                marathon.deploy_group(json_data)
        elif args.action[0] == "delete":
            marathon.delete_group(args.action[1])
    except Exception as e:
        logger.error(e, exc_info=True)
        sys.exit(1)

    sys.exit(os.EX_OK)


if __name__ == "__main__":
    main()
