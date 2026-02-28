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

import copy
import enum
import json
import os
import re
import subprocess

from typing import Any, Dict, Optional
from unittest import mock


class Config(object):
    INDENT = 4
    IMPLICIT_VARIABLE_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')

    class Mode(enum.Enum):
        JSON = enum.auto()
        YAML = enum.auto()

    @classmethod
    def loads(cls, string, mode=None):
        if mode == cls.Mode.YAML or (mode is None and not string.strip().startswith(('{', "["))):
            import yaml
            data = yaml.safe_load(string) or {}
            return cls(data, mode=cls.Mode.YAML)
        else:
            data = json.loads(string)
            return cls(data, mode=cls.Mode.JSON)

    @classmethod
    def load(cls, file, mode=None):
        if isinstance(file, str):
            path = file
            if not os.path.exists(path):
                raise FileNotFoundError(f"Configuration file not found: {path}")

            if mode is None:
                ext = os.path.splitext(path)[1].lower()
                if ext == '.json':
                    mode = cls.Mode.JSON
                elif ext in ('.yaml', '.yml'):
                    mode = cls.Mode.YAML
                else:
                    raise ValueError(f"Cannot determine format from extension: {ext}")

            with open(path, 'r', encoding='utf-8') as f:
                if mode == cls.Mode.JSON:
                    data = json.load(f)
                else:
                    import yaml
                    data = yaml.safe_load(f) or {}
        else:
            if mode is None:
                if hasattr(file, 'name'):
                    ext = os.path.splitext(file.name)[1].lower()
                    if ext == '.json':
                        mode = cls.Mode.JSON
                    elif ext in ('.yaml', '.yml'):
                        mode = cls.Mode.YAML

                if mode is None:
                    raise ValueError("mode parameter required when loading from file object without inferrable extension")

            if mode == cls.Mode.JSON:
                data = json.load(file)
            else:
                import yaml
                data = yaml.safe_load(file) or {}

        return cls(data, mode=mode)

    @classmethod
    def _renderForeach(cls, template, context):
        from jsone.shared import TemplateError

        TOKEN = '$foreach'
        REQUIRED_KEYS = ('in', TOKEN)
        missing = [k for k in REQUIRED_KEYS if k not in template]
        extra = [k for k in template if k not in REQUIRED_KEYS]
        if missing:
            raise TemplateError(f"{TOKEN} is missing required keys: {missing}")
        if extra:
            raise TemplateError(f"{TOKEN} does not allow extra keys: {extra}")

        iterable = cls._renderValue(template[TOKEN], context)
        body = template['in']
        if isinstance(iterable, list):
            var_name = 'i'
            while var_name in context:
                var_name += '_'
            return [cls._renderValue(body, {**context, var_name: item}) for item in iterable]
        elif isinstance(iterable, dict):
            key_name = 'key'
            while key_name in context:
                key_name += '_'
            val_name = 'value'
            while val_name in context:
                val_name += '_'
            return [cls._renderValue(body, {**context, key_name: k, val_name: v}) for k, v in iterable.items()]
        else:
            raise TemplateError(f"{TOKEN} requires a list or dict value")

    @classmethod
    def _renderExec(cls, template, context):
        from jsone.shared import TemplateError

        TOKEN = '$exec'
        OPTIONAL_KEYS = ('type', 'allow_error')
        ALL_KEYS = (TOKEN,) + OPTIONAL_KEYS
        extra = [k for k in template if k not in ALL_KEYS]
        if extra:
            raise TemplateError(f"{TOKEN} does not allow extra keys: {extra}")

        command = cls._renderValue(template[TOKEN], context)
        output_type = template.get('type', 'str')
        allow_error = template.get('allow_error', False)

        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0 and not allow_error:
            raise TemplateError(f"{TOKEN} command failed with exit code {result.returncode}: {result.stderr.strip()}")
        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        if output_type in ('str', 'string'):
            return output
        elif output_type == 'int':
            return int(output)
        elif output_type == 'float':
            return float(output)
        elif output_type == 'json':
            return json.loads(output)
        elif output_type in ('yaml', 'yml'):
            import yaml
            return yaml.safe_load(output)
        elif output_type in ('bool', 'boolean'):
            return output.lower() in ('true', '1', 'yes')
        else:
            raise TemplateError(f"{TOKEN} unknown type: {output_type!r}")

    @classmethod
    def _renderValue(cls, template, context):
        from jsone.shared import string, TemplateError, JSONTemplateError, DeleteMarker
        from jsone.six import viewitems
        from jsone.render import IDENTIFIER_RE, interpolate, operators

        if isinstance(template, string):
            return interpolate(template, context)

        elif isinstance(template, dict):
            if '$_' in template:
                template = {('$eval' if k == '$_' else k): v for k, v in template.items()}

            if '$foreach' in template:
                return cls._renderForeach(template, context)

            if '$exec' in template:
                return cls._renderExec(template, context)

            matches = [k for k in template if k in operators]
            if matches:
                if len(matches) > 1:
                    raise TemplateError("only one operator allowed")
                try:
                    return operators[matches[0]](template, context)
                except JSONTemplateError:
                    if matches[0] == '$eval':
                        return None
                    raise

            def updated():
                local_context = dict(**context)
                for k, v in viewitems(template):
                    if k.startswith("$$"):
                        k = k[1:]
                    elif k.startswith("$") and IDENTIFIER_RE.match(k[1:]):
                        raise TemplateError("$<identifier> is reserved; use $$<identifier>")
                    else:
                        k = interpolate(k, local_context)

                    try:
                        v = cls._renderValue(v, local_context)
                    except JSONTemplateError as e:
                        if IDENTIFIER_RE.match(k):
                            e.add_location(".{}".format(k))
                        else:
                            e.add_location("[{}]".format(json.dumps(k)))
                        raise
                    if v is not DeleteMarker:
                        if cls.IMPLICIT_VARIABLE_RE.match(k):
                            local_context[k] = v
                        yield k, v

            return dict(updated())

        elif isinstance(template, list):

            def updated():
                for i, e in enumerate(template):
                    try:
                        v = cls._renderValue(e, context)
                        if v is not DeleteMarker:
                            yield v
                    except JSONTemplateError as e:
                        e.add_location("[{}]".format(i))
                        raise

            return list(updated())

        else:
            return template

    def __init__(self, data=None, mode=None, context=None):
        super().__init__()

        data = data or {}
        mode = mode or Config.Mode.JSON
        context = context or {}

        if not isinstance(data, (dict, list)):
            raise TypeError(f"data must be dict or list, not {type(data).__name__}")
        if not isinstance(mode, Config.Mode):
            raise TypeError(f"mode must be Config.Mode, not {type(mode).__name__}")
        if not isinstance(context, dict):
            raise TypeError(f"context must be dict, not {type(context).__name__}")

        self.mode = mode

        import jsone

        with mock.patch('jsone.renderValue', new=self._renderValue):
            self.data = jsone.render(data, context)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"Config({self.data!r}, mode={self.mode!r})"

    def __str__(self):
        if self.mode == Config.Mode.JSON:
            return json.dumps(self.data, indent=self.INDENT, ensure_ascii=False)
        elif self.mode == Config.Mode.YAML:
            import yaml
            return yaml.dump(self.data, default_flow_style=False, allow_unicode=True, indent=self.INDENT)
        else:
            raise NotImplemented

    def __eq__(self, other):
        if isinstance(other, Config):
            return self.data == other.data
        elif isinstance(other, (dict, list)):
            return self.data == other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def keys(self):
        if isinstance(self.data, dict):
            return self.data.keys()
        raise AttributeError("'Config' object has no attribute 'keys' (data is not a dict)")

    def values(self):
        if isinstance(self.data, dict):
            return self.data.values()
        raise AttributeError("'Config' object has no attribute 'values' (data is not a dict)")

    def items(self):
        if isinstance(self.data, dict):
            return self.data.items()
        raise AttributeError("'Config' object has no attribute 'items' (data is not a dict)")

    def get(self, key, default=None):
        if isinstance(self.data, dict):
            return self.data.get(key, default)
        raise AttributeError("'Config' object has no attribute 'get' (data is not a dict)")

    def append(self, value):
        if isinstance(self.data, list):
            return self.data.append(value)
        raise AttributeError("'Config' object has no attribute 'append' (data is not a list)")

    def extend(self, values):
        if isinstance(self.data, list):
            return self.data.extend(values)
        raise AttributeError("'Config' object has no attribute 'extend' (data is not a list)")

    def insert(self, index, value):
        if isinstance(self.data, list):
            return self.data.insert(index, value)
        raise AttributeError("'Config' object has no attribute 'insert' (data is not a list)")
