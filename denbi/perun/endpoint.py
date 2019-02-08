import json
import logging

from denbi.perun.keystone import KeyStone

log = logging.getLogger(__name__)


def import_json(path):
    with open(path, 'r') as json_file:
        json_obj = json.loads(json_file.read())
    return json_obj


class Endpoint:
    """
    Perun endpoint. Import and data from perun propagation push service.

    Support JSON data in SCIM format and "deNBI Portal Compute Center" format.

    """

    # mapping of quota names in the de.NBI portal datasets to openstack quotas
    # a value of None indicates that the quota may be present, but is not
    # implemented so far
    # some names are deprecated, but may still be in use in older projects
    DENBI_QUOTA_NAMES = {  # denbiProjectDiskSpace is the old. deprecated name
                           'denbiProjectDiskSpace': 'gigabytes',
                           'denbiProjectVolumeLimit': 'gigabytes',

                           # this is a deprecated setting without a real
                           # openstack equivalent...
                           'denbiProjectRamPerVm': None,

                           # custom denbi quotas to control access to object
                           # storage and fpga/gpu hardware. no implementation yet
                           'denbiProjectObjectStorage': None,
                           'denbiProjectSpecialPurposeHardware': None,

                           'denbiProjectNumberOfVms': 'instances',
                           'denbiRAMLimit': 'ram',
                           # old and new quota for vCPUs
                           'denbiProjectNumberOfCpus': 'cores',
                           'denbiCoresLimit': 'cores',

                           # assume that all sites are using neutron....
                           'denbiNrOfFloatingIPs': 'floatingip',

                           # these were present in the first quota code,
                           # but aren't registered with perun or set by the
                           # portal...
                           # 'denbiProjectNumberOfNetworks': 'network',
                           # 'denbiProjectNumberOfSubnets': 'subnet',
                           # 'denbiProjectNumberOfRouter': 'router',

                           'denbiProjectNumberOfSnapshots': 'snapshots',
                           'denbiProjectVolumeCounter': 'volumes'}

    def __init__(self, keystone=None, mode="scim", store_email=True,
                 support_quotas=True, read_only=False):
        '''

        :param keystone: initialized keystone object
        :param mode: 'scim' or 'denbi_portal_compute_center'
        :param store_email : should an available email address stored ?
        :param support_quotas : should quotas supported
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

    def import_data(self, users_path, groups_path):
        '''
        Import data (in the given mode) into Keystone

        :param users_path: Path to user data (must be in json format)
        :param groups_path: Path to projet data (must be in json format)
        :return:
        '''

        log.info("Importing data mode=%s users_path=%s groups_path=%s", self.mode, users_path, groups_path)
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
                        log.info("Updating user %s elixir_id=%s email=%s enabled=%s", perun_id, elixir_id, email, enabled)
                        self.keystone.users_update(perun_id, elixir_id=elixir_id, email=email, enabled=enabled)

                else:
                    # register user in keystone
                    log.info("Creating user %s elixir_id=%s email=%s, enabled=%s", perun_id, elixir_id, email, enabled)
                    self.keystone.users_create(elixir_id, perun_id, email=email, enabled=enabled)

                # add perun_id to temporary list
                user_ids.append(perun_id)

            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set(user_map.keys())

        for id in del_users:
            log.info("Deleting user %s", id)
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
                        log.info("Updating project %s with {%s}", perun_id, ','.join(members))
                        self.keystone.projects_update(perun_id, members)
                else:
                    log.info("Creating project %s with name=%s members={%s}", perun_id, name, ','.join(members))
                    self.keystone.projects_create(perun_id, name=name, members=members)

                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set(project_map.keys())

        for id in del_projects:
            log.info("Deleting project %s", id)
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
                        log.info("Updating user %s elixir_id=%s email=%s enabled=%s", perun_id, elixir_id, email, enabled)
                        self.keystone.users_update(perun_id, elixir_id, email, enabled)
                else:
                    # register user in keystone
                    log.info("Creating user %s elixir_id=%s email=%s, enabled=%s", perun_id, elixir_id, email, enabled)
                    self.keystone.users_create(elixir_id, perun_id, email=email, enabled=enabled)

                # add perun_id to temporary list
                user_ids.append(perun_id)
            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set(user_map.keys())

        for id in del_users:
            log.info("Deleting user %s", id)
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

                    # TODO(hxr) prod, this was not working so I set to `True`
                    if set(project['members']) != set(members) or \
                            project['name'] != name or \
                            'description' in project and project['description'] != description:
                        log.info("Updating project %s with {%s}", perun_id, ','.join(members))
                        self.keystone.projects_update(perun_id, members)

                    # check for quotas and update it if possible
                    if self.support_quotas:
                        self._set_quotas(project['id'], dpcc_project)

                else:
                    log.info("Creating project %s with name=%s members={%s}", perun_id, name, ','.join(members))
                    project = self.keystone.projects_create(perun_id, name=name, description=description, members=members)
                    if self.support_quotas:
                        if self.read_only:
                            log.info("Not setting quotas for new project %s, readonly mode", name)
                        else:
                            self._set_quotas(project['id'], dpcc_project)
                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set(project_map.keys())

        for id in del_projects:
            log.info("Deleting project %s", id)
            self.keystone.projects_delete(id)

    def _set_quotas(self, project_id, project_definition):
        manager = self.keystone.quota_factory.get_manager(project_id)

        for name in self.DENBI_QUOTA_NAMES:
            value = project_definition.get(name, None)
            if value is not None:
                quota_name = self.DENBI_QUOTA_NAMES[name]
                if quota_name is None:
                    log.info("Skipping quota %s for project %s, not supported yet", name, project_id)
                else:
                    try:
                        log.debug("Checking quota %s for project %s",
                                  quota_name, project_id)
                        current = manager.get_current_quota(quota_name)
                        log.debug("Comparing %s vs %s", current, value)
                        if manager.check_value(quota_name, value):
                            if manager.get_current_quota(quota_name) != value:
                                if self.read_only:
                                    log.info("Would update quota %s for project %s to from value %s to value %s",
                                             quota_name, project_id, current, value)
                                else:
                                    log.info("Updating quota %s for project %s to from value %s to value %s",
                                             quota_name, project_id, current, value)
                                    manager.set_value(quota_name, value)
                        else:
                            log.warn("Unable to set quota %s to %s, would exceed currently used resources",
                                     quota_name, value)
                    except ValueError as error:
                        log.error("Unable to check/set quota %s: %s", quota_name, str(error))
