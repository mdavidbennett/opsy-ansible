# Opsy Ansible
It's Opsy! A simple multi-user/role operations inventory system with aspirations. Now in ansible form!

## Checkout and build
This is an ansible collection and ansible is very particular on how its directory structure is setup. Before you clone this repo you need to setup some parent directories like so:

    $ mkdir -p ansible_collections/opsy/
    $ cd ansible_collections/opsy/
    $ git clone https://github.com/testeddoughnut/opsy-ansible.git opsy_ansible
    $ cd opsy_ansible

You can then build the checked out code by running the following:

    $ ansible-galaxy collection build

This will output a tarball in the current directory named `opsy-opsy_ansible-<version_number>.tar.gz`.

## Installation
Now that you've built your tarball you can install it in your ansible environment. By default ansible will install collections to `~/.ansible/collections`, you can adjust this behavior by adding something like the following to your `ansible.cfg`:

    [defaults]
    collections_paths = ./collections

You can install the collection like so:

    $ ansible-galaxy collection install <path_to_tarball>/opsy-opsy_ansible-<version_number>.tar.gz

## Using the inventory plugin
Add something like this to your `ansible.cfg`:

    [inventory]
    enable_plugins = host_list, script, auto, yaml, ini, opsy.opsy_ansible.opsy
    cache = True
    cache_plugin = jsonfile
    cache_connection = ./cache

The enable_plugins line enables the inventory plugin for use. The lines that start with cache enables caching of the results from Opsy, you can omit these lines if you don't intend to use caching.

In your inventory directory, you will need to add a file called `opsy.yml` with something like the following as its contents:

    plugin: opsy
    url: "http://127.0.0.1:5000/"
    zone: west
    user: ansible
    password: password
    cache: True

Documentation about the specific options are available using `ansible-doc`:

    $ ansible-doc -t inventory opsy.opsy_ansible.opsy

You can test that it loaded successfully like so:

    $ ansible-inventory -i inventory/opsy/opsy.yml --graph --vars
    @all:
      |--@default:
      |  |--westconsul
      |  |  |--{datacenter = west}
      |  |  |--{default = True}
      |  |  |--{opsy_host_id = 1c79a03c-d07d-4922-9747-486f61cdef54}
      |  |  |--{prom_node = westprom}
      |  |--westprom
      |  |  |--{consul_node = westconsul}
      |  |  |--{datacenter = west}
      |  |  |--{default = True}
      |  |  |--{opsy_host_id = 046c7aef-d968-4135-833f-c9d2ff32cd5e}
      |  |  |--{prom_node = westprom}
      |  |  |--{prom_region = west}
      |  |  |--{thanos = True}
      |--@prom_nodes:
      |  |--westprom
      |  |  |--{consul_node = westconsul}
      |  |  |--{datacenter = west}
      |  |  |--{default = True}
      |  |  |--{opsy_host_id = 046c7aef-d968-4135-833f-c9d2ff32cd5e}
      |  |  |--{prom_node = westprom}
      |  |  |--{prom_region = west}
      |  |  |--{thanos = True}
      |--@ungrouped:

## Running tests
Ansible has its own test runners that we make use of. CircleCI will automatically run tests against all supported versions of python on a PR, but you can kick off tests locally as well. Before running tests, be sure to install all the test requirements like so:

    $ pip install -r test-requirements.txt

Then you can kick off the tests like so (replace the python version with whatever version you're using):

    $ ansible-test sanity --python 3.6
    $ ansible-test units --python 3.6

The sanity tests are more or less style and other ansible specific checks. The unit tests are tests for the Opsy ansible plugins.
