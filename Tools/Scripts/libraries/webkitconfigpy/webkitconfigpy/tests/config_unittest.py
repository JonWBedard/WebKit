# Copyright (C) 2026 Apple Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1.  Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
# 2.  Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY APPLE INC. AND ITS CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL APPLE INC. OR ITS CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import os
import tempfile
import unittest

from webkitconfigpy import Config


class ConfigTest(unittest.TestCase):
    def test_init_empty(self):
        config = Config()
        self.assertEqual(config.data, {})
        self.assertEqual(config.mode, Config.Mode.JSON)

    def test_init_with_dict(self):
        data = {'key': 'value', 'number': 42}
        config = Config(data)
        self.assertEqual(config.data, data)
        self.assertEqual(config.mode, Config.Mode.JSON)

    def test_init_with_list(self):
        data = [1, 2, 3, 4, 5]
        config = Config(data)
        self.assertEqual(config.data, data)
        self.assertEqual(config.mode, Config.Mode.JSON)

    def test_init_with_mode(self):
        config = Config({'key': 'value'}, mode=Config.Mode.YAML)
        self.assertEqual(config.mode, Config.Mode.YAML)

    def test_init_invalid_data_type(self):
        with self.assertRaises(TypeError) as cm:
            Config("invalid")
        self.assertIn("data must be dict or list", str(cm.exception))

    def test_init_invalid_mode_type(self):
        with self.assertRaises(TypeError) as cm:
            Config({}, mode="json")
        self.assertIn("mode must be Config.Mode", str(cm.exception))

    def test_mode_enum_values(self):
        self.assertIsInstance(Config.Mode.JSON.value, int)
        self.assertIsInstance(Config.Mode.YAML.value, int)
        self.assertNotEqual(Config.Mode.JSON.value, Config.Mode.YAML.value)

    def test_getitem_dict(self):
        config = Config({'key': 'value', 'number': 42})
        self.assertEqual(config['key'], 'value')
        self.assertEqual(config['number'], 42)

    def test_getitem_list(self):
        config = Config([10, 20, 30])
        self.assertEqual(config[0], 10)
        self.assertEqual(config[2], 30)

    def test_setitem_dict(self):
        config = Config({'key': 'value'})
        config['new_key'] = 'new_value'
        self.assertEqual(config['new_key'], 'new_value')

    def test_setitem_list(self):
        config = Config([1, 2, 3])
        config[1] = 99
        self.assertEqual(config[1], 99)

    def test_delitem_dict(self):
        config = Config({'key1': 'value1', 'key2': 'value2'})
        del config['key1']
        self.assertNotIn('key1', config)
        self.assertIn('key2', config)

    def test_delitem_list(self):
        config = Config([1, 2, 3])
        del config[1]
        self.assertEqual(list(config), [1, 3])

    def test_contains_dict(self):
        config = Config({'key': 'value'})
        self.assertIn('key', config)
        self.assertNotIn('missing', config)

    def test_contains_list(self):
        config = Config([1, 2, 3])
        self.assertIn(2, config)
        self.assertNotIn(99, config)

    def test_iter_dict(self):
        config = Config({'a': 1, 'b': 2, 'c': 3})
        keys = list(config)
        self.assertEqual(set(keys), {'a', 'b', 'c'})

    def test_iter_list(self):
        config = Config([10, 20, 30])
        self.assertEqual(list(config), [10, 20, 30])

    def test_len_dict(self):
        config = Config({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(len(config), 3)

    def test_len_list(self):
        config = Config([10, 20, 30, 40])
        self.assertEqual(len(config), 4)

    # Dict-specific methods tests
    def test_keys(self):
        config = Config({'a': 1, 'b': 2})
        self.assertEqual(set(config.keys()), {'a', 'b'})

    def test_keys_on_list_raises(self):
        config = Config([1, 2, 3])
        with self.assertRaises(AttributeError):
            config.keys()

    def test_values(self):
        config = Config({'a': 1, 'b': 2})
        self.assertEqual(set(config.values()), {1, 2})

    def test_values_on_list_raises(self):
        config = Config([1, 2, 3])
        with self.assertRaises(AttributeError):
            config.values()

    def test_items(self):
        config = Config({'a': 1, 'b': 2})
        self.assertEqual(set(config.items()), {('a', 1), ('b', 2)})

    def test_items_on_list_raises(self):
        config = Config([1, 2, 3])
        with self.assertRaises(AttributeError):
            config.items()

    def test_get(self):
        config = Config({'key': 'value'})
        self.assertEqual(config.get('key'), 'value')
        self.assertEqual(config.get('missing', 'default'), 'default')
        self.assertIsNone(config.get('missing'))

    def test_get_on_list_raises(self):
        config = Config([1, 2, 3])
        with self.assertRaises(AttributeError):
            config.get(0)

    def test_append(self):
        config = Config([1, 2, 3])
        config.append(4)
        self.assertEqual(list(config), [1, 2, 3, 4])

    def test_append_on_dict_raises(self):
        config = Config({'key': 'value'})
        with self.assertRaises(AttributeError):
            config.append('item')

    def test_extend(self):
        config = Config([1, 2, 3])
        config.extend([4, 5])
        self.assertEqual(list(config), [1, 2, 3, 4, 5])

    def test_extend_on_dict_raises(self):
        config = Config({'key': 'value'})
        with self.assertRaises(AttributeError):
            config.extend(['a', 'b'])

    def test_insert(self):
        config = Config([1, 2, 3])
        config.insert(1, 99)
        self.assertEqual(list(config), [1, 99, 2, 3])

    def test_insert_on_dict_raises(self):
        config = Config({'key': 'value'})
        with self.assertRaises(AttributeError):
            config.insert(0, 'item')

    def test_eq_with_dict(self):
        config = Config({'key': 'value', 'number': 42})
        self.assertEqual(config, {'key': 'value', 'number': 42})
        self.assertNotEqual(config, {'other': 'data'})

    def test_eq_with_list(self):
        config = Config([1, 2, 3])
        self.assertEqual(config, [1, 2, 3])
        self.assertNotEqual(config, [4, 5, 6])

    def test_eq_with_config(self):
        config1 = Config({'key': 'value'})
        config2 = Config({'key': 'value'})
        config3 = Config({'other': 'data'})
        self.assertEqual(config1, config2)
        self.assertNotEqual(config1, config3)

    def test_ne_with_dict(self):
        config = Config({'key': 'value'})
        self.assertTrue(config != {'other': 'data'})
        self.assertFalse(config != {'key': 'value'})

    # String representation tests
    def test_str_json_mode(self):
        config = Config({'key': 'value', 'number': 42}, mode=Config.Mode.JSON)
        output = str(config)
        # Should be valid JSON
        parsed = json.loads(output)
        self.assertEqual(parsed, {'key': 'value', 'number': 42})
        # Should be indented with 4 spaces
        self.assertIn('    ', output)

    def test_str_yaml_mode(self):
        config = Config({'key': 'value', 'number': 42}, mode=Config.Mode.YAML)
        output = str(config)
        # Should contain YAML-style output
        self.assertIn('key: value', output)
        self.assertIn('number: 42', output)

    def test_str_default_mode(self):
        config = Config({'key': 'value'})
        output = str(config)
        parsed = json.loads(output)
        self.assertEqual(parsed, {'key': 'value'})

    def test_repr(self):
        config = Config({'key': 'value'}, mode=Config.Mode.YAML)
        repr_str = repr(config)
        self.assertIn('Config', repr_str)
        self.assertIn('Mode.YAML', repr_str)

    def test_loads_json_explicit(self):
        json_str = '{"key": "value", "number": 42}'
        config = Config.loads(json_str, mode=Config.Mode.JSON)
        self.assertEqual(config.data, {'key': 'value', 'number': 42})
        self.assertEqual(config.mode, Config.Mode.JSON)

    def test_loads_yaml_explicit(self):
        yaml_str = 'key: value\nnumber: 42'
        config = Config.loads(yaml_str, mode=Config.Mode.YAML)
        self.assertEqual(config.data, {'key': 'value', 'number': 42})
        self.assertEqual(config.mode, Config.Mode.YAML)

    def test_loads_autodetect_json(self):
        json_str = '{"key": "value"}'
        config = Config.loads(json_str)
        self.assertEqual(config.mode, Config.Mode.JSON)
        self.assertEqual(config.data, {'key': 'value'})

    def test_loads_autodetect_json_array(self):
        json_str = '[1, 2, 3]'
        config = Config.loads(json_str)
        self.assertEqual(config.mode, Config.Mode.JSON)
        self.assertEqual(config.data, [1, 2, 3])

    def test_loads_autodetect_yaml(self):
        yaml_str = 'key: value\nother: data'
        config = Config.loads(yaml_str)
        self.assertEqual(config.mode, Config.Mode.YAML)
        self.assertEqual(config.data, {'key': 'value', 'other': 'data'})

    def test_loads_yaml_with_list(self):
        yaml_str = '- item1\n- item2\n- item3'
        config = Config.loads(yaml_str, mode=Config.Mode.YAML)
        self.assertEqual(config.data, ['item1', 'item2', 'item3'])
        self.assertEqual(config.mode, Config.Mode.YAML)

    def test_dollar_underscore_alias_for_eval(self):
        config = Config({'base': 'hello', 'derived': {'$_': 'base'}})
        self.assertEqual(config['derived'], 'hello')

    def test_dollar_underscore_unknown_variable_returns_none(self):
        config = Config({'value': {'$_': 'nonexistent'}})
        self.assertIsNone(config['value'])

    def test_dollar_underscore_and_eval_equivalent(self):
        config_eval = Config({'x': 42, 'y': {'$eval': 'x'}})
        config_us = Config({'x': 42, 'y': {'$_': 'x'}})
        self.assertEqual(config_eval['y'], config_us['y'])

    def test_dollar_underscore_nested(self):
        config = Config({'a': 'foo', 'b': {'inner': {'$_': 'a'}}})
        self.assertEqual(config['b']['inner'], 'foo')

    def test_foreach_basic(self):
        config = Config({'result': {'$foreach': [1, 2, 3], 'in': {'v': {'$_': 'i'}}}})
        self.assertEqual(config['result'], [{'v': 1}, {'v': 2}, {'v': 3}])

    def test_foreach_dynamic_list(self):
        config = Config({'items': ['a', 'b'], 'result': {'$foreach': {'$_': 'items'}, 'in': {'$_': 'i'}}})
        self.assertEqual(config['result'], ['a', 'b'])

    def test_foreach_empty_list(self):
        config = Config({'result': {'$foreach': [], 'in': {'$_': 'i'}}})
        self.assertEqual(config['result'], [])

    def test_foreach_nested_uses_i_underscore(self):
        config = Config({'result': {'$foreach': [[1, 2], [3]], 'in': {'$foreach': {'$_': 'i'}, 'in': {'$_': 'i_'}}}})
        self.assertEqual(config['result'], [[1, 2], [3]])

    def test_foreach_triple_nested_uses_i_double_underscore(self):
        config = Config({'result': {'$foreach': [[[10]]], 'in': {'$foreach': {'$_': 'i'}, 'in': {'$foreach': {'$_': 'i_'}, 'in': {'$_': 'i__'}}}}})
        self.assertEqual(config['result'], [[[10]]])

    def test_foreach_non_list_raises(self):
        with self.assertRaises(Exception):
            Config({'result': {'$foreach': 'not-a-list-or-dict', 'in': {'$_': 'i'}}})

    def test_foreach_missing_in_raises(self):
        with self.assertRaises(Exception):
            Config({'result': {'$foreach': [1, 2, 3]}})

    def test_foreach_extra_keys_raises(self):
        with self.assertRaises(Exception):
            Config({'result': {'$foreach': [1, 2, 3], 'in': {'$_': 'i'}, 'unexpected': True}})

    def test_foreach_dict_basic(self):
        config = Config({'result': {'$foreach': {'a': 1, 'b': 2}, 'in': {'k': {'$_': 'key'}, 'v': {'$_': 'value'}}}})
        self.assertEqual(config['result'], [{'k': 'a', 'v': 1}, {'k': 'b', 'v': 2}])

    def test_foreach_dict_dynamic(self):
        config = Config({'d': {'x': 10}, 'result': {'$foreach': {'$_': 'd'}, 'in': {'$_': 'value'}}})
        self.assertEqual(config['result'], [10])

    def test_foreach_dict_nested_uses_key_value_underscore(self):
        config = Config({'result': {'$foreach': {'a': {'p': 1}}, 'in': {'$foreach': {'$_': 'value'}, 'in': {'k': {'$_': 'key_'}, 'v': {'$_': 'value_'}}}}})
        self.assertEqual(config['result'], [[{'k': 'p', 'v': 1}]])

    def test_exec_basic(self):
        config = Config({'result': {'$exec': "python3 -c 'print(\"hello\")'"}})
        self.assertEqual(config['result'], 'hello')

    def test_exec_dynamic_command(self):
        config = Config({'cmd': "python3 -c 'print(\"world\")'", 'result': {'$exec': {'$_': 'cmd'}}})
        self.assertEqual(config['result'], 'world')

    def test_exec_type_int(self):
        config = Config({'result': {'$exec': "python3 -c 'print(42)'", 'type': 'int'}})
        self.assertEqual(config['result'], 42)
        self.assertIsInstance(config['result'], int)

    def test_exec_type_float(self):
        config = Config({'result': {'$exec': "python3 -c 'print(3.14)'", 'type': 'float'}})
        self.assertAlmostEqual(config['result'], 3.14)

    def test_exec_type_json(self):
        config = Config({'result': {'$exec': """python3 -c 'import json; print(json.dumps({"a": 1}))'""", 'type': 'json'}})
        self.assertEqual(config['result'], {'a': 1})

    def test_exec_type_bool_true(self):
        config = Config({'result': {'$exec': "python3 -c 'print(\"true\")'", 'type': 'bool'}})
        self.assertTrue(config['result'])

    def test_exec_type_bool_false(self):
        config = Config({'result': {'$exec': "python3 -c 'print(\"false\")'", 'type': 'bool'}})
        self.assertFalse(config['result'])

    def test_exec_allow_error_returns_none(self):
        config = Config({'result': {'$exec': "python3 -c 'import sys; sys.exit(1)'", 'allow_error': True}})
        self.assertIsNone(config['result'])

    def test_exec_error_raises(self):
        with self.assertRaises(Exception):
            Config({'result': {'$exec': "python3 -c 'import sys; sys.exit(1)'"}})

    def test_exec_extra_keys_raises(self):
        with self.assertRaises(Exception):
            Config({'result': {'$exec': "python3 -c 'print(1)'", 'unexpected': True}})

    def test_exec_unknown_type_raises(self):
        with self.assertRaises(Exception):
            Config({'result': {'$exec': "python3 -c 'print(1)'", 'type': 'bogus'}})
