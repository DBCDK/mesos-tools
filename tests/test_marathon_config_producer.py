#!/usr/bin/env python3
# Copyright Dansk Bibliotekscenter a/s. Licensed under GPLv3
# See license text at https://opensource.dbc.dk/licenses/gpl-3.0

import unittest

import marathon_config_producer

class TestConfigProducer(unittest.TestCase):
    def test_merge(self):
        src = {"a": 1, "b": 3, "c": 3}
        dest = {"a": 1, "b": 2, "d": 4}
        expected_result = {"a": 1, "b": 3, "c": 3, "d": 4}
        actual_result = marathon_config_producer.merge(src, dest)
        self.assertEqual(expected_result, actual_result)

    def test_merge_stack(self):
        # the order of the stack is significant, base must be at the end
        stack = [
            {"changes": {"b": {"c": 4}}},
            {"a": 1, "b": {"c": 2, "d": 3}}
        ]
        expected_result = {"a": 1, "b": {"c": 4, "d": 3}}
        actual_result = marathon_config_producer.merge_config_stack(stack)
        self.assertEqual(expected_result, actual_result)

    def test_fill_template(self):
        template = '{"a": "${key1}", "b": "${key2}"}'
        expected_result = '{"a": "value1", "b": "value2"}'
        actual_result = marathon_config_producer.fill_template(template,
            key1="value1", key2="value2")
        self.assertEqual(expected_result, actual_result)

    def test_merge_lists(self):
        src = {"a": [
            {
                "key": "key1",
                "value": "blah",
                "override": "key"
            },
            {
                "key": "key3",
                "value": "value3"
            }]}
        dest = {"a": [
            {
                "key": "key1",
                "value": "value1"
            },
            {
                "key": "key2",
                "value": "value2"
            }]}
        expected_result = {"a": [
            {
                "key": "key1",
                "value": "blah"
            }, {
                "key": "key2",
                "value": "value2"
            }, {
                "key": "key3",
                "value": "value3"
            }]}
        actual_result = marathon_config_producer.merge(src, dest)
        self.assertEqual(expected_result, actual_result)

    def test_merge_lists_no_value_throws_exception(self):
        src = [
            {
                "key": "key",
                "value": "value",
                "override": "key"
            }]
        dest = [
            {
                "key": "key",
                "value1": "value1"
            }]
        with self.assertRaises(marathon_config_producer.ConfigException):
            marathon_config_producer.merge_lists(src, dest)

    def test_merge_lists_not_list_throws_exception(self):
        src = {}
        dest = []
        with self.assertRaises(marathon_config_producer.ConfigException):
            marathon_config_producer.merge_lists(src, dest)

    def test_make_hierarchy(self):
        instances = [
            {
                "id": "/parent/child1/instance1",
                "container": {}
            },
            {
                "id": "/parent/child2/instance2",
                "container": {}
            }
        ]
        expected_result = {
            "id": "parent",
            "groups": [
                {
                    "id": "child1",
                    "groups": [],
                    "apps": [
                        {
                            "id": "/parent/child1/instance1",
                            "container": {}
                        }
                    ]
                },
                {
                    "id": "child2",
                    "groups": [],
                    "apps": [
                        {
                            "id": "/parent/child2/instance2",
                            "container": {}
                        }
                    ]
                }
            ]
        }
        actual_result = marathon_config_producer.make_hierarchy_dict(
            "parent", instances, False)
        self.assertEqual(expected_result, actual_result)

    def test_make_hierarchy_flat_hierarchy(self):
        instances = [
            {
                "id": "/parent/child1/instance1",
                "container": {}
            },
            {
                "id": "/parent/child2/instance2",
                "container": {}
            }
        ]
        expected_result = {
            "id": "parent",
            "apps": [
                {
                    "id": "parent-child1-instance1",
                    "container": {}
                },
                {
                    "id": "parent-child2-instance2",
                    "container": {}
                }
            ],
            "groups": []
        }
        actual_result = marathon_config_producer.make_hierarchy_dict(
            "parent", instances, True)
        self.assertEqual(expected_result, actual_result)
