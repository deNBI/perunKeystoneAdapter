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

    def __init__(self, keystone=None, mode="scim", store_email=True, support_quotas=True, read_only=False):
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

                # retrieve project quota
                # quotas are defined by the following fields in the dict:
                # VMs: denbiProjectNumberOfVms
                # RAM: denbiRAMLimit
                # Cores: denbiCoresLimit
                # Volume: denbiVolumeLimit
                # Volume Counter: denbiVolumeCounter
                # Object Storage: denbiProjectObjectStorage
                # TODO: make a complete list
                number_of_vms = dpcc_project.get('denbiProjectNumberOfVms', None)
                disk_space = dpcc_project.get('denbiProjectDiskSpace', None)
                special_purpose_hardware = dpcc_project.get('denbiProjectSpecialPurposeHardware', None)
                ram_per_vm = dpcc_project.get('denbiProjectRamPerVm', None)
                object_storage = dpcc_project.get('denbiProjectObjectStorage', None)
                number_of_cpus = dpcc_project.get('denbiProjectNumberOfCpus', None)
                number_of_snapshots = dpcc_project.get('denbiProjectNumberOfSnapshots', None)
                volume_limit = dpcc_project.get('denbiProjectVolumeLimit', None)
                number_of_networks = dpcc_project.get('denbiProjectNumberOfNetworks', None)
                number_of_subnets = dpcc_project.get('denbiProjectNumberOfSubnets', None)
                number_of_router = dpcc_project.get('denbiProjectNumberOfRouter', None)

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
                        quotas = project['quotas']
                        # TODO(hxr): makes assumption that some quota vals are set. they're not.
                        modified = (
                            ('number_of_vms' in quotas and quotas['number_of_vms'] != number_of_vms),
                            ('disk_space' in quotas and quotas['disk_space'] != disk_space),
                            ('special_purpose_hardware' in quotas and quotas['special_purpose_hardware'] != special_purpose_hardware),
                            ('ram_per_vm' in quotas and quotas['ram_per_vm'] != ram_per_vm),
                            ('object_storage' in quotas and quotas['object_storage'] != object_storage),
                            ('number_of_cpus' in quotas and quotas['number_of_cpus'] != number_of_cpus),
                            ('number_of_snapshots' in quotas and quotas['number_of_snapshots'] != number_of_snapshots),
                            ('volume_limit' in quotas and quotas['volume_limit'] != volume_limit),
                            ('number_of_networks' in quotas and quotas['number_of_networks'] != number_of_networks),
                            ('number_of_subnets' in quotas and quotas['number_of_subnets'] != number_of_subnets),
                            ('number_of_router' in quotas and quotas['number_of_router'] != number_of_router)
                        )

                        # TODO(hxr): prod had none of these values on the quotas object, so none were attempted to be set.
                        if any(modified):
                            log.info("Updating quota vms=%s disk=%s hardware=%s ram=%s os=%s", number_of_vms, disk_space, special_purpose_hardware, ram_per_vm, object_storage)
                            self.keystone.project_quota(number_of_vms=number_of_vms,
                                                        disk_space=disk_space,
                                                        special_purpose_hardware=special_purpose_hardware,
                                                        ram_per_vm=ram_per_vm,
                                                        object_storage=object_storage,
                                                        number_of_cpus = number_of_cpus,
                                                        number_of_snapshots = number_of_snapshots,
                                                        volume_limit = volume_limit,
                                                        number_of_networks = number_of_networks,
                                                        number_of_subnets = number_of_subnets,
                                                        number_of_router = number_of_router)
                        else:
                            log.debug("Quota unchanged")

                else:
                    log.info("Creating project %s with name=%s members={%s}", perun_id, name, ','.join(members))
                    self.keystone.projects_create(perun_id, name=name, description=description, members=members)
                    if self.support_quotas:
                        log.info("Setting quota vms=%s disk=%s hardware=%s ram=%s os=%s", number_of_vms, disk_space, special_purpose_hardware, ram_per_vm, object_storage)
                        self.keystone.project_quota(number_of_vms=number_of_vms,
                                                    disk_space=disk_space,
                                                    special_purpose_hardware=special_purpose_hardware,
                                                    ram_per_vm=ram_per_vm,
                                                    object_storage=object_storage,
                                                    number_of_cpus = number_of_cpus,
                                                    number_of_snapshots = number_of_snapshots,
                                                    volume_limit = volume_limit,
                                                    number_of_networks = number_of_networks,
                                                    number_of_subnets = number_of_subnets,
                                                    number_of_router = number_of_router)
                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set(project_map.keys())

        for id in del_projects:
            log.info("Deleting project %s", id)
            self.keystone.projects_delete(id)
