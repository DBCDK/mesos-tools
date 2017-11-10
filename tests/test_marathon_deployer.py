#!/usr/bin/env python3
# Copyright Dansk Bibliotekscenter a/s. Licensed under GNU GPL v3
# See license text at https://opensource.dbc.dk/licenses/gpl-3.0
#
# -*- coding: utf-8 -*-
# -*- mode: python -*-

import copy
import json
import os
import unittest
from mesos_tools.marathon_deployer import Marathon


class TestMarathon(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_response.json'), 'r') as app_response:
            self.app_response = json.load(app_response)

    def test_is_update_identical(self):
        self.assertFalse(Marathon.is_update(self.app_response['app'], self.app_response['app']))

    def test_is_update_no_change_except_defaults(self):
        application = json.loads("""
        {
            "cmd": "env && python3 -m http.server $PORT0",
            "constraints": [
                ["net", "CLUSTER", "prod"],
                ["hostname", "UNIQUE"]
            ],
            "container": {
                "docker": {
                    "image": "docker.dbc.dk/dbc-python3:latest"
                },
                "type": "DOCKER"
            },
            "cpus": 0.25,
            "healthChecks": [
                {
                    "gracePeriodSeconds": 3,
                    "intervalSeconds": 10,
                    "maxConsecutiveFailures": 3,
                    "path": "/",
                    "portIndex": 0,
                    "protocol": "HTTP",
                    "timeoutSeconds": 5
                }
            ],
            "id": "/dev/mesos-tools/marathon-deployer-test-app",
            "instances": 3,
            "mem": 50,
            "ports": [
                0
            ],
            "upgradeStrategy": {
                "minimumHealthCapacity": 0.5,
                "maximumOverCapacity": 0.5
            }
        }
        """)
        self.assertFalse(Marathon.is_update(application, self.app_response['app']))

    def test_is_update_simple_change(self):
        self.assertTrue(Marathon.is_update({'mem': 42}, self.app_response['app']))

    def test_is_update_change_in_embedded_object(self):
        application = json.loads("""
        {
            "container": {
                "docker": {
                    "image": "my_new_python3_image"
                }
            }
        }
        """)
        self.assertTrue(Marathon.is_update(application, self.app_response['app']))

    def test_is_update_change_in_embedded_list(self):
        application = json.loads("""
        {
            "constraints": [
                ["net", "CLUSTER", "staging"],
                ["hostname", "UNIQUE"]
            ]
        }
        """)
        self.assertTrue(Marathon.is_update(application, self.app_response['app']))

    def test_is_update_change_in_embedded_object_in_embedded_list(self):
        application = json.loads("""
        {
            "healthChecks": [
                {
                    "gracePeriodSeconds": 3,
                    "intervalSeconds": 10,
                    "maxConsecutiveFailures": 3,
                    "path": "/newpath",
                    "portIndex": 0,
                    "protocol": "HTTP",
                    "timeoutSeconds": 5
                }
            ]            
        }
        """)
        self.assertTrue(Marathon.is_update(application, self.app_response['app']))

    def test_is_scale_only_update_true(self):
        application = json.loads("""
        {
            "id": "/dev/mesos-tools/marathon-deployer-test-app",
            "instances": 42
        }
        """)
        self.assertTrue(Marathon.is_scale_only_update(application, self.app_response['app']))

    def test_is_scale_only_update_false(self):
        application = json.loads("""
        {
            "id": "/dev/mesos-tools/marathon-deployer-test-app",
            "mem": 42,
            "instances": 42
        }
        """)
        self.assertFalse(Marathon.is_scale_only_update(application, self.app_response['app']))

    def test_is_port_update_no_ports_or_port_definitions(self):
        self.assertFalse(Marathon.is_port_update({}, self.app_response['app']))

    def test_is_port_update_identical(self):
        application = json.loads("""
        {
            "ports": [1, 2, 3],
            "portDefinitions": [
                {
                    "port": 1,
                    "protocol": "tcp"
                },
                {
                    "port": 2,
                    "protocol": "tcp"
                },
                {
                    "port": 3,
                    "protocol": "tcp"
                }
            ]
        }
        """)
        self.assertFalse(Marathon.is_port_update(application, application))

    def test_is_port_update_number_of_ports_differ(self):
        application = json.loads("""
        {
            "ports": [1, 2, 3]
        }
        """)
        current = copy.deepcopy(application)
        current['ports'].append(4)
        self.assertTrue(Marathon.is_port_update(application, current))

    def test_is_port_update_ports_values_differ(self):
        application = json.loads("""
        {
            "ports": [1, 2, 3]
        }
        """)
        current = json.loads("""
        {
            "ports": [1, 22, 3]
        }
        """)
        self.assertTrue(Marathon.is_port_update(application, current))

    def test_is_port_update_ports_zero_values_are_not_compared(self):
        application = json.loads("""
        {
            "ports": [1, 0, 3]
        }
        """)
        current = json.loads("""
        {
            "ports": [1, 2, 3]
        }
        """)
        self.assertFalse(Marathon.is_port_update(application, current))

    def test_is_port_update_number_of_port_definitions_differ(self):
        application = json.loads("""
        {
            "portDefinitions": [
                {
                    "port": 1,
                    "protocol": "tcp"
                }
            ]
        }
        """)
        current = copy.deepcopy(application)
        current['portDefinitions'].append({'port': 2})
        self.assertTrue(Marathon.is_port_update(application, current))

    def test_is_port_update_port_definition_values_differ(self):
        application = json.loads("""
        {
            "portDefinitions": [
                {
                    "port": 1,
                    "protocol": "tcp"
                },
                {
                    "port": 2,
                    "protocol": "tcp"
                }
            ]            
        }
        """)
        current = copy.deepcopy(application)
        current['portDefinitions'][1]['port'] = 22
        self.assertTrue(Marathon.is_port_update(application, current))

    def test_is_port_update_port_definitions_zero_port_values_are_not_compared(self):
        application = json.loads("""
        {
            "portDefinitions": [
                {
                    "port": 1,
                    "protocol": "tcp"
                },
                {
                    "port": 0,
                    "protocol": "tcp"
                }
            ]            
        }
        """)
        current = copy.deepcopy(application)
        current['portDefinitions'][1]['port'] = 22
        self.assertFalse(Marathon.is_port_update(application, current))
