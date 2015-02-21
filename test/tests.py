"""
    digital_ocean tests
    ~~~~~~~~~~~~~~~~~~~~
    Tests for digital_ocean.py

    :copyright: (c) 2015 by Shawn Adams.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import re

here = os.path.dirname(os.path.abspath(__file__))
sys.path.append(here + "/..")

import pytest
from dopy.manager import DoError
from digital_ocean import GroupRule, DataProvider, DigitalOceanInventory


@pytest.fixture
def droplets():
    return [
        {
            "backups_active": False,
            "created_at": "2015-02-18T20:00:00Z",
            "id": 1,
            "image_id": 10,
            "ip_address": "10.0.0.1",
            "locked": False,
            "name": "droplet-1",
            "private_ip_address": None,
            "region_id": 20,
            "size_id": 30,
            "status": "active"
        },
        {
            "backups_active": False,
            "created_at": "2015-02-18T21:30:00Z",
            "id": 2,
            "image_id": 11,
            "ip_address": "10.0.0.2",
            "locked": False,
            "name": "droplet-2",
            "private_ip_address": None,
            "region_id": 21,
            "size_id": 31,
            "status": "active"
        }
    ]


@pytest.fixture
def images():
    return [
        {"id": 10, "distribution": "ubuntu", "slug": "ubuntu-12"},
        {"id": 11, "distribution": "centos", "slug": "centos-12"}
    ]


@pytest.fixture
def regions():
    return [
        {"slug": "nyc3", "id": 20},
        {"slug": "sfo1", "id": 21}
    ]


@pytest.fixture
def sizes():
    return [
        {"slug": "512mb", "id": 30},
        {"slug": "1gb", "id": 31}
    ]


@pytest.fixture
def expanded_droplets():
    """
    Expanded droplets have had the various attribute "slugs" added to the
    droplet dict. (size, image, region, etc)
    """
    return [
        {"size": "512mb", "ip_address": "10.0.0.1"},
        {"size": "512mb", "ip_address": "10.0.0.2"},
        {"size": "1024mb", "ip_address": "10.0.0.3", "image": "ubuntu"}
    ]


def test_group_rule_by_attribute(expanded_droplets):
    inventory = {}

    rule = GroupRule("size")
    [rule.apply(d, inventory) for d in expanded_droplets]

    assert inventory["512mb"] == ["10.0.0.1", "10.0.0.2"]
    assert inventory["1024mb"] == ["10.0.0.3"]


def test_group_name(expanded_droplets):
    inventory = {}

    rule = GroupRule("size", group_name="size_{0}")
    [rule.apply(d, inventory) for d in expanded_droplets]

    assert inventory["size_512mb"] == ["10.0.0.1", "10.0.0.2"]
    assert inventory["size_1024mb"] == ["10.0.0.3"]


def test_group_match(expanded_droplets):
    inventory = {}

    rule = GroupRule("size", group_match=r"^512")
    [rule.apply(d, inventory) for d in expanded_droplets]

    assert inventory["512mb"] == ["10.0.0.1", "10.0.0.2"]
    assert "1024mb" not in inventory


def test_group_match_with_group_name(expanded_droplets):
    inventory = {}

    rule = GroupRule("size", group_match=r"^(512)(mb)$", group_name="{0}_{1}")
    [rule.apply(d, inventory) for d in expanded_droplets]

    assert inventory["512_mb"] == ["10.0.0.1", "10.0.0.2"]
    assert len(inventory) is 1


def test_droplets_with_missing_attributes(expanded_droplets):
    inventory = {}

    rule = GroupRule("image")
    [rule.apply(d, inventory) for d in expanded_droplets]

    assert inventory["ubuntu"] == ["10.0.0.3"]
    assert len(inventory) is 1


def test_do_data_provider_images(mocker, images):
    do = mock_do_manager(mocker, images=images)

    image_map = DataProvider("client_id", "api_key").images

    assert image_map == {10: "ubuntu-12", 11: "centos-12"}
    do.assert_called_with("client_id", "api_key")
    do().all_images.assert_called_with("global")


def test_do_data_provider_distros(mocker, images):
    do = mock_do_manager(mocker, images=images)

    distro_map = DataProvider("client_id", "api_key").distros

    assert distro_map == {10: "ubuntu", 11: "centos"}
    do.assert_called_with("client_id", "api_key")
    do().all_images.assert_called_with("global")


def test_do_data_provider_regions(mocker, regions):
    do = mock_do_manager(mocker, regions=regions)

    regions_map = DataProvider("client_id", "api_key").regions

    assert regions_map == {20: "nyc3", 21: "sfo1"}
    do.assert_called_with("client_id", "api_key")


def test_do_data_provider_sizes(mocker, sizes):
    do = mock_do_manager(mocker, sizes=sizes)
    sizes_map = DataProvider("client_id", "api_key").sizes

    assert sizes_map == {30: "512mb", 31: "1gb"}
    do.assert_called_with("client_id", "api_key")


def test_do_data_provider_droplets(mocker, droplets):
    do = mock_do_manager(mocker, droplets=droplets)

    droplets_map = DataProvider("client_id", "api_key").droplets

    assert droplets_map == droplets
    do.assert_called_with("client_id", "api_key")


def test_do_data_provider_missing_creds():
    with pytest.raises(DoError) as e:
        DataProvider(None, "api_key")

    assert str(e.value) == "Please provide a client_id and api_key."

    with pytest.raises(DoError) as e:
        DataProvider("client_id", None)

    assert str(e.value) == "Please provide a client_id and api_key."

    with pytest.raises(DoError) as e:
        DataProvider(None, None)

    assert str(e.value) == "Please provide a client_id and api_key."


def test_list_inventory(mocker, droplets, images, regions, sizes):
    mock_do_manager(mocker, droplets, images, regions, sizes)

    rules = [
        GroupRule("name"),
        GroupRule("size", "size_{0}")
    ]

    do_inventory = DigitalOceanInventory(rules, "client_id", "api_key")
    inventory = do_inventory.list_inventory()

    expected_inventory = {
        "_meta": {
            "hostvars": {
                "10.0.0.1": {
                    "do_backups_active": False,
                    "do_created_at": "2015-02-18T20:00:00Z",
                    "do_id": 1,
                    "do_image_id": 10,
                    "do_image": "ubuntu-12",
                    "do_distro": "ubuntu",
                    "do_ip_address": "10.0.0.1",
                    "do_locked": False,
                    "do_name": "droplet-1",
                    "do_private_ip_address": None,
                    "do_region_id": 20,
                    "do_region": "nyc3",
                    "do_size_id": 30,
                    "do_size": "512mb",
                    "do_status": "active"
                },
                "10.0.0.2": {
                    "do_backups_active": False,
                    "do_created_at": "2015-02-18T21:30:00Z",
                    "do_id": 2,
                    "do_image_id": 11,
                    "do_image": "centos-12",
                    "do_distro": "centos",
                    "do_ip_address": "10.0.0.2",
                    "do_locked": False,
                    "do_name": "droplet-2",
                    "do_private_ip_address": None,
                    "do_region_id": 21,
                    "do_region": "sfo1",
                    "do_size_id": 31,
                    "do_size": "1gb",
                    "do_status": "active"
                }
            }
        },
        "droplet-1": ["10.0.0.1"],
        "droplet-2": ["10.0.0.2"],
        "size_512mb": ["10.0.0.1"],
        "size_1gb": ["10.0.0.2"]
    }

    assert inventory == expected_inventory


def test_from_config():
    from digital_ocean import default_group_rules
    do_inventory = DigitalOceanInventory.from_config(here + "/test.ini")

    assert do_inventory.group_rules == default_group_rules
    assert do_inventory.api_key == "123"
    assert do_inventory.client_id == "abc"


def test_from_config_do_cred_from_env():
    os.environ["DO_API_KEY"] = "555"
    os.environ["DO_CLIENT_ID"] = "BBB"

    do_inventory = DigitalOceanInventory.from_config(here + "/test.ini")
    assert do_inventory.api_key == "555"
    assert do_inventory.client_id == "BBB"


def test_from_config_custom_group_rules():
    from digital_ocean import default_group_rules
    do_inventory = DigitalOceanInventory.from_config(here + "/test-rules.ini")

    assert do_inventory.group_rules[:-2] == default_group_rules
    assert do_inventory.group_rules[-2].group_by == "size"
    assert do_inventory.group_rules[-2].group_match == re.compile(r"^512mb$")
    assert do_inventory.group_rules[-2].group_name == "small"
    assert do_inventory.group_rules[-1].group_by == "name"
    assert do_inventory.group_rules[-1].group_match == re.compile(r"^[\t]+")
    assert do_inventory.group_rules[-1].group_name == "production"


def mock_do_manager(mocker, droplets=None, images=None,
                    regions=None, sizes=None):

    do = mocker.patch("digital_ocean.DoManager")

    if droplets:
        do().all_active_droplets.return_value = droplets
    if images:
        do().all_images.return_value = images
    if regions:
        do().all_regions.return_value = regions
    if sizes:
        do().sizes.return_value = sizes

    return do