#!/usr/bin/env python

"""
    digital_ocean
    ~~~~~~~~~~~~~~
    This module provides an Ansible dynamic inventory for DigitalOcean.

    :copyright: (c) 2015 by Shawn Adams.
    :license: MIT, see LICENSE for more details.
"""

import json
import os
import re
import sys
import traceback

from ConfigParser import SafeConfigParser
from argparse import ArgumentParser

try:
    from dopy.manager import DoError, DoManager
except ImportError, e:
    sys.exit("failed=True msg='`dopy` library required for this script'")


class GroupRule(object):
    """
    A GroupRule represents a way to group the droplets returned by DigitalOcean.
    In its simplest form we can put droplets into a group based on an attribute
    of the droplet. For instance memory "size" ::

        >>> droplets = [
        ...     {"size": "512mb", "ip_address": "10.0.0.1"},
        ...     {"size": "512mb", "ip_address": "10.0.0.2"},
        ...     {"size": "1024mb", "ip_address": "10.0.0.3"}
        ... ]
        >>>
        >>> inventory = {}
        >>>
        >>> rule = GroupRule("size")
        >>> [rule.apply(d, inventory) for d in droplets]
        >>>
        >>> print inventory
        {'512mb': ['10.0.0.1', '10.0.0.2'], '1024mb': ['10.0.0.3']}

    Passing ``group_name`` gives us greater control of groups are named.
    ``group_name`` is treated as a format string. Given the above droplets we
    could have defined our `GroupRule` like this ::

        >>> rule = GroupRule("size", "size_{0}")

    Running this rule on our droplets would leave us with this `inventory` ::

        >>> {'size_512mb': ['10.0.0.1', '10.0.0.2'], 'size_1024mb': ['10.0.0.3']}

    ``group_match`` lets us group only attributes that match a specific regex.
    Take this simple example of only grouping droplets of size 512mb ::

        >>> rule = GroupRule("size", group_match=r"^512mb$")

    Resulting inventory ::

        >>>  {'512mb': ['10.0.0.1', '10.0.0.2']}

    ``group_match`` also modifies the way we define ``group_name``. Matched
    regex groups can be referenced by their index in ``group_name``.
    For example ::

        >>> rule = GroupRule("size", group_match=r"^(512)(mb)$",
        ...                  group_name="size_in_{1}_is_{0}")

    And the resulting ``inventory`` ::

        >>> {"size_in_mb_is_512": ["10.0.0.1", "10.0.0.2"]}

    """
    def __init__(self, group_by, group_name=None, group_match=None):
        self.group_by = group_by
        self.group_name = group_name

        if group_match is not None:
            self.group_match = re.compile(group_match)
        else:
            self.group_match = None

    def apply(self, droplet, inventory):
        """
        Apply the rule to a `droplet` possibly adding the droplet to a group on
        the passed in `inventory`

        :param droplet: A droplet dict
        :param inventory: A dict like object representing Ansible inventory
                          that groups will be added to
        """

        value = droplet.get(self.group_by)
        ip = droplet["ip_address"]

        if value is None:
            return None

        if self.group_match:
            m = self.group_match.match(value)
            if m is None:
                return
            if self.group_name:
                group_name = self.group_name.format(*m.groups())
            else:
                group_name = value
        else:
            group_name = (self.group_name or "{0}").format(value)

        inventory.setdefault(group_name, []).append(ip)


class DataProvider(object):
    def __init__(self, api_token):
        if api_token is None:
            raise DoError("Please provide an api_token.")
        self.do = DoManager(None, api_token, api_version='2')

    def __getattr__(self, cache_key):
        if cache_key not in self.cache:
            raise AttributeError(cache_key)
        return self.cache[cache_key]

    @property
    def droplets(self):
        for droplet in self.do.all_active_droplets():

            def private_ip():
                for interface in droplet["networks"]["v4"]:
                    if interface["type"] == "private":
                        return interface["ip_address"]

            yield {
                "id": droplet["id"],
                "name": droplet["name"],
                "ip_address": droplet["ip_address"],
                "private_ip_address": private_ip(),
                "image": droplet["image"]["slug"],
                "image_id": droplet["image"]["id"],
                "distro": droplet["image"]["distribution"],
                "locked": droplet["locked"],
                "region": droplet["region"]["slug"],
                "size": droplet["size"]["slug"],
                "created_at": droplet["created_at"],
                "status": droplet["status"],
                "backups_active": droplet["next_backup_window"] is not None,
            }


default_group_rules = [
    GroupRule("id"),
    GroupRule("name"),
    GroupRule("image", "image_{0}"),
    GroupRule("image_id", "image_{0}"),
    GroupRule("distro", "distro_{0}"),
    GroupRule("region", "region_{0}"),
    GroupRule("size", "size_{0}"),
    GroupRule("status", "status_{0}")
]


class DigitalOceanInventory(object):

    @property
    def do(self):
        if self.__do is None:
            self.__do = DataProvider(self.api_token)
        return self.__do

    def __init__(self, group_rules, api_token=None):
        self.api_token = api_token
        self.group_rules = group_rules
        self.__do = None

    @classmethod
    def from_config(cls, config_file):
        """
        Create an instance of `DigitalOcean` from a configuration file.

        :param config_file: Path to a .ini style file which will be used to
                            configure the instance of `DigitalOcean`
        """

        config = SafeConfigParser()
        config.read(config_file)

        group_rules = []
        for section in config.sections():
            if not section.startswith("group:"):
                continue
            group_rules.append(GroupRule(**dict(config.items(section))))

        def get_config(key, env=None):
            if config.has_option("digital_ocean", key):
                return config.get("digital_ocean", key)
            if env is not None and env in os.environ:
                return os.environ[env]
            return None

        return cls(
            default_group_rules + group_rules,
            api_token=get_config("api_token", "DO_API_TOKEN")
        )

    def main(self, args):
        """
        The main point of entry for handing command line arguments and running
        this dynamic inventory.

        :param args: List of arguments gotten from `sys.argv[1:]`
        """
        parser = ArgumentParser(
            __name__,
            description="Generate DigitalOcean inventory for ansible"
        )

        parser.add_argument("--list", action="store_true",
                            help="Get inventory list of active droplets")
        parser.add_argument("--host", action="store",
                            help="Get inventory vars for the specified host")
        parser.add_argument("--pretty", action="store_true",
                            help="Pretty print output")

        parser.add_argument("--env", "-e", action="store_true",
                            help="Print out DO_CLIENT_ID and DO_API_KEY "
                                 "environmental variables")

        parser.add_argument("--api-token", "-a", action="store",
                            help="DigitalOcean v2 api token")

        args = parser.parse_args(args)
        self.api_token = args.api_token or self.api_token

        if args.env:
            return "DO_API_VERSION=2 DO_API_TOKEN={1}".format(self.api_token)
        if args.host:
            out = self.get_host(args.host)
        else:
            out = self.list_inventory()

        if args.pretty:
            return json.dumps(out, sort_keys=True, indent=2)
        return json.dumps(out)

    def list_inventory(self):
        """
        Get the inventory list. The exact groups returned is dependent on the
        group rules passed when initializing `DigitalOceanInventory`. Most
        likely `default_group_rules` plus any group rules defined in the
        config.
        """
        inventory = {}
        host_vars = {}

        for droplet in self.do.droplets:
            for rule in self.group_rules:
                rule.apply(droplet, inventory)

            host_vars[droplet["ip_address"]] = {
                "do_{}".format(k): v for k, v in droplet.iteritems()
            }

        inventory["_meta"] = {
            "hostvars": host_vars
        }

        return inventory

    def get_host(self, host):
        """
        Get vars for a given host
        """
        for droplet in self.do.droplets:
            if droplet["ip_address"] == host:
                return {"do_{}".format(k): v for k, v in droplet.iteritems()}
        return {}


if __name__ == "__main__":

    config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "digital_ocean.ini"
    )

    do_inventory = DigitalOceanInventory.from_config(config_file)

    try:
        print do_inventory.main(sys.argv[1:])
        sys.exit(0)
    except Exception as e:
        print traceback.format_exc()
        sys.exit(1)
