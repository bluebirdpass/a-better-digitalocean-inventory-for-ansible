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


def api_droplet(id, name, size, region, image, ip, private_ip):
    return {
        "status": "active",
        "kernel": None,
        "locked": False,
        "name": name,
        "backup_ids": [],
        "created_at": "2015-10-01T14:17:36Z",
        "snapshot_ids": [],
        "size_slug": size,
        "id": id,
        "next_backup_window": None,
        "vcpus": 1,
        "features": [
            "private_networking",
            "virtio"
        ],
        "image": {
            "min_disk_size": 20,
            "slug": image,
            "name": "15.04 x64",
            "created_at": "2015-07-07T17:56:28Z",
            "id": 12658446,
            "regions": [
                "nyc3",
            ],
            "distribution": "Ubuntu",
            "type": "snapshot",
            "public": True
        },
        "memory": 0,
        "region": {
            "available": True,
            "slug": region,
            "features": [
                "private_networking",
                "backups",
                "ipv6",
                "metadata"
            ],
            "name": "Test Region",
            "sizes": [
                "32gb",
                "16gb",
                "2gb",
                "1gb",
                "4gb",
                "8gb",
                "512mb",
                "64gb",
                "48gb"
            ]
        },
        "disk": 30,
        "ip_address": ip,
        "networks": {
            "v4": [
                {
                    "ip_address": private_ip,
                    "netmask": "255.255.255.0",
                    "type": "private",
                    "gateway": "10.0.0.2"
                },
                {
                    "ip_address": ip,
                    "netmask": "255.255.255.0",
                    "type": "public",
                    "gateway": "45.0.0.1"
                }
            ],
            "v6": []
        },
        "size": {
            "price_monthly": 0.0,
            "available": True,
            "vcpus": 1,
            "regions": [
                "nyc2",
                "sgp1",
                "ams1",
                "sfo1",
                "lon1",
                "nyc3",
                "ams3",
                "nyc1",
                "ams2",
                "fra1",
                "tor1"
            ],
            "memory": 0,
            "transfer": 2.0,
            "disk": 30,
            "price_hourly": 0.01488,
            "slug": size
        }
    }


@pytest.fixture
def api_droplets():
    return [
        api_droplet(110, "droplet-1", "512mb", "nyc3", "ubuntu-14", "45.0.0.2", "10.0.0.2"),
        api_droplet(111, "droplet-2", "512mb", "nyc3", "ubuntu-14", "45.0.0.3", "10.0.0.3"),
        api_droplet(112, "droplet-3", "1gb", "nyc3", "ubuntu-14", "45.0.0.4", "10.0.0.4")
    ]


@pytest.fixture
def droplets():
    """
    Mapped droplets have had the various attribute from the DO API
    mapped into the final droplet dict.
    """
    return [
        {
            'id': 110,
            'name': 'droplet-1',
            'ip_address': '45.0.0.2',
            'private_ip_address': '10.0.0.2',
            'created_at': '2015-10-01T14:17:36Z',
            'distro': 'Ubuntu',
            'image': 'ubuntu-14',
            'image_id': 12658446,
            'region': 'nyc3',
            'size': '512mb',
            'backups_active': False,
            'locked': False,
            'status': 'active'
        },
        {
            'id': 111,
            'name': 'droplet-2',
            'ip_address': '45.0.0.3',
            'private_ip_address': '10.0.0.3',
            'created_at': '2015-10-01T14:17:36Z',
            'distro': 'Ubuntu',
            'image': 'ubuntu-14',
            'image_id': 12658446,
            'region': 'nyc3',
            'size': '512mb',
            'backups_active': False,
            'locked': False,
            'status': 'active'
        },
        {
            'id': 112,
            'name': 'droplet-3',
            'ip_address': '45.0.0.4',
            'private_ip_address': '10.0.0.4',
            'created_at': '2015-10-01T14:17:36Z',
            'distro': 'Ubuntu',
            'image': 'ubuntu-14',
            'image_id': 12658446,
            'region': 'nyc3',
            'size': '1gb',
            'backups_active': False,
            'locked': False,
            'status': 'active'
        }
    ]


def test_group_rule_by_attribute(droplets):
    inventory = {}

    rule = GroupRule("size")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["512mb"] == ["45.0.0.2", "45.0.0.3"]
    assert inventory["1gb"] == ["45.0.0.4"]


def test_group_name(droplets):
    inventory = {}

    rule = GroupRule("size", group_name="size_{0}")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["size_512mb"] == ["45.0.0.2", "45.0.0.3"]
    assert inventory["size_1gb"] == ["45.0.0.4"]


def test_group_match(droplets):
    inventory = {}

    rule = GroupRule("size", group_match=r"^512")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["512mb"] == ["45.0.0.2", "45.0.0.3"]
    assert "1024mb" not in inventory


def test_group_match_with_group_name(droplets):
    inventory = {}

    rule = GroupRule("size", group_match=r"^(512)(mb)$", group_name="{0}_{1}")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["512_mb"] == ["45.0.0.2", "45.0.0.3"]
    assert len(inventory) is 1


def test_droplets_with_missing_attributes(droplets):
    inventory = {}

    droplets[0]["image"] = None
    droplets[1]["image"] = None

    rule = GroupRule("image")
    [rule.apply(d, inventory) for d in droplets]

    assert inventory["ubuntu-14"] == ["45.0.0.4"]
    assert len(inventory) is 1


def test_do_data_provider_droplets(mocker, droplets, api_droplets):
    do = mock_do_manager(mocker, api_droplets=api_droplets)
    droplets_map = DataProvider("api_token").droplets

    assert list(droplets_map) == droplets
    do.assert_called_with(None, "api_token", api_version='2')


def test_do_data_provider_missing_creds():
    with pytest.raises(DoError) as e:
        DataProvider(None)

    assert str(e.value) == "Please provide an api_token."


def test_list_inventory(mocker, api_droplets):
    mock_do_manager(mocker, api_droplets)

    rules = [
        GroupRule("name"),
        GroupRule("size", "size_{0}")
    ]

    do_inventory = DigitalOceanInventory(rules, "api_token")
    inventory = do_inventory.list_inventory()

    expected_inventory = {
        "_meta": {
            "hostvars": {
                "45.0.0.2": {
                    'do_id': 110,
                    'do_name': 'droplet-1',
                    'do_ip_address': '45.0.0.2',
                    'do_private_ip_address': '10.0.0.2',
                    'do_created_at': '2015-10-01T14:17:36Z',
                    'do_distro': 'Ubuntu',
                    'do_image': 'ubuntu-14',
                    'do_image_id': 12658446,
                    'do_region': 'nyc3',
                    'do_size': '512mb',
                    'do_backups_active': False,
                    'do_locked': False,
                    'do_status': 'active'
                },
                "45.0.0.3": {
                    'do_id': 111,
                    'do_name': 'droplet-2',
                    'do_ip_address': '45.0.0.3',
                    'do_private_ip_address': '10.0.0.3',
                    'do_created_at': '2015-10-01T14:17:36Z',
                    'do_distro': 'Ubuntu',
                    'do_image': 'ubuntu-14',
                    'do_image_id': 12658446,
                    'do_region': 'nyc3',
                    'do_size': '512mb',
                    'do_backups_active': False,
                    'do_locked': False,
                    'do_status': 'active'
                },
                "45.0.0.4": {
                    'do_id': 112,
                    'do_name': 'droplet-3',
                    'do_ip_address': '45.0.0.4',
                    'do_private_ip_address': '10.0.0.4',
                    'do_created_at': '2015-10-01T14:17:36Z',
                    'do_distro': 'Ubuntu',
                    'do_image': 'ubuntu-14',
                    'do_image_id': 12658446,
                    'do_region': 'nyc3',
                    'do_size': '1gb',
                    'do_backups_active': False,
                    'do_locked': False,
                    'do_status': 'active'
                }
            }
        },
        "droplet-1": ["45.0.0.2"],
        "droplet-2": ["45.0.0.3"],
        "droplet-3": ["45.0.0.4"],
        "size_512mb": ["45.0.0.2", "45.0.0.3"],
        "size_1gb": ["45.0.0.4"]
    }

    assert inventory == expected_inventory


def test_from_config():
    from digital_ocean import default_group_rules
    do_inventory = DigitalOceanInventory.from_config(here + "/test.ini")

    assert do_inventory.group_rules == default_group_rules
    assert do_inventory.api_token == "123"


def test_from_config_do_cred_from_env():
    os.environ["DO_API_TOKEN"] = "555"

    do_inventory = DigitalOceanInventory.from_config(here + "/test-no-token.ini")
    assert do_inventory.api_token == "555"


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


def mock_do_manager(mocker, api_droplets=None):

    do = mocker.patch("digital_ocean.DoManager")

    if droplets:
        do().all_active_droplets.return_value = api_droplets

    return do