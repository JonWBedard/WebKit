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
import unittest

from webkitconfigpy import Config


def discover_fixture_pairs(files_dir):
    if not os.path.exists(files_dir):
        return []

    pairs = []
    for filename in sorted(os.listdir(files_dir)):
        if '-expected' in filename:
            continue
        base, ext = os.path.splitext(filename)
        if ext not in ['.json', '.yaml', '.yml']:
            continue

        expected_filename = f"{base}-expected{ext}"
        template_path = os.path.join(files_dir, filename)
        expected_path = os.path.join(files_dir, expected_filename)

        if os.path.exists(expected_path):
            test_name = f"test_{base.replace('-', '_').replace('.', '_')}"
            pairs.append((template_path, expected_path, test_name))

    return pairs


def generate_test_method(template_path, expected_path):
    def test_method(self):
        template_config = Config.load(template_path)
        expected_config = Config.load(expected_path)

        self.assertEqual(
            template_config.data,
            expected_config.data,
            f"\nMismatch between:\n  Template: {template_path}\n  Expected: {expected_path}\n"
            f"  Actual:   {json.dumps(template_config.data, indent=Config.INDENT)}\n"
            f"  Expected: {json.dumps(expected_config.data, indent=Config.INDENT)}"
        )

    test_method.__name__ = f"test_{os.path.basename(template_path)}"
    test_method.__doc__ = f"Test dynamo resolution for {os.path.basename(template_path)}"

    return test_method


class DynamoTest(unittest.TestCase):
    pass


# Discover fixture pairs and dynamically generate test methods
files_dir = os.path.join(os.path.dirname(__file__), 'files')
for template_path, expected_path, test_name in discover_fixture_pairs(files_dir):
    test_method = generate_test_method(template_path, expected_path)
    setattr(DynamoTest, test_name, test_method)
