"""
    digital_ocean tests
    ~~~~~~~~~~~~~~~~~~~~
    Tests for digital_ocean.py

    :copyright: (c) 2015 by Shawn Adams.
    :license: BSD, see LICENSE for more details.
"""
from digital_ocean import GroupRule

droplets = [
    {"size": "512mb", "ip_address": "10.0.0.1"},
    {"size": "512mb", "ip_address": "10.0.0.2"},
    {"size": "1024mb", "ip_address": "10.0.0.3"}
]


def test_group_rule_by_attribute():
    inventory = {}

    rule = GroupRule("size")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["512mb"] == ["10.0.0.1", "10.0.0.2"]
    assert inventory["1024mb"] == ["10.0.0.3"]


def test_group_name():
    inventory = {}

    rule = GroupRule("size", group_name="size_{0}")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["size_512mb"] == ["10.0.0.1", "10.0.0.2"]
    assert inventory["size_1024mb"] == ["10.0.0.3"]


def test_group_match():
    inventory = {}

    rule = GroupRule("size", group_match=r"^512")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["512mb"] == ["10.0.0.1", "10.0.0.2"]
    assert "1024mb" not in inventory


def test_group_match_with_group_name():
    inventory = {}

    rule = GroupRule("size", group_match=r"^(512)(mb)$", group_name="{0}_{1}")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["512_mb"] == ["10.0.0.1", "10.0.0.2"]
    assert len(inventory) is 1