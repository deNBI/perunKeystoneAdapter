import json
from denbi.bielefeld.perun.keystone import KeyStone

def import_json(path):
    with open(path, 'r') as json_file:
        json_obj = json.loads(json_file.read())
    return json_obj

class Endpoint:
    """
    Perun endpoint. Import and data from perun propagtion push service.

    Support JSON data in SCIM format and "deNBI Portal Compute Center" format.

    """

    def __init__(self,keystone = None,mode = "scim", store_email = True, support_quotas = True):
        '''

        :param keystone: initialized keystone object
        :param mode: 'scim' or 'denbi_portal_compute_center'
        :param store_email : should an available email address stored ?
        :param support_quotas : should quotas supported
        '''

        if keystone:
            self.keystone = keystone
        else:
            self.keystone = KeyStone()

        self.mode = mode
        self.store_email = store_email
        self.support_quotas = support_quotas

    def import_data(self, users_path, groups_path):
        '''
        Import data (in the given mode) into Keystone

        :param users_path: Path to user data (must be in json format)
        :param groups_path: Path to projet data (must be in json format)
        :return:
        '''

        if self.mode == "scim":
            self.__import_scim_userdata__(import_json(users_path))
            self.__import_scim_projectdata__(import_json(groups_path))
        elif self.mode == "denbi_portal_compute_center":
            self.__import_dpcc_userdata__(import_json(users_path))
            self.__import_dpcc_projectdata__(import_json(groups_path))
        else:
            raise ValueError("Unknown/Unsupported mode!")

    def __import_scim_userdata__(self,json_obj):
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
            if scim_user.has_key('id') and scim_user.has_key('login') and scim_user.has_key('status'):
                perun_id = str(scim_user['id'])
                elixir_id = str(scim_user['login'])
                enabled = scim_user['status'] == 'VALID'
                email = None
                if self.store_email and  scim_user.has_key('mail'):
                    email = str(scim_user['mail'])

                # user already registered in keystone
                if user_map.has_key(perun_id):
                    # check if user data changed
                    user = user_map[perun_id]
                    if not (\
                            user['perun_id'] == perun_id and \
                            user['elixir_id'] == elixir_id and \
                            user['email'] == email and \
                            user['enabled'] == enabled ):
                        # update user
                        self.keystone.users_update(perun_id, elixir_id = elixir_id, email = email, enabled=enabled)

                else:
                    # register user in keystone
                    self.keystone.users_create(elixir_id, perun_id, email=email, enabled=enabled)

                # add perun_id to temporary list
                user_ids.append(perun_id)

            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set (user_map.keys())

        for id in del_users:
            self.keystone.users_delete(id)


    def __import_scim_projectdata__(self,json_obj):

        #get current project_map from keystone
        project_map = self.keystone.projects_map()

        project_ids = []


        # convert scim json to keystone compatible hash
        for scim_project in json_obj:

            if scim_project.has_key('id') and scim_project.has_key('members'):
                perun_id = str(scim_project['id'])
                name = str(scim_project['name'])
                members =  []
                for m in scim_project['members']:
                    members.append(m['userId'])

                # if project already registered in keystone
                if project_map.has_key(perun_id):
                    # check if project data changed
                    project = project_map[perun_id]

                    if set(project['members']) !=  set(members):
                        self.keystone.projects_update(perun_id,members)
                else:
                    self.keystone.projects_create(perun_id,name=name,members=members)

                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set (project_map.keys())

        for id in del_projects:
            self.keystone.projects_delete(id)



    def __import_dpcc_userdata__(self,json_obj):
        # get current user_map from keystone
        user_map = self.keystone.users_map()

        user_ids = []

        # convert denbi_portal_compute_center json to keystone compatible hash
        for dpcc_user in json_obj:
            # check for mandantory fields (id, login, status)
            if dpcc_user.has_key('id') and dpcc_user.has_key('login-namespace:elixir-persistent') and dpcc_user.has_key('status'):
                perun_id = str(dpcc_user['id'])
                elixir_id = str(dpcc_user['login-namespace:elixir-persistent'])
                enabled = dpcc_user['status'] == 'VALID'
                email = None
                if self.store_email and  dpcc_user.has_key('preferredMail'):
                    email = str(dpcc_user['preferredMail'])

                # user already registered in keystone
                if user_map.has_key(perun_id):
                    # check if user data changed
                    user = user_map[perun_id]
                    if not ( \
                                    user['perun_id'] == perun_id and \
                                    user['elixir_id'] == elixir_id and \
                                    user['email'] == email and \
                                    user['enabled'] == enabled ):
                        # update user
                        self.keystone.users_update(perun_id, elixir_id, email, enabled)

                else:
                    # register user in keystone
                    self.keystone.users_create(elixir_id, perun_id, email=email, enabled=enabled)

                # add perun_id to temporary list
                user_ids.append(perun_id)
            else:
                # otherwise ignore user
                pass

        # Now we have to check if some keystone user entries must be deleted
        del_users = set(user_ids) ^ set (user_map.keys())

        for id in del_users:
            self.keystone.users_delete(id)


    def __import_dpcc_projectdata__(self,json_obj):
        #get current project_map from keystone
        project_map = self.keystone.projects_map()

        project_ids = []


        # convert scim json to keystone compatible hash
        for dpcc_project in json_obj:

            if dpcc_project.has_key('id') and dpcc_project.has_key('denbiProjectMembers'):
                perun_id = str(dpcc_project['id'])
                name = str(dpcc_project['name'])
                description = str(dpcc_project['description'])
                status = str(dpcc_project['denbiProjectStatus']) # values ?
                members =  []
                for m in dpcc_project['denbiProjectMembers']:
                    members.append(str(m['id']))

                # retrieve project quota
                number_of_vms = dpcc_project['denbiProjectNumberOfVms']
                disk_space = dpcc_project['denbiProjectDiskSpace'] # in GB ?
                special_purpose_hardware = dpcc_project ['denbiProjectSpecialPurposeHardware'] # values ?
                ram_per_vm = dpcc_project ['denbiProjectRamPerVm'] # in GB ?
                object_storage = dpcc_project ['denbiProjectObjectStorage'] # in GB ?

                # if project already registered in keystone
                if project_map.has_key(perun_id):
                    # check if project data changed
                    project = project_map[perun_id]

                    if set(project['members']) !=  set(members) or \
                            project['name'] != name or \
                            project.has_key('description') and project['description'] != description :
                        self.keystone.projects_update(perun_id,members)

                    # check for quotas and update it if possible
                    if self.support_quotas:
                        quotas = project['quotas']
                        if (quotas.hasKey('number_of_vms') and quotas['number_of_vms']  != number_of_vms) or\
                            (quotas.hasKey('disk_space') and quotas['disk_space']  != disk_space) or \
                            (quotas.hasKey('special_purpose_hardware') and quotas['special_purpose_hardware']  != special_purpose_hardware) or \
                            (quotas.hasKey('ram_per_vm') and quotas['ram_per_vm']  != ram_per_vm) or \
                            (quotas.hasKey('object_storage') and quotas['object_storage']  != object_storage):
                            self.keystone.project_quota(number_of_vms=number_of_vms,\
                                                    disk_space=disk_space,\
                                                    special_purpose_hardware=special_purpose_hardware,\
                                                    ram_per_vm = ram_per_vm,\
                                                    object_storage = object_storage)

                else:
                    self.keystone.projects_create(perun_id,name=name,description=description,members=members)
                    if self.support_quotas:
                        self.keystone.project_quota(number_of_vms=number_of_vms,\
                            disk_space=disk_space,\
                            special_purpose_hardware=special_purpose_hardware,\
                            ram_per_vm = ram_per_vm,\
                            object_storage = object_storage)
                project_ids.append(perun_id)

            else:
                # otherwise ignore project
                pass

        del_projects = set(project_ids) ^ set (project_map.keys())

        for id in del_projects:
            self.keystone.projects_delete(id)

