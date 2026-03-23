# Copyright (C) 2026 Apple Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1.  Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2.  Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY APPLE INC. AND ITS CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL APPLE INC. OR ITS CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import enum
import json
import os
from typing import Any, IO, Optional, Union


class Config(dict):
    class Mode(enum.Enum):
        JSON = enum.auto()
        YAML = enum.auto()

    CONTEXT_SYMBOL: str = '$context'

    @classmethod
    def pop(cls, collection: Union[list[Any], dict[Any, Any]], *args: Union[int, str]) -> Any:
        if isinstance(collection, list):
            return collection.pop(int(args[0])) if args else collection.pop(0)
        if isinstance(collection, dict):
            if not args:
                raise TypeError('pop() on a dict requires a key argument')
            return collection.pop(args[0])
        raise TypeError('pop() requires a list or dict')

    @classmethod
    def render(cls, value: Any, context: Optional[dict[str, Any]] = None) -> Any:
        import jsone
        from jsone.render import parse as jsone_parse

        def dynamic_pop(jsone_context: dict, collection: Union[list[Any], dict[Any, Any]], *args: Union[int, str]) -> Any:
            if isinstance(collection, list) and args and isinstance(args[0], str):
                filter_expr = args[0]
                for i, item in enumerate(collection):
                    subcontext = dict(jsone_context)
                    if isinstance(item, dict):
                        subcontext.update(item)
                    else:
                        subcontext['it'] = item
                    if jsone_parse(filter_expr, subcontext):
                        return collection.pop(i)
                raise ValueError(f'No item in list matches filter: {filter_expr!r}')
            return cls.pop(collection, *args)

        # Treat pop as a jsone built-in so we can apply a filter against it
        dynamic_pop._jsone_builtin = True

        context = dict(context or {})
        context.setdefault('pop', dynamic_pop)

        if not isinstance(value, dict):
            return jsone.render(value, context=context)

        if cls.CONTEXT_SYMBOL in value:
            result = Config()
            context = dict(**context)
            context.update(cls.render(value[cls.CONTEXT_SYMBOL], context=context))
            for key, content in value.items():
                if key == cls.CONTEXT_SYMBOL:
                    continue
                result[key] = cls.render(content, context=context)
                if isinstance(result[key], list):
                    context[key] = [x for x in result[key]]
                elif isinstance(result[key], dict):
                    result[key] = dict(**result[key])
                    context[key] = dict(**result[key])
                else:
                    context[key] = result[key]
            return result

        result = jsone.render(value, context=context)
        if isinstance(result, dict):
            return Config(**result)
        return result

    @classmethod
    def loads(cls, string: str, mode: Optional['Config.Mode'] = None) -> 'Config':
        if mode is cls.Mode.JSON:
            result = cls.render(json.loads(string))
        else:
            import yaml
            documents = list(yaml.safe_load_all(string))
            if not documents:
                result = cls()
            elif len(documents) == 1:
                result = cls.render(documents[0])
            else:
                data = {cls.CONTEXT_SYMBOL: documents[0]}
                for doc in documents[1:]:
                    if not isinstance(doc, dict):
                        raise TypeError('yaml sub-document is not a dictionary')
                    data.update(doc)
                print(data.keys())
                result = cls.render(data)
            mode = cls.Mode.YAML
        result.mode = mode
        return result

    @classmethod
    def load(cls, file: IO[str], mode: Optional['Config.Mode'] = None) -> 'Config':
        if mode is None and hasattr(file, 'name'):
            ext = os.path.splitext(file.name)[1].lower()
            if ext == '.json':
                mode = cls.Mode.JSON
            elif ext in ('.yaml', '.yml'):
                mode = cls.Mode.YAML
        result = cls.loads(file.read(), mode=mode)
        return result

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.mode: 'Config.Mode' = self.Mode.YAML

    def dumps(self, mode: Optional['Config.Mode'] = None, indent: int = 4) -> str:
        mode = mode or self.mode
        if mode is self.Mode.JSON:
            return json.dumps(dict(self), indent=indent)
        import yaml
        return yaml.dump(dict(self), indent=indent, default_flow_style=False)
