A better DigitalOcean inventory for Ansible
===========================================

Ansible already bundles a dynamic inventory for DigitalOcean but there are some
things about it that could be improved.

**Overall design and testability of the code** leaves a bit to be desired. In an
effort to make the code more "pythonic" and fully tested I've rewritten pretty
much everything. I've tried to keep feature parity in the core functionality
of the inventory like --list, --host and configuration. Some things are missing like
caching and some other command line flags.

**The ability to create more meaningful host groups** was something I desperately needed.
DigitalOcean does not let you add any sort of metadata or tags to your droplets. This was my
primary reason for writing a new DO inventory.  All grouping is controlled by a pluggable `GroupRule`
system. This way you can put droplets into groups based on some defined naming conventions. All the
groups in the currently bundled DO inventory are supported with the ability configure more. More on this later.


Usage
=====
Use this inventory like any other [Ansible dynamic inventory](http://docs.ansible.com/intro_dynamic_inventory.html). Simply clone this repo and move `digital_ocean.py` and `digital_ocean.ini` into your "playbook" inventory. Make sure `digital_ocean.py` executable. 

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

Calling `--host HOST` will return the above list of variables for `HOST`. The `--list` call also returns a `_meta` dict with `hostvars` for all returned hosts. Doing this prevents ansible from calling `--host` on all hosts returned from `--list`. See the "developing inventory" [docs](http://docs.ansible.com/developing_inventory.html#tuning-the-external-inventory-script) for more info.





