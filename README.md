A better DigitalOcean inventory for Ansible
===========================================

Ansible already bundles a dynamic inventory for DigitalOcean but there are some
things about it that could be improved.

**Overall design and testability of the code** leaves a bit to be desired. In an
effort to make the code more "pythonic" and fully tested I've rewritten pretty
much everything. I've tried to keep feature parity in the core functionality
of the inventory like --list, --host and configuration. Some things are missing like
caching and some other command line flags.

**The ability to create more meaningful host groups** was something I
desperately needed. DigitalOcean does not let you add any sort of metadata or
tags to your droplets. This was my primary reason for writing a new DO
inventory.  All grouping is controlled by a pluggable `GroupRule` system. This
way you can put droplets into groups based on some defined naming conventions.
All the groups in the currently bundled DO inventory are supported with the
ability configure more. More on this later.


Usage
=====
Use this inventory like any other
[Ansible dynamic inventory](http://docs.ansible.com/intro_dynamic_inventory.html).
Simply clone this repo and move `digital_ocean.py` and `digital_ocean.ini` into
your "playbook" inventory. Make sure `digital_ocean.py` executable.

### Using directly
List all inventory groups
```shell
$ digital_ocean.py --list
```

Get vars for a particular host
```shell
$ digital_ocean.py --host 10.0.0.1
```

### Inventory groups 
The following groups are defined for you when `--list` is called

* {id} - hosts grouped by droplet id (eg: `122231`)
* {name} - hosts grouped by droplet name (eg: `my-droplet`)
* image_{id} - hosts grouped by image id (eg: `image_674747`)
* image_{slug} - hosts grouped by image slug (eg: `image_ubuntu-12-x64`)
* distro_{distribution} - Hosts grouped by distro name (eg: `distro_Ubuntu`)
* size_{id} - hosts grouped by size id (eg: `size_66`)
* size_{slug} - hosts grouped by size slug (eg: `size_512mb`)
* region_{id} - hosts grouped by region id (eg: `region_4`)
* region_{slug} - hosts grouped by region slug (eg: `region_nyc4`)
* status_{status} - hosts grouped by status (eg: `status_active`)


### Host vars
The following vars are defined for droplets

* `do_id` - Droplet id (eg: `3089638`)
* `do_backups_active` - Are backups active? (eg: `false`)
* `do_created_at` - Droplet creation timestamp (eg: `2014-11-06T15:49:41Z`)
* `do_distro` - Friendly linux distro name (eg: `Ubuntu`)
* `do_image` - Image name (eg: `ubuntu-14-04-x64`)
* `do_image_id` - Image id (eg: `7111343`)
* `do_ip_address` - Droplet's public ip address
* `do_locked` - Is the droplet locked? (eg: `false`)
* `do_name` - Droplet's name
* `do_private_ip_address` - Droplet's private ip address
* `do_region` - Region (eg: `nyc3`)
* `do_region_id` - Region id (eg: `4`)
* `do_size` Droplet size (eg: `512mb`)
* `do_size_id` - Droplet size id (eg: `66`)
* `do_status` - Droplet status (eg: `active`)

Calling `--host HOST` will return the above list of variables for `HOST`. The
`--list` call also returns a `_meta` dict with `hostvars` for all returned
hosts. Doing this prevents ansible from calling `--host` on all hosts returned
from `--list`. See the "developing inventory"
[docs](http://docs.ansible.com/developing_inventory.html#tuning-the-external-inventory-script)
for more info.


### Custom groups

Groups can be defined in `digital_ocean.ini`. Take the following example

```ini
[group:prod]
group_by = name
group_match = ^prod\.
group_name = prod
```

This will group all droplets whose name matches the regex `^prod\.` into a
group called `prod`. If we have the following droplets

```
name: prod.server-1.com
ip_address: 10.0.0.1
...

name: prod.server-2.com
ip_address: 10.0.0.2
...
```

The output of `--list` will contain the following group
```
"prod": ["10.0.0.1", "10.0.0.2"]
```

A group is defined by a section `[group:GROUP_NAME`] where `GROUP_NAME` is a
unique name for your group. The meaning of the properties are as follows:

* `group_by` (required) The droplet attribute to group on. This can be any host
             var listed above minus the `do_` prefix
* `group_match` (optional) A regex to match the attribute value on. Only
                matches will be grouped.
* `group_name` (optional) The name of the group. If omitted the droplet's
                attribute value will be used.

#### Control naming with group_name
`group_name` is actually treated as a python format string. When you use
`group_match` you can define regex groups and reference them in `group_name` by
their index (eg `{0}`, `{1}`, etc). If `group_match` is omitted the attribute
value can be referenced as `{0}`. The more interesting case being the former as
it allows us to define groups for a complex multi stage environment.

Here is an example of how you might want to group servers in a 2 stage
environment. Our server naming convention will be:

```
prod.{app-name}.{server-type}.com
staging.{app-name}.{server-type}.com
```

Given these droplets

```
# Staging
name: staging.api.appserver-1.com
ip: 10.0.0.1

name staging.api.appserver-2.com
ip: 10.0.0.2

name staging.api.loadbalancer-1.com
ip: 10.0.0.3

# Production
name: prod.api.appserver-1.com
ip: 10.0.0.4

name prod.api.appserver-2.com
ip: 10.0.0.5

name prod.api.loadbalancer-1.com
ip: 10.0.0.6
```

We can define the following groups

```ini
[group:staging]
group_by = name
group_match = ^staging\.[\w]+\.[\w]+-[0-9]+\.com$
group_name = staging

[group:staging-servers]
group_by = name
group_match = ^staging\.([\w]+)\.([\w]+)-[0-9]+\.com$
group_name = staging-{0}-{1}

[group:prod]
group_by = name
group_match = ^prod\.[\w]+\.[\w]+-[0-9]+\.com$
group_name = prod

[group:prod-servers]
group_by = name
group_match = ^prod\.([\w]+)\.([\w]+)-[0-9]+\.com$
group_name = prod-{0}-{1}
```

Running `--list` would include the following groups
```
"staging": ["10.0.0.1", "10.0.0.2", "10.0.0.3"],
"staging-api-appserver": ["10.0.0.1", "10.0.0.2"],
"staging-loadbalancer": ["10.0.0.3"],
"prod": ["10.0.0.4", "10.0.0.5", "10.0.0.6"],
"prod-api-appserver": ["10.0.0.4", "10.0.0.5"],
"prod-loadbalancer": ["10.0.0.6"]
```

Caching?
========

With the addition of the `_meta` object to the output of the `--list` call
ansible makes far fewer calls to the inventory. I have found the cache was 
only saving a couple of seconds. That being said, I do plan to implement 
the cache but my current needs dont demand it.


Running unit tests
===================
After cloning the repo you'll need to install dependencies run these commands
from the repo dir.

```shell
$ pip install -r requirements.txt -r test_requirements.txt
```

The simply run
```
py.test
```







