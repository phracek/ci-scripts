#!/usr/bin/env python3


from stream_generator import YamlLoader
from data.data_yaml_loader import load_yaml_result


def test_load_yaml():
    loader = YamlLoader("tests/data/minimal.yml")
    assert loader.data == load_yaml_result
