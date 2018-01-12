import os

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client


class KeyStone:
    """
    Keystone simplifies the communication with Openstack. Offers shortcuts for common functions and also
    simplifies data structures returned by Keystone and offers own data structure for denbi_user and denbi_project.

    Every user and every project generted by this class is marked with  perun propagation auto generated flag.

    denbi_user = {id: string, elixir_id: string, perun_id: string, email: string, enabled: boolean}
    denbi_project = {id: string, perun_id: string, enabled: boolean, members: [denbi_user]}
    """

    def __init__(self,environ=None, default_role = "_member", create_default_role = False, flag = "perun_propagation", support_quotas = True):
        """
        Create a new Openstack Keystone session using the system environment.
        The following variables are considered:
        - OS_AUTH_URL
        - OS_USERNAME
        - OS_PASSWORD
        - OS_PROJECT_NAME
        - OS_USER_DOMAIN_NAME

        Instead of the system variables a "local" enviroment (a dict) can be explicitly set

        :param environ : local environ used instead of system environment
        :param default_role : default role used for all users (default is "_member_")
        :param create_default_role: create a default role if it not exists (default is False)
        :param flag : value used to mark users/projects (default is perun_propagation)
        :param support_quotas:

        """

        if environ == None : # use os enviroment settings if no explicit environ is given
            self.auth_url = os.environ['OS_AUTH_URL']
            self.username = os.environ['OS_USERNAME'],
            self.password = os.environ['OS_PASSWORD'],
            self.project_name = os.environ['OS_PROJECT_NAME'],
            self.domain_name = os.environ['OS_USER_DOMAIN_NAME']
        else :
            self.auth_url = environ['OS_AUTH_URL']
            self.username = environ['OS_USERNAME']
            self.password = environ['OS_PASSWORD']
            self.project_name = environ['OS_PROJECT_NAME']
            self.domain_name = environ['OS_USER_DOMAIN_NAME']

        # create new keystone client
        auth = v3.Password(auth_url=self.auth_url,
                           username=self.username,
                           password=self.password,
                           project_name=self.project_name,
                           user_domain_name=self.domain_name,
                           project_domain_name=self.domain_name)
        sess = session.Session(auth=auth)
        self.keystone = client.Client(session=sess)

        #get domain id for used domain name
        self.domain_id = self.keystone.domains.list(name=self.domain_name)[0].id


        # Check if role exists ...
        self.default_role = default_role
        self.default_role_id = None
        for role  in self.keystone.roles.list():
            if role.name == self.default_role:
                self.default_role_id = role.id
                break

        # create it if wished
        if not(self.default_role_id):
            if create_default_role:
                role = self.keystone.roles.create(self.default_role)
                self.default_role_id = role.id
            else:
                raise Exception("Default role "+default_role+" does not exists and should not be created!")

        self.flag = flag

        self.support_quotas = support_quotas

        # initialize user and project map
        self.denbi_user_map = {}
        self.__user_id2perun_id__ = {}
        self.denbi_project_map = {}
        self.__project_id2perun_id__  = {}


    def users_create(self, elixir_id, perun_id , email = None, enabled = True):
        """
        Create a new user and updates internal user list
        :param elixir_id: elixir_id of the user to be created
        :param perun_id: perun_id of the user to be created
        :param email: email of the user to be created (optional, default is None)
        :param enabled: status of the user (optional, default is None)
        :return: a denbi_user hash {id:string, elixir_id:string, perun_id:string, email:string, enabled: boolean}
        """
        os_user = self.keystone.users.create(name=str(elixir_id),\
                                             email=str(email),\
                                             perun_id=str(perun_id),\
                                             enabled=enabled,\
                                             deleted=False,\
                                             flag=self.flag)
        denbi_user= {'id': os_user.id,
                     'elixir_id' : os_user.name,
                     'perun_id' : os_user.perun_id,
                     'enabled' : os_user.enabled,
                     'deleted' : False}

        if hasattr(os_user,'email'):
            denbi_user['email'] = os_user.email
        else:
            denbi_user['email'] = None


        self.__user_id2perun_id__[os_user.id] = os_user.perun_id
        self.denbi_user_map[denbi_user['perun_id']] = denbi_user

        return denbi_user;

    def users_delete(self, perun_id):
        """
        Disable the user and tag it as deleted. Since it is dangerous to delete a user completly, the delete function
        just disable the user and tag it as deleted. To remove an user completely use the function terminate.
        :param perun_id: perunid of user to be deleted
        :return:
        """
        self.users_update(perun_id,enabled=False,deleted=True)

    def users_terminate(self,perun_id):
        """
        Delete a user
        :param perun_id: perunid of user to be deleted
        :return:
        """
        if self.denbi_user_map.has_key(perun_id):
            denbi_user = self.denbi_user_map[perun_id]
            # delete user
            self.keystone.users.delete(denbi_user['id'])
            # remove entry from map
            del(self.denbi_user_map[perun_id])
        else:
            raise ValueError('User with perun_id '+id+' not found in user_map')

    def users_update(self, perun_id, elixir_id = None , email = None , enabled = None , deleted=False):
        """
        Update an existing user entry.


        :param elixir_id: elixir id
        :param email: email
        :param enabled: status
        :return: the modified denbi_user hash
        """
        if self.denbi_user_map.has_key(perun_id):
            denbi_user = self.denbi_user_map[perun_id]

            if elixir_id == None:
                elixir_id=denbi_user['elixir_id']
            if email == None:
                email=denbi_user['email']
            if enabled == None:
                enabled = denbi_user['enabled']

            os_user = self.keystone.users.update(denbi_user['id'],\
                                                 name=str(elixir_id),\
                                                 email= str(email),\
                                                 enabled=enabled,\
                                                 deleted=deleted)

            denbi_user['elixir-id'] = os_user.name
            denbi_user['enabled'] = os_user.enabled
            denbi_user['deleted'] = os_user.deleted
            denbi_user['email'] = os_user.email

            self.denbi_user_map[denbi_user['perun_id']] = denbi_user # @ToDo not necessary ...

            return denbi_user
        else:
            raise ValueError('User with perun_id '+id+' not found in user_map')

    def users_map(self):
        """
        Return a  de.NBI user map {elixir-id -> denbi_user }
        :return: a denbi_user map {elixir-id : {id:string, elixir_id:string, perun_id:string, email:string, enabled: boolean}}
        """
        self.denbi_user_map = {}  # clear previous project list
        self.__user_id2perun_id__ = {}
        for os_user in self.keystone.users.list():
            #  beruecksichttige only correct flagged user
            # any other checks (like for name or perun_id are then not neccessary ...
            if hasattr(os_user,"flag") and os_user.flag == self.flag:

                denbi_user = {'id' : os_user.id,
                              'perun_id' : os_user.perun_id,
                              'elixir_id'  : os_user.name,
                              'enabled' : os_user.enabled,
                              'deleted' : os_user.deleted }
                # check for optional attribute email
                if hasattr(os_user,'email'):
                    denbi_user['email'] = os_user.email
                else:
                    denbi_user['email'] = None

                # create entry in maps
                self.denbi_user_map[os_user.perun_id] = denbi_user
                self.__user_id2perun_id__[os_user.id] = os_user.perun_id

        return self.denbi_user_map;

    def projects_create(self, perun_id, name = None, description = None, members = None, enabled=True):
        """
        Create a new project in the admins user default domain.
        :param perun_id: perun_id of the project
        :param name: name of the project (optional, if not set the perun_id will be used)
        :param description: description of this project (optional)
        :param members: list of user id, which are members of this project
        :param enabled : default True
        :return: a denbi_project  {id: string, perun_id : string, enabled : boolean, members: [denbi_users]}
        """

        if name == None:
            name = perun_id

        os_project = self.keystone.projects.create(name=str(name),\
                                                   perun_id=str(perun_id),\
                                                   domain=self.domain_id,\
                                                   description=str(description),\
                                                   enabled=enabled,\
                                                   scratched=False,\
                                                   flag=self.flag)
        denbi_project= {'id':os_project.id,
                        'name': os_project.name,
                        'perun_id': os_project.perun_id,
                        'description' :os_project.description,
                        'enabled' : os_project.enabled,
                        'scratched' : os_project.scratched,
                        'members' : [] }
        self.denbi_project_map[denbi_project['perun_id']] = denbi_project
        self.__project_id2perun_id__[denbi_project['id']] = denbi_project['perun_id']

        # if a list of  members is given append them to current project
        if members:
            for member in members:
                self.projects_append_user(perun_id,member)

        return denbi_project

    def project_quota(self,\
                      perun_id,\
                      number_of_vms=None,\
                      disk_space=None,\
                      special_purpose_hardware=None,\
                      ram_per_vm=None,\
                      object_storage=None):
        """
        Set/Update quota for project
        :param number_of_vms:
        :param disk_space: in GB
        :param special_purpose_hardware: supported values GPU, FPGA
        :param ram_per_vm: in GB
        :param object_storage: in GB
        :return:
        """
        if self.support_quotas:
            project = self.denbi_project_map[perun_id]
            raise NotImplementedError


    def projects_update(self,perun_id,members=None, name=None, description=None,enabled=None, scratched = False):
        """
        Update  a project
        :param perun_id: perun_id of the project to be modified
        :param members: list of perun user id
        :param name
        :param description
        :param enabled
        :param scratched - tagged for termination
        :return:
        """
        add = []
        rem = []

        project = self.denbi_project_map[perun_id]

        if (name != None or description != None or enabled != None or project['scratched'] != scratched ):
            if name == None:
                name = project['name']
            if description == None:
                description = project['description']
            if enabled == None:
                enabled = project['enabled']
            if scratched:
                enabled = False
            self.keystone.projects.update(project['id'],\
                                          name=name,\
                                          description=description,\
                                          enabled=enabled, \
                                          scratched=scratched)
            project['name'] = name
            project['description'] = description
            project['enabled'] = enabled
            project['scratched'] = scratched

        # update memberslist
        if members:
            # search for member to be removed or added
            for m in set(members) ^ set(project["members"]):
                # members to remove
                if m in project["members"]:
                    rem.append(m)
                else: # members to add
                    add.append(m)

            for m in rem:
                self.projects_remove_user(perun_id,m)

            for m in add:
                self.projects_append_user(perun_id,m)

    def projects_delete(self, perun_id):
        """
        Disable and tag project as deleted. Since it is dangerous to delete a project completly, the function just
        disable the project and tag it as deleted. To remove a project from keystone use the function projects_terminate.
        :param perun_id: perun_id of project to be deleted
        :return:
        """
        self.projects_update(perun_id,scratched=True)

    def projects_terminate(self, perun_id):
        """
        Terminate a tagged as deleted project. Raise an exception (ValueError) of invalid perun_id and termination
        of an untagged project.
        :param perun_id: perunid of project to be deleted
        :return:
        """
        if self.denbi_project_map.has_key(perun_id):
            # get project from map
            denbi_project = self.denbi_project_map[perun_id]

            if denbi_project['scratched']:
                # delete project by id in keystone database
                self.keystone.projects.delete(denbi_project['id'])
                # delete project from project map
                del(self.denbi_project_map[denbi_project['perun_id']])
            else:
                raise ValueError('Project with perun_id '+perun_id+' must be tagged as deleted before terminate!')
        else:
            raise ValueError('Project with perun_id '+perun_id+' not found in project_map!')

    def projects_map(self):
        """
        Return a map of projects
        :return: a map of denbi projects {perun_id: {id: string, perun_id : string, enabled : boolean, members: [denbi_users]}}
        """
        self.denbi_project_map = {}
        self.__project_id2perun_id__  = {}


        for os_project in self.keystone.projects.list(domain=self.domain_id):
            if hasattr(os_project,'flag') and os_project.flag == self.flag:
                denbi_project = {'id': os_project.id,
                                'name' : os_project.name,
                                'perun_id' : os_project.perun_id,
                                'description' : os_project.description,
                                'enabled' : os_project.enabled,
                                'scratched' : os_project.scratched,
                                'members' : [],
                                'quotas' : {} }
                # create entry in maps
                self.__project_id2perun_id__[denbi_project['id']] = denbi_project['perun_id']
                self.denbi_project_map[denbi_project['perun_id']] = denbi_project

        for role in self.keystone.role_assignments.list():
            tpid =  role.scope['project']['id']
            tuid = role.user['id']
            
            if self.__project_id2perun_id__.has_key(tpid) and self.__user_id2perun_id__.has_key(tuid):
                self.denbi_project_map[self.__project_id2perun_id__[tpid]]['members'].\
                    append(self.__user_id2perun_id__[tuid])

        # Check for project specific quota
        if self.support_quotas:
            raise NotImplementedError

        return self.denbi_project_map

    def projects_append_user(self, project_id, user_id):
        """
        Append an user to a project (grant default_role to user/project
        :param project_id: perun id of a project
        :param user_id: perun id of an user
        :return:
        """

        #check if project/user exists
        if not(self.denbi_project_map.has_key(project_id)):
            raise ValueError('A project with perun_id:'+str(project_id)+' does not exists!')

        if not(self.denbi_user_map.has_key(user_id)):
            raise ValueError('A user with perun_id: '+str(user_id)+' does not exists!')

        # get keystone id for user and project
        pid = self.denbi_project_map[project_id]['id']
        uid = self.denbi_user_map[user_id]['id']

        self.keystone.roles.grant(role=self.default_role_id,user=uid, project=pid)

        self.denbi_project_map[project_id]['members'].append(user_id)

    def projects_remove_user(self,project_id, user_id):
        """
        Remove an user from a project (revoke default_role from user/project)
        :param project_id: perun id of an project
        :param user_id: could be an openstack or perun id
        :return:
        """

        #check if project/user exists
        if not(self.denbi_project_map.has_key(project_id)):
            raise ValueError('A project with perun_id:'+project_id+' does not exists!')

        if not(self.denbi_user_map.has_key(user_id)):
            raise ValueError('A user with perun_id: '+user_id+' does not exists!')

        # get keystone id for user and project
        pid = self.denbi_project_map[project_id]['id']
        uid = self.denbi_user_map[user_id]['id']

        self.keystone.roles.revoke(role=self.default_role_id,user=uid,project=pid)

        self.denbi_project_map[project_id]['members'].remove(user_id)

    def projects_memberlist(self,perun_id):
        """
        Return a list of members
        :param perun_id: perun id of an project
        :return: Return a list of members
        """
        return self.denbi_project_map[perun_id]['members']