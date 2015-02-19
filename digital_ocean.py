"""
    digital_ocean
    ~~~~~~~~~~~~~~
    This module provides an Ansible dynamic inventory for DigitalOcean.

    :copyright: (c) 2015 by Shawn Adams.
    :license: BSD, see LICENSE for more details.
"""
import sys
from argparse import ArgumentParser
import re

try:
    from dopy.manager import DoError, DoManager
except ImportError, e:
    sys.exit("failed=True msg='`dopy` library required for this script'")


class Inventory(object):
    pass


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
    def __init__(self, attr, group_name=None, group_match=None):
        self.attr = attr
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
        :param inventory: A dict like object representing Anisble inventory
        """

        value = droplet.get(self.attr)
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


class DigitalOcean(object):
    def __init__(self, api_key=None, client_id=None, group_rules=None):
        self.api_key = api_key
        self.client_id = client_id
        self.groups = group_rules

    def main(self, args):
        """
        The main point of entry for handing command line arguments and running
        this dynamic inventory.
        """
        parser = ArgumentParser(
            __name__,
            description="Generate DigitalOcean inventory for ansible"
        )

        parser.add_argument("--list", action="store_true",
                            help="Get inventory list of active droplets")
        parser.add_argument("--host", action="store",
                            help="Get inventory vars for the specified host")

        parser.parse_args(args)


if __name__ == "__main__":
    print DigitalOcean().main(sys.argv[1:])