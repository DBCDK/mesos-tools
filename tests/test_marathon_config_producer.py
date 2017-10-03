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
