A better DigitalOcean inventory for Ansible
===========================================

Ansible already bundles a dynamic inventory for DigitalOcean but there are some
things about it that could be improved.

_Overall design and testability of the code_ leaves a bit to be desired. In an
effort to make the code more "pythonic" and fully tested I've rewritten pretty
much everything. I've tried to keep feature parity in the core functionality
of the inventory, --list, --host and configuration. Some things are missing like
caching and some other command line flags.


