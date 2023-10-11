# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import logging
import re

from denbi.perun.keystone import KeyStone


def import_json(path):
    """
    Read path as json and return as object
    :param path: json file to read
    :return: json object
    """
    with open(path, 'r', encoding='utf-8') as json_file:
        json_obj = json.loads(json_file.read())
    return json_obj


def validate_cidr(cidr):
    """
    Validates a CIDR (Classless Inter-Domain Routing) notation
    :param cidr: value to be validated
    :return: True or False
    """

    # Regular expression pattern to match a CIDR notation
    cidr_pattern = r'^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$'

    # Check if the input matches the CIDR pattern
    if not re.match(cidr_pattern, cidr):
        return False

    # Split the CIDR into its address and prefix parts
    parts = cidr.split('/')
    ip_address = parts[0]
    prefix_length = int(parts[1])

    # Validate the IP address
    ip_parts = ip_address.split('.')
    if len(ip_parts) != 4:
        return False

    for part in ip_parts:
        try:
            octet = int(part)
            if octet < 0 or octet > 255:
                return False
        except ValueError:
            return False

    # Validate the prefix length
    if prefix_length < 0 or prefix_length > 32:
        return False

    return True


class Endpoint(object):
    """
    Perun endpoint. Import and data from perun propagation push service.

    Support JSON data in SCIM format and "deNBI Portal Compute Center" format.

    """

    # Mapping of quota names from de.NBI portal to openstack ns.
    # - a value of None indicates that the quota may be present, but is not
    #   implemented so far
    # - a value is a  map containing  the corresponding openstack quota name and a factor.
    # - a factor factorize the de.NBI quota value (1 - no factorize - in most cases)
    # - some de.NBI quotas are deprecated, but may still be in use in older projects
    DENBI_OPENSTACK_QUOTA_MAPPING = {
        # denbiProjectDiskSpace is the old. deprecated name
        'denbiProjectDiskSpace': None,
        'denbiVolumeLimit': {'name': 'gigabytes', 'factor': 1},

        # this is a deprecated setting without a real
        # openstack equivalent...
        'denbiProjectRamPerVm': None,

        # custom denbi quotas to control access to object
        # storage and fpga/gpu hardware. no implementation yet
        'denbiProjectObjectStorage': None,
        'denbiProjectSpecialPurposeHardware': None,

        'denbiProjectNumberOfVms': {'name': 'instances', 'factor': 1},
        'denbiRAMLimit': {'name': 'ram', 'factor': 1024},
        # old and new quota for vCPUs
        'denbiProjectNumberOfCpus': None,
        'denbiCoresLimit': {'name': 'cores', 'factor': 1},

        # assume that all sites are using neutron...  not used by the portal
        'denbiNrOfFloatingIPs': None,

        # Not used by the portal ...
        'denbiProjectNumberOfSnapshots': None,
        'denbiVolumeCounter': {'name': 'volumes', 'factor': 1}}

    def __init__(self,
                 keystone=None,
                 mode="scim",
                 store_email=True,
                 support_quotas=True,
                 support_elixir_name=True,
                 support_ssh_key=True,
                 support_router=False,
                 support_network=False,
                 support_default_ssh_sgrule=False,
                 external_network_id="",
                 network_cidr="192.168.33.0/24",
                 read_only=False,
                 logging_domain="denbi",
                 report_domain="report"):
        '''

        :param keystone: initialized keystone object
        :param mode: 'scim' or 'denbi_portal_compute_center'
        :param store_email : should an available email address be stored?
        :param support_quotas : should quotas supported ?
        :param support_elixir_name : should an available elixir_name be stored ?
        :param support_router: should a router generated (for new projects)
        :param support_network: should a network/subnetwork generated and attached to router (for new projects)
        :param support_default_ssh_sgrule: should a ssh sg rule created with defautl sg
        :param external_network_id: neutron id of external network used
        :param network_cidr: CIDR notation of the internal network to be created (
        :param read_only: test mode
        :param logging_domain: domain where "standard" logs are logged (default is "denbi")
        :param report_domain: domain where "update" logs are reported (default is "report")
        '''

        if keystone:
            if read_only and not isinstance(keystone, KeyStone):
                raise Exception("Read-only flag is only functional with internal keystone library")
            self.keystone = keystone
        else:
            self.keystone = KeyStone(read_only=read_only)

        self.neutron = self.keystone._neutron

        self.mode = str(mode)
        self.store_email = bool(store_email)
        self.support_quotas = bool(support_quotas)
        self.support_elixir_name = bool(support_elixir_name)
        self.support_ssh_key = bool(support_ssh_key)
        self.support_router = bool(support_router)
        self.support_network = bool(support_network)
        self.support_default_ssh_sgrule = bool(support_default_ssh_sgrule)
        self.external_network_id = external_network_id
        self.network_cidr = network_cidr
        self.read_only = read_only
        self.log = logging.getLogger(logging_domain)
        self.log2 = logging.getLogger(report_domain)

        # check if CIDR mask
        if not (validate_cidr(self.network_cidr)):
            raise RuntimeError(f"Network CIDR '{self.network_cidr}' is invalid.")

        # check if external_network_id is a valid id
        if self.support_network:
            if external_network_id:
                if not (self.neutron.list_networks(id=external_network_id)['networks']):
                    self.log.fatal(f"External network  '{external_network_id}' not found.")
                    raise RuntimeError(f"External network  '{external_network_id}' not found.")
            else:
                self.log.fatal("Support_network option is set, but external_network_id is NOT set.")
                raise RuntimeError("Support_network option is set, but external_network_id is NOT set.")

    def import_data(self, users_path, groups_path):
        '''
        Import data (in the given mode) into Keystone

        :param users_path: Path to user data (must be in json format)
        :param groups_path: Path to project data (must be in json format)
        :return:
        '''

        self.log.info("Importing data mode=%s users_path=%s groups_path=%s", self.mode, users_path, groups_path)
        if self.mode == "scim":
            self.__import_scim_userdata__(import_json(users_path))
            self.__import_scim_projectdata__(import_json(groups_path))
        elif self.mode == "denbi_portal_compute_center":
            self.__import_dpcc_userdata__(import_json(users_path))
            self.__import_dpcc_projectdata__(import_json(groups_path))
        else:
            raise ValueError("Unknown/Unsupported mode!")

    def __import_scim_userdata__(self, json_obj):
        '''
        Import users data in scim format
        :param json_obj:
        :return:
        '''
        # get current user_map from keystone
        user_map = self.keystone.users_map()

        user_ids = []

        # convert scim json to keystone compatible hash
        for scim_user in json_obj:

            # check for mandatory fields (id, login, status)
            if 'id' in scim_user and 'login' in scim_user and 'status' in scim_user:
                perun_id = str(scim_user['id'])
                elixir_id = str(scim_user['login'])
                enabled = str(scim_user['status']) == 'VALID'
                email = None
                if self.store_email and 'mail' in scim_user:
                    email = str(scim_user['mail'])

                # user already registered in keystone
                if perun_id in user_map:
                    # check if user data changed
                    user = user_map[perun_id]
                    if not (user['perun_id'] == perun_id
                            and user['elixir_id'] == elixir_id
                            and user['email'] == email
                            and user['enabled'] == enabled):
                        # update user ...
                        self.keystone.users_update(perun_id, elixir_id=elixir_id, email=email, enabled=enabled)
                        # ... and log to update log
                        self.log2.info(
                            f"user [{perun_id},{elixir_id}]: update and {'enabled' if enabled else 'disabled'}")
                else:
                    # register user ...
                    self.keystone.users_create(elixir_id, perun_id, email=email, enabled=enabled)
                    # ... and log to update log
                    self.log2.info(f"user [{perun_id},{elixir_id}]: create and {'enabled' if enabled else 'disabled'}")

                # add perun_id to temporary list
                user_ids.append(perun_id)

            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set(user_map.keys())

        for id in del_users:
            self.keystone.users_delete(id)
            self.log2.info(f"user {id}: deleted")

    def __import_scim_projectdata__(self, json_obj):

        # get current project_map from keystone
        project_map = self.keystone.projects_map()
        project_ids = []

        # convert scim json to keystone compatible hash
        for scim_project in json_obj:

            if 'id' in scim_project and 'members' in scim_project:
                perun_id = str(scim_project['id'])
                name = str(scim_project['name'])
                members = []
                for m in scim_project['members']:
                    members.append(m['userId'])

                # if project already registered in keystone
                if perun_id in project_map:
                    # check if project data changed
                    project = project_map[perun_id]

                    if set(project['members']) != set(members):
                        # Update project ...
                        self.keystone.projects_update(perun_id, members)
                        # ... and log to update log
                        self.log2.info(f"project [{perun_id},{name}]: update with members [{','.join(members)}]")
                else:
                    # Create project ...
                    self.keystone.projects_create(perun_id, name=name, members=members)
                    # ... and log to update log
                    self.log2.info(f"project [{perun_id},{name}]: create with members {','.join(members)}")

                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set(project_map.keys())

        for id in del_projects:
            # Delete project ...
            self.keystone.projects_delete(id)
            # ... log to update log
            self.log2.info(f"project [{id}]")

    def __import_dpcc_userdata__(self, json_obj):
        # get current user_map from keystone
        user_map = self.keystone.users_map()

        user_ids = []

        # convert denbi_portal_compute_center json to keystone compatible hash
        for dpcc_user in json_obj:
            # check for mandatory fields (id, login, status)
            if 'id' in dpcc_user and 'login-namespace:elixir-persistent' in dpcc_user and 'status' in dpcc_user:
                perun_id = str(dpcc_user['id'])
                elixir_id = str(dpcc_user['login-namespace:elixir-persistent'])
                elixir_name = None
                if self.support_elixir_name and str(dpcc_user['login-namespace:elixir']):
                    elixir_name = str(dpcc_user['login-namespace:elixir'])
                enabled = str(dpcc_user['status']) == 'VALID'
                email = None
                if self.store_email and 'preferredMail' in dpcc_user:
                    email = str(dpcc_user['preferredMail'])
                ssh_key = None
                if self.support_ssh_key and \
                        'sshPublicKey' in dpcc_user and \
                        dpcc_user['sshPublicKey'] is not None and \
                        len(dpcc_user['sshPublicKey']) > 0:
                    ssh_key = str(dpcc_user['sshPublicKey'][0])

                # user already registered in keystone
                if perun_id in user_map:
                    # check if user data changed
                    user = user_map[perun_id]
                    if not (user['perun_id'] == perun_id
                            and user['elixir_id'] == elixir_id
                            and user['elixir_name'] == elixir_name
                            and user['email'] == email
                            and user['enabled'] == enabled
                            and user['ssh_key'] == ssh_key):
                        # update user
                        self.keystone.users_update(perun_id, elixir_id=elixir_id, elixir_name=elixir_name,
                                                   ssh_key=ssh_key, email=email, enabled=enabled)
                        # ... and log to update log
                        self.log2.info(
                            f"user [{perun_id},{elixir_id}]: update and {'enabled' if enabled else 'disabled'}")
                else:
                    # register user ...
                    self.keystone.users_create(elixir_id, perun_id, elixir_name=elixir_name, email=email,
                                               ssh_key=ssh_key, enabled=enabled)
                    # ... and log to update log
                    self.log2.info(f"user [{perun_id},{elixir_id}]: create and {'enabled' if enabled else 'disabled'}")

                # add perun_id to temporary list
                user_ids.append(perun_id)
            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set(user_map.keys())

        for id in del_users:
            # delete user ...
            self.keystone.users_delete(id)
            # ... and log to update log

            self.log2.info(f"user [{id}]: deleted")

    def __import_dpcc_projectdata__(self, json_obj):
        # get current project_map from keystone
        project_map = self.keystone.projects_map()
        project_ids = []

        # convert scim json to keystone compatible hash
        for dpcc_project in json_obj:

            if 'id' in dpcc_project and 'denbiProjectMembers' in dpcc_project:
                perun_id = str(dpcc_project['id'])  # as ascii str
                name = str(dpcc_project['name'])  # as ascii str
                description = dpcc_project['description']  # as unicode str
                # status = str(dpcc_project['denbiProjectStatus'])  # values ?
                members = []
                for m in dpcc_project['denbiProjectMembers']:
                    members.append(str(m['id']))  # as ascii str

                # if project already registered in keystone
                if perun_id in project_map:
                    # check if project data changed
                    project = project_map[perun_id]

                    if set(project['members']) != set(members) or \
                            project['name'] != name or \
                            'description' in project and project['description'] != description:
                        # Update project ...
                        self.keystone.projects_update(perun_id, members)
                        # ... and log to update logger
                        self.log2.info(f"project [{perun_id},{name}]: update with {','.join(members)}")

                    # check for quotas and update it if possible
                    if self.support_quotas:
                        if self.read_only:
                            self.log.info(f"project [{perun_id},{name}]: not setting quotas in  readonly mode.")
                        else:
                            self._set_quotas(project, dpcc_project)
                else:
                    # create project ...
                    project = self.keystone.projects_create(perun_id, name=name, description=description,
                                                            members=members)
                    # ... and log to update logger
                    self.log2.info(f"project [{perun_id},{name}]: create with members {','.join(members)}")

                    # check for quotas and update it if possible
                    if self.support_quotas:
                        if self.read_only:
                            self.log.info(f"project [{perun_id},{name}]: not setting quotas in  readonly mode.")
                        else:
                            self._set_quotas(project, dpcc_project)
                    # create router
                    if self.support_router:
                        self._create_router(project, not (self.support_network))

                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set(project_map.keys())

        for id in del_projects:
            # Delete project ...
            self.keystone.projects_delete(id)
            # ... and log to update logger
            self.log2.info(f"project [{id}]: deleted")

    def _set_quotas(self, project, project_definition):
        '''
        Set/adjust quota for given project


        :param project:
        :param project_definition:
        :return:
        '''

        manager = self.keystone.quota_factory.get_manager(project['id'])

        for denbi_quota_name in self.DENBI_OPENSTACK_QUOTA_MAPPING:
            value = project_definition.get(denbi_quota_name, None)
            if value is not None:
                os_quota = self.DENBI_OPENSTACK_QUOTA_MAPPING[denbi_quota_name]
                # if factor is None ignore it
                if os_quota is None:
                    self.log.debug(f"project [{project['perun_id']},{project['name']}]:"
                                   f" skipping quota {denbi_quota_name}, not supported yet")
                else:

                    try:
                        self.log.debug(f"project [{project['perun_id']},{project['name']}]:"
                                       f" checking quota {denbi_quota_name}")

                        # use os_quota['factor'] on value
                        value = value * os_quota['factor']

                        current = manager.get_current_quota(os_quota['name'])
                        self.log.debug(f"project [{project['perun_id']},{project['name']}]:"
                                       f" comparing %s vs %s", project['perun_id'], project['name'], current, value)
                        if manager.check_value(os_quota['name'], value):
                            if manager.get_current_quota(os_quota['name']) != value:
                                if self.read_only:
                                    # Log to update logger.
                                    self.log.info(f"project [{project['perun_id']},{project['name']}]:"
                                                  f" would update quota {denbi_quota_name} from value {current} to value {value}")
                                else:
                                    # Update quota ...
                                    manager.set_value(os_quota['name'], value)
                                    # ... and log to update logger
                                    self.log2.info(f"project [{project['perun_id']},{project['name']}]:"
                                                   f" update quota {denbi_quota_name} from value {current} to value {value}")
                        else:
                            self.log.warning(f"project [{project['perun_id']},{project['name']}]:"
                                             f" unable to set quota {denbi_quota_name}s to {value}, would exceed currently used resources,")
                    except ValueError as error:
                        self.log.error(f"project [{project['perun_id']},{project['name']}]:"
                                       f" unable to check/set quota {denbi_quota_name}:{str(error)}")

    def _create_router(self, project, router_only=False):
        """
        Creates a new router for a project, add a gateway and append optional a network/subnetwork

        :param project:
        :param router_only - creates only a router without attached network/subnet
        :return:
        """

        # create router
        _tmp_router = {'name': f"{project['name']}_router",
                       'admin_state_up': True,
                       'project_id': project['id'],
                       'external_gateway_info': {
                           'network_id': self.external_network_id

                       }}

        tmp_router = self.keystone._neutron.create_router(body={'router': _tmp_router})

        self.log2.info(f"project [{project['id']},{project['name']}]:"
                       f"create router {tmp_router['router']['name']}")

        if not (router_only):
            # create network
            _tmp_net = {'name': f"{project['name']}_net",
                        'project_id': project['id'],
                        'shared': False,
                        'admin_state_up': True,
                        'port_security_enabled': True,
                        }

            tmp_net = self.keystone._neutron.create_network(body={'network': _tmp_net})
            #  create subnet
            _tmp_subnet = {'name': f"{project['name']}_subnet",
                           'enable_dhcp': True,
                           'ip_version': 4,
                           'network_id': tmp_net['network']['id'],
                           'cidr': "192.168.192.0/24",
                           'allocation_pools': [{'start': '192.168.192.10', 'end': '192.168.192.200'}],
                           'project_id': project['id']}
            tmp_subnet = self.keystone._neutron.create_subnet(body={'subnet': _tmp_subnet})
            # attach subnet to router
            self.keystone._neutron.add_interface_router(tmp_router['router']['id'],
                                                        body={'subnet_id': tmp_subnet['subnet']['id']})

            self.log2.info(f"project [{project['id']},{project['name']}]:"
                           f"create network {tmp_net['network']['name']} with subnet {tmp_subnet['subnet']['name']}")

    def _delete_routers(self, project_id):
        """
        Remove all routers and networks belonging associated to the given project.
        :param project: map describing a project
        :return:
        """

        router_list = self.neutron.list_routers(project_id=project_id)["routers"]
        network_list = self.neutron.list_networks(project_id=project_id)["networks"]
        subnet_list = self.neutron.list_subnets(project_id=project_id)["subnets"]
        port_list = self.neutron.list_ports(device_owner='network:router_interface',
                                            project_id=project_id)["ports"]

        # remove interface from all routers
        for port in port_list:
            device_id = port["device_id"]
            for router in router_list:
                if router["id"] == port["device_id"]:
                    self.neutron.remove_interface_router(router["id"], body={"port_id": port["id"]})

        # delete router
        for router in router_list:
            self.neutron.delete_router(router["id"])

        # delete subnet
        for subnet in subnet_list:
            self.neutron.delete_subnet(subnet["id"])

        # delete network
        for network in network_list:
            self.neutron.delete_network(network["id"])

        # delete security-groups
        sg_list = self.neutron.list_security_groups(project_id=project_id)['security_groups']
        for sg in sg_list:
            self.neutron.delete_security_group(sg['id'])

    def _add_ssh_sgrule(self, project_id):
        """
        Add a security group rule to allow ssh access from 0.0.0.0.
        :param project_id: map describing project
        :return:
        """
        default_sg = self.neutron.list_security_groups(project_id=project_id, name="default")["security_groups"]

        if default_sg:
            self.neutron.create_security_group_rule(body={'security_group_rule': {
                                                            'security_group_id': default_sg[0]["id"],
                                                            'ethertype': 'IPv4',
                                                            'direction': 'ingress',
                                                            'protocol': 'tcp',
                                                            'port_range_min': 22,
                                                            'port_range_max': 22,
                                                            'remote_ip_prefix': '0.0.0.0/0',
                                                            'description': 'Allow ssh access.'}
                                                            })