from __future__ import (absolute_import, division, print_function)

import json
import httpretty
import pytest

from ansible.inventory.data import InventoryData
from ansible.template import Templar
from ansible.module_utils.common.json import AnsibleJSONEncoder
from ansible_collections.opsy.opsy_ansible.plugins.inventory import opsy


__metaclass__ = type


@pytest.fixture(scope="function")
def inventory():
    config_data = {
        'plugin': 'opsy',
        'url': 'http://localhost:80/',
        'user': 'admin',
        'password': 'password',
        'zone': 'west'
    }
    inventory = opsy.InventoryModule()
    inventory._config_data = config_data
    inventory.inventory = InventoryData()
    inventory.templar = Templar(loader=None)
    return inventory


@pytest.fixture(scope="function")
def fake_opsy_server():

    def login_post_callback(request, uri, response_headers):
        """Make sure the request includes all the creds"""
        request_body = json.loads(request.body.decode('utf-8'))
        assert request_body['user_name'] == 'admin'
        assert request_body['password'] == 'password'
        response_headers = {'Content-Type': 'application/json'}
        response_body = open('tests/data/login_success.json', 'r').read()
        return [200, response_headers, response_body]

    def list_hosts_callback(request, uri, response_headers):
        """Make sure the request includes the auth token"""
        auth_token = json.loads(
            open('tests/data/login_success.json', 'r').read())['token']
        assert request.headers.get('X-AUTH-TOKEN') == auth_token
        response_headers = {'Content-Type': 'application/json'}
        response_body = open('tests/data/list_hosts.json', 'r').read()
        return [200, response_headers, response_body]

    def list_groups_callback(request, uri, response_headers):
        """Make sure the request includes the auth token"""
        auth_token = json.loads(
            open('tests/data/login_success.json', 'r').read())['token']
        assert request.headers.get('X-AUTH-TOKEN') == auth_token
        response_headers = {'Content-Type': 'application/json'}
        response_body = open('tests/data/list_groups.json', 'r').read()
        return [200, response_headers, response_body]

    httpretty.register_uri(
        httpretty.GET, 'http://localhost/docs/swagger.json',
        body=open('tests/data/swagger.json', 'r').read(),
        content_type='application/json')
    httpretty.register_uri(
        httpretty.POST, 'http://localhost/api/v1/login/',
        body=login_post_callback)
    httpretty.register_uri(
        httpretty.GET, 'http://localhost/api/v1/hosts/',
        body=list_hosts_callback)
    httpretty.register_uri(
        httpretty.GET, 'http://localhost/api/v1/groups/',
        body=list_groups_callback)
    httpretty.enable()
    yield
    httpretty.disable()


def test_get_data(inventory, fake_opsy_server):
    """Make sure get data gets the right data."""
    hosts = json.loads(open('tests/data/list_hosts.json', 'r').read())
    groups = json.loads(open('tests/data/list_groups.json', 'r').read())
    data = inventory._get_data(
        'http://localhost:80/', 'admin', 'password')
    # dump and reload to ensure all datetimes are converted to strings
    data = json.loads(json.dumps(data, cls=AnsibleJSONEncoder))
    # now make sure everything matches.
    assert data['hosts'] == hosts
    assert data['groups'] == groups


def test_populate_inventory(inventory, fake_opsy_server):
    """Make sure we populate ansible's inventory correctly."""
    # First let's populate the inventory from our fake opsy server.
    data = inventory._get_data(
        'http://localhost:80/', 'admin', 'password')
    inventory._populate_inventory(data)
    # Now we make sure the groups were generated correctly.
    groups = inventory.inventory.get_groups_dict()
    assert groups['default'] == ['westconsul', 'westprom']
    assert groups['prom_nodes'] == ['westprom']
    # Now let's make sure our vars loaded correctly.
    hosts = json.loads(open('tests/data/list_hosts.json', 'r').read())
    for host in hosts:
        # We add the things that it should have added.
        extra_data = {
            'inventory_file': None,
            'inventory_dir': None,
            'opsy_host_id': host['id']}
        if host['compiled_vars']:
            host['compiled_vars'].update(extra_data)
        else:
            host['compiled_vars'] == extra_data
        # Now compare
        assert host['compiled_vars'] == inventory.inventory.get_host(
            host['name']).vars
