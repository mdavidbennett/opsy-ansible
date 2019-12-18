from __future__ import (absolute_import, division, print_function)
from ansible.errors import AnsibleError
from ansible.module_utils.common._collections_compat import MutableMapping
from ansible.plugins.inventory import (BaseInventoryPlugin, Cacheable,
                                       to_safe_group_name, Constructable)

__metaclass__ = type

DOCUMENTATION = '''
    name: opsy
    plugin_type: inventory
    short_description: opsy inventory source
    requirements:
        - opsyclient
    description:
        - Get inventory hosts from the opsy service.
        - "Uses a configuration file as an inventory source, it must end in
          ``.opsy.yml`` or ``.opsy.yaml`` and has a ``plugin: opsy`` entry."
    extends_documentation_fragment:
        - inventory_cache
        - constructed
    options:
      plugin:
        description: the name of this plugin, it should always be set to
          'opsy' for this plugin to recognize it as it's own.
        required: True
        choices: ['opsy']
      url:
        description: url to opsy
        default: 'http://localhost:5000/'
        env:
            - name: ANSIBLE_OPSY_SERVER
      user:
        description: opsy authentication user
        required: True
        env:
            - name: ANSIBLE_OPSY_USER
      password:
        description: opsy authentication password
        required: True
        env:
            - name: ANSIBLE_OPSY_PASSWORD
      zone:
        description: the zone in opsy to use
        required: True
        env:
            - name: ANSIBLE_OPSY_ZONE
'''

EXAMPLES = '''
# my.opsy.yml
plugin: opsy
url: http://localhost:5000
user: ansible-tester
password: secure
zone: west
'''

# 3rd party imports
try:
    from opsyclient import OpsyClient
except ImportError:
    raise AnsibleError('This script requires opsyclient')


class InventoryModule(BaseInventoryPlugin, Cacheable, Constructable):
    ''' Host inventory parser for ansible using opsy as source. '''

    NAME = 'opsy'

    def __init__(self):

        super(InventoryModule, self).__init__()
        self.zone = None
        self.cache_key = None

    def verify_file(self, path):

        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(('opsy.yaml', 'opsy.yml')):
                valid = True
            else:
                self.display.vvv('Skipping due to inventory source not ending '
                                 'in "opsy.yaml" nor "opsy.yml"')
        return valid

    def _get_data(self, url, user_name, password):
        """Get the inventory data from opsy."""
        client = OpsyClient(url, user_name=user_name, password=password,
                            use_models=False)
        data = {}
        data['hosts'] = client.hosts.list_hosts(
            zone_name=self.zone).response().result
        data['groups'] = client.groups.list_groups(
            zone_name=self.zone).response().result
        return data

    def _populate_inventory(self, data):
        """Populate ansible's inventory with opsy's data."""
        # first get groups
        for group in data['groups']:
            self.inventory.add_group(to_safe_group_name(group['name']))
        # loop again to set children
        for group in data['groups']:
            for child in [x for x in data['groups']
                          if x['parent_id'] == group['id']]:
                self.inventory.add_child(group['name'], child['name'])
        # now setup hosts
        for host in data['hosts']:
            self.inventory.add_host(host['name'])
            self.inventory.set_variable(
                host['name'], 'opsy_host_id', host['id'])
            if isinstance(host['compiled_vars'], MutableMapping):
                for k, v in host['compiled_vars'].items():
                    self.inventory.set_variable(host['name'], k, v)
            for group_mapping in host['group_mappings']:
                self.inventory.add_child(
                    group_mapping['group_name'], host['name'])

    def parse(self, inventory, loader, path, cache=False):

        super(InventoryModule, self).parse(inventory, loader, path)

        # read config from file, this sets 'options'
        self._read_config_data(path)

        self.zone = self.get_option('zone')

        # update cache if the user has caching enabled and the cache is being
        # refreshed.
        # will update variable below in the case of an expired cache
        cache_key = self.get_cache_key(
            '{path}_{zone}'.format(path=path, zone=self.zone))
        cache_needs_update = not cache and self.get_option('cache')

        if cache:
            cache = self.get_option('cache')
        data = None
        if cache:
            try:
                data = self._cache[cache_key]
            except KeyError:
                # cache expired or doesn't exist yet
                cache_needs_update = True
        if not data:
            data = self._get_data(
                self.get_option('url'),
                self.get_option('user'),
                self.get_option('password'))
        if cache_needs_update:
            self._cache[cache_key] = data
        self._populate_inventory(data)
