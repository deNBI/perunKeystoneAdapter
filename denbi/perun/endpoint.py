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

from denbi.perun.keystone import KeyStone


def import_json(path):
    """
    Read path as json and return as object
    :param path: json file to read
    :return: json object
    """
    with open(path, 'r',encoding='utf-8') as json_file:
        json_obj = json.loads(json_file.read())
    return json_obj


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
    DENBI_OPENSTACK_QUOTA_MAPPING = {  # denbiProjectDiskSpace is the old. deprecated name
        'denbiProjectDiskSpace': {'name': 'gigabytes', 'factor': 1},
        'denbiProjectVolumeLimit': {'name': 'gigabytes', 'factor': 1},

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
        'denbiProjectNumberOfCpus': {'name': 'cores', 'factor': 1},
        'denbiCoresLimit': {'name': 'cores', 'factor': 1},

        # assume that all sites are using neutron....
        'denbiNrOfFloatingIPs': {'name': 'floatingip', 'factor': 1},

        # these were present in the first quota code,
        # but aren't registered with perun or set by the
        # portal...
        # 'denbiProjectNumberOfNetworks': { 'name' : 'network', 'factor' : 1 },
        # 'denbiProjectNumberOfSubnets': { 'name' : 'subnet', 'factor' : 1 },
        # 'denbiProjectNumberOfRouter': { 'name' : 'router', 'factor' : 1024 },

        'denbiProjectNumberOfSnapshots': {'name': 'snapshots', 'factor': 1},
        'denbiProjectVolumeCounter': {'name': 'volumes', 'factor': 1}}

    def __init__(self, keystone=None, mode="scim", store_email=True,
                 support_quotas=True, read_only=False, logging_domain="denbi"):
        '''

        :param keystone: initialized keystone object
        :param mode: 'scim' or 'denbi_portal_compute_center'
        :param store_email : should an available email address stored ?
        :param support_quotas : should quotas supported
        :param read_only: test mode
        :param logging_domain
        '''

        if keystone:
            if read_only and not isinstance(keystone, KeyStone):
                raise Exception("Read-only flag is only functional with internal keystone library")
            self.keystone = keystone
        else:
            self.keystone = KeyStone(read_only=read_only)

        self.mode = str(mode)
        self.store_email = bool(store_email)
        self.support_quotas = bool(support_quotas)
        self.read_only = read_only
        self.logging = logging.getLogger(logging_domain)

    def import_data(self, users_path, groups_path):
        '''
        Import data (in the given mode) into Keystone

        :param users_path: Path to user data (must be in json format)
        :param groups_path: Path to projet data (must be in json format)
        :return:
        '''

        self.logging.info("Importing data mode=%s users_path=%s groups_path=%s", self.mode, users_path, groups_path)
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

            # check for mandantory fields (id, login, status)
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
                        # update user
                        self.logging.info("Updating user %s elixir_id=%s email=%s enabled=%s", perun_id, elixir_id, email, enabled)
                        self.keystone.users_update(perun_id, elixir_id=elixir_id, email=email, enabled=enabled)

                else:
                    # register user in keystone
                    self.logging.info("Creating user %s elixir_id=%s email=%s, enabled=%s", perun_id, elixir_id, email, enabled)
                    self.keystone.users_create(elixir_id, perun_id, email=email, enabled=enabled)

                # add perun_id to temporary list
                user_ids.append(perun_id)

            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set(user_map.keys())

        for id in del_users:
            self.logging.info("Deleting user %s", id)
            self.keystone.users_delete(id)

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
                        self.logging.info("Updating project %s with {%s}", perun_id, ','.join(members))
                        self.keystone.projects_update(perun_id, members)
                else:
                    self.logging.info("Creating project %s with name=%s members={%s}", perun_id, name, ','.join(members))
                    self.keystone.projects_create(perun_id, name=name, members=members)

                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set(project_map.keys())

        for id in del_projects:
            self.logging.info("Deleting project %s", id)
            self.keystone.projects_delete(id)

    def __import_dpcc_userdata__(self, json_obj):
        # get current user_map from keystone
        user_map = self.keystone.users_map()

        user_ids = []

        # convert denbi_portal_compute_center json to keystone compatible hash
        for dpcc_user in json_obj:
            # check for mandantory fields (id, login, status)
            if 'id' in dpcc_user and 'login-namespace:elixir-persistent' in dpcc_user and 'status' in dpcc_user:
                perun_id = str(dpcc_user['id'])
                elixir_id = str(dpcc_user['login-namespace:elixir-persistent'])
                enabled = str(dpcc_user['status']) == 'VALID'
                email = None
                if self.store_email and 'preferredMail' in dpcc_user:
                    email = str(dpcc_user['preferredMail'])

                # user already registered in keystone
                if perun_id in user_map:
                    # check if user data changed
                    user = user_map[perun_id]
                    if not (user['perun_id'] == perun_id
                            and user['elixir_id'] == elixir_id
                            and user['email'] == email
                            and user['enabled'] == enabled):
                        # update user
                        self.logging.info("Updating user %s elixir_id=%s email=%s enabled=%s", perun_id, elixir_id, email, enabled)
                        self.keystone.users_update(perun_id, elixir_id, email, enabled)
                else:
                    # register user in keystone
                    self.logging.info("Creating user %s elixir_id=%s email=%s, enabled=%s", perun_id, elixir_id, email, enabled)
                    self.keystone.users_create(elixir_id, perun_id, email=email, enabled=enabled)

                # add perun_id to temporary list
                user_ids.append(perun_id)
            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set(user_map.keys())

        for id in del_users:
            self.logging.info("Deleting user %s", id)
            self.keystone.users_delete(id)

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
                        self.logging.info("Updating project %s with {%s}", perun_id, ','.join(members))
                        self.keystone.projects_update(perun_id, members)

                    # check for quotas and update it if possible
                    if self.support_quotas:
                        self._set_quotas(project, dpcc_project)

                else:
                    self.logging.info("Creating project %s with name=%s members={%s}", perun_id, name, ','.join(members))
                    project = self.keystone.projects_create(perun_id, name=name, description=description, members=members)
                    if self.support_quotas:
                        if self.read_only:
                            self.logging.info("Not setting quotas for new project %s, readonly mode", name)
                        else:
                            self._set_quotas(project, dpcc_project)
                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set(project_map.keys())

        for id in del_projects:
            self.logging.info("Deleting project %s", id)
            self.keystone.projects_delete(id)

    def _set_quotas(self, project, project_definition):

        manager = self.keystone.quota_factory.get_manager(project['id'])

        for denbi_quota_name in self.DENBI_OPENSTACK_QUOTA_MAPPING:
            value = project_definition.get(denbi_quota_name, None)
            if value is not None:
                os_quota = self.DENBI_OPENSTACK_QUOTA_MAPPING[denbi_quota_name]
                # if factor is None ignore it
                if os_quota is None:
                    self.logging.info("Skipping quota %s for project [%s,%s], not supported yet", denbi_quota_name, project['perun_id'], project['id'])
                else:

                    try:
                        self.logging.debug("Checking quota %s for project [%s,%s]", denbi_quota_name, project['perun_id'], project['id'])
                        # use os_quota['factor'] on value
                        value = value * os_quota['factor']

                        current = manager.get_current_quota(os_quota['name'])
                        self.logging.debug("Comparing %s vs %s", current, value)
                        if manager.check_value(os_quota['name'], value):
                            if manager.get_current_quota(os_quota['name']) != value:
                                if self.read_only:
                                    self.logging.info("Would update quota %s for project [%s,%s] to from value %s to value %s",
                                                      denbi_quota_name, project['perun_id'], project['id'], current, value)
                                else:
                                    self.logging.info("Updating quota %s for project [%s,%s] to from value %s to value %s",
                                                      denbi_quota_name, project['perun_id'], project['id'], current, value)
                                    manager.set_value(os_quota['name'], value)
                        else:
                            self.logging.warn("Project [%s,%s] : Unable to set quota %s to %s, would exceed currently used resources",
                                              project['perun_id'], project['id'], denbi_quota_name, value)
                    except ValueError as error:
                        self.logging.error("Project [%s,%s] : Unable to check/set quota %s: %s", project['perun_id'], project['id'], denbi_quota_name, str(error))
