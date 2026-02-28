# webkitconfigpy

Provides utilities for parsing and managing dynamic JSON and YAML configurations.

## Requirements

- webkitcorepy
- pyyaml

## Command Line

The `explode-config` command parses JSON or YAML configuration files and outputs them to stdout:

```bash
explode-config config.json
explode-config config.yaml

# Convert between formats
explode-config config.yaml --format json
explode-config config.json --format yaml

# Control JSON indentation
explode-config config.json --indent 4
```

This tool will eventually resolve all dynamic elements in configuration files, making them fully expanded and explicit.

## Usage

The `webkitconfigpy` library provides a unified API for loading and parsing configuration files in both JSON and YAML formats. The library supports dynamic configuration loading with validation and type checking.

### Basic Usage

```python
from webkitconfigpy import Config

# Load from a file (automatically detects JSON or YAML based on extension)
config = Config.from_file('/path/to/config.json')

# Access configuration values
value = config.get('key')
nested_value = config.get('section.nested.key')

# Load from a string
json_config = Config.from_json('{"key": "value"}')
yaml_config = Config.from_yaml('key: value')
```

### Dynamic Configuration

The library supports dynamic configuration loading with automatic type detection:

```python
from webkitconfigpy import Config

# Load configuration with schema validation
config = Config.from_file('/path/to/config.yaml', validate=True)

# Get with default values
value = config.get('optional_key', default='default_value')

# Check if key exists
if config.has('some.nested.key'):
    value = config.get('some.nested.key')
```

### Working with Multiple Configurations

You can merge multiple configuration sources:

```python
from webkitconfigpy import Config

base_config = Config.from_file('/path/to/base.json')
env_config = Config.from_file('/path/to/environment.yaml')

# Merge configurations (env_config takes precedence)
merged = base_config.merge(env_config)
```

### JSON Configuration

```python
from webkitconfigpy import JSONConfig

config = JSONConfig('/path/to/config.json')
data = config.load()
```

### YAML Configuration

```python
from webkitconfigpy import YAMLConfig

config = YAMLConfig('/path/to/config.yaml')
data = config.load()
```
