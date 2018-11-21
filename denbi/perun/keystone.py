import os
import ast
import numbers
import logging
import itertools

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
from keystoneauth1.exceptions import Unauthorized
from novaclient import client as novaClient
from cinderclient import client as cinderClient
from neutronclient.v2_0 import client as neutronClient
from denbi.perun.quotas import manager as quotas

class KeyStone:
    """
    Keystone simplifies the communication with Openstack. Offers shortcuts for common functions and also
    simplifies data structures returned by Keystone and offers own data structure for denbi_user and denbi_project.

    Every user and every project generated by this class is marked with  perun propagation auto generated flag.

    denbi_user = ``{id: string, elixir_id: string, perun_id: string, email: string, enabled: boolean}``

    denbi_project = ``{id: string, perun_id: string, enabled: boolean, members: [denbi_user]}``
    """

    def __init__(self, environ=None, default_role="_member_",
                 create_default_role=False, flag="perun_propagation",
                 support_quotas=True, target_domain_name=None, read_only=False,
                 logging_domain='denbi', nested=False, cloud_admin=False):
        """
        Create a new Openstack Keystone session using the system environment.
        The following variables are considered:
        - OS_AUTH_URL
        - OS_USERNAME
        - OS_PASSWORD
        - OS_PROJECT_NAME
        - OS_USER_DOMAIN_NAME

        Instead of the system variables a "local" enviroment (a dict) can be explicitly set

        :param environ: local environ used instead of system environment
        :param default_role: default role used for all users (default is "_member_")
        :param create_default_role: create a default role if it not exists (default is False)
        :param flag: value used to mark users/projects (default is perun_propagation)
        :param support_quotas: support project quotas  (needs a complete openstack setup)
        :param target_domain_name: domain where all users & projects are created, will be created if it not exists
        :param read_only: do not make any changes to the keystone
        :param nested: use nested projects instead of cloud/domain admin accesss
        :param cloud_admin: credentials are cloud admin credentials

        """
        self.ro = read_only
        self.nested = nested
        self.logger = logging.getLogger(logging_domain)

        if cloud_admin:
            # working as cloud admin requires setting a target domain
            if target_domain_name is None:
                raise Exception("You need to set a target domain if working with cloud admin credentials.")
            # with cloud admin credentials we do not need multiple sessions
            auth = self._create_auth(environ, False)
            project_session = session.Session(auth=auth)
            domain_session = project_session
        else:
            # use two separate sessions for domain and project access
            domain_auth = self._create_auth(environ, True)
            project_auth = self._create_auth(environ, False)
            domain_session = session.Session(auth=domain_auth)
            project_session = session.Session(auth=project_auth)

        # we have both session, now check the credentials
        # by authenticating to keystone. we also need the AccessInfo
        # instances to retrieve project and domain ids for later


        try:
            domain_access = domain_auth.get_access(domain_session)
        except Unauthorized:
            raise Exception("Authorization for domain session failed, wrong credentials / role?")
        try:
            if domain_session is not project_session:
                project_access = project_auth.get_access(project_session)
            else:
                project_access = domain_access
        except Unauthorized:
            raise Exception("Authorization for project session failed, wrong credentials / role?")

        # store both session for later use
        self._domain_keystone = client.Client(session=domain_session)
        self._project_keystone = client.Client(session=project_session)

        # If support_quotas create instance of nova client
        if support_quotas:
            self.nova = novaClient.Client(2, session=project_session, endpoint_type="public")
            self.cinder = cinderClient.Client(2, session=project_session, endpoint_type="public")
            self.neutron = neutronClient.Client(session=project_session, endpoint_type="public")

        # override the domain name if necessary
        # we need to check that a correct value is given if a different
        # domain is used
        # TODO: the check might need to be improved if we need to differentiate
        #       between domain name syntax and uuid syntax
        if (target_domain_name
           and target_domain_name != domain_access.domain_name
           and target_domain_name != domain_access.domain_id):
            # valide the different domain name
            # the credentials should be cloud admin credentials in this case
            self.target_domain_id = self._resolve_domain(target_domain_name)
        else:
            if target_domain_name:
                self.logger.debug("Overridden domain name is same as project domain, ignoring value.")

            # use project domain
            self.target_domain_id = domain_access.domain_id

        self.logger.debug("Working on domain %s", self.target_domain_id)

        if nested:
            self.parent_project_id = project_access.project_id
            self.logger.debug("Using nested project %s (id %s)",
                              project_access.project_name,
                              self.parent_project_id)
        else:
            self.parent_project_id = None

        # Check if role exists ...
        self.default_role = str(default_role)
        self.default_role_id = None
        for role in self.domain_keystone.roles.list():
            if str(role.name) == self.default_role:
                self.default_role_id = str(role.id)
                break

        # create it if wished
        if not(self.default_role_id):
            if create_default_role:
                if not self.ro:
                    role = self.domain_keystone.roles.create(self.default_role)
                    self.default_role_id = str(role.id)
                    self.logger.debug('Created default role %s (id %s)', role.name, role.id)
                else:
                    self.default_role_id = 'read-only'
                    self.logger.debug('Read-only mode, not creating default role')
            else:
                raise Exception("Default role %s does not exists and should not be created!" % default_role)
        else:
            self.logger.debug('Using existing default role %s (id %s)', default_role, self.default_role_id)

        self.flag = flag

        self.support_quotas = support_quotas

        # initialize user and project map
        self.denbi_user_map = {}
        self.__user_id2perun_id__ = {}
        self.denbi_project_map = {}
        self.__project_id2perun_id__ = {}

        # initialize the quota factory
        self._quota_factory = quotas.QuotaFactory(project_session)

    @property
    def domain_keystone(self):
        return self._domain_keystone

    @property
    def project_keystone(self):
        return self._project_keystone

    @property
    def keystone(self, want_domain=True):
        if want_domain:
            return self.domain_keystone
        else:
            return self.project_keystone

    def _create_auth(self, environ, auth_at_domain=False):
        """
        Helper method to create the auth object for keystone, depending on the
        given environment.

        This method supports authentication via project scoped tokens for
        project and cloud admins, and domain scoped tokens for domain admins.
        The auth_at_domain flag indicates which kind of authentication is
        requested.

        In case of project scoped tokens, the user domain name is also used
        for the project if no separate project domain name is given.

        :param environ: dicts to take auth information from
        :param nested: enforce nested projects
        :param auth_at_domain: create domain scoped token

        :returns: the auth object to be used for contacting keystone
        """

        # default to shell environment if no specific one was given
        if environ is None:
            environ = os.environ
        if auth_at_domain:
            # create a domain scoped token
            auth = v3.Password(auth_url=environ['OS_AUTH_URL'],
                               username=environ['OS_USERNAME'],
                               password=environ['OS_PASSWORD'],
                               domain_name=environ['OS_DOMAIN_NAME'],
                               user_domain_name=environ['OS_USER_DOMAIN_NAME'])
        else:
            # create a project scoped token
            project_domain_name = environ['OS_PROJECT_DOMAIN_NAME'] if 'OS_PROJECT_DOMAIN_NAME' in environ else environ['OS_USER_DOMAIN_NAME']
            auth = v3.Password(auth_url=environ['OS_AUTH_URL'],
                               username=environ['OS_USERNAME'],
                               password=environ['OS_PASSWORD'],
                               project_name=environ['OS_PROJECT_NAME'],
                               user_domain_name=environ['OS_USER_DOMAIN_NAME'],
                               project_domain_name=project_domain_name)
        return auth

    def _resolve_domain(self, target_domain):
        """
        Helper method to check whether the given domain is accessible and
        to return the ID of that domain

        :param target_domain: name or id of the domain to check

        :returns: the keystone id of the given domain if the domain
                  is accessible
        """

        # start by enumerating all domains the current sessions have access to
        for domain in itertools.chain(self.domain_keystone.auth.domains(),
                                      self.project_keystone.auth.domains()):
            # compare domain to target and return id on match
            if (domain.id == target_domain or domain.name == target_domain):
                return domain.id
        # no matching domain found....
        raise Exception("Unknown or inaccessible domain %s" % target_domain)

    def users_create(self, elixir_id, perun_id, email=None, enabled=True):
        """
        Create a new user and updates internal user list

        :param elixir_id: elixir_id of the user to be created
        :param perun_id: perun_id of the user to be created
        :param email: email of the user to be created (optional, default is None)
        :param enabled: status of the user (optional, default is None)

        :return: a denbi_user hash {id:string, elixir_id:string, perun_id:string, email:string, enabled: boolean}
        """
        if not self.ro:
            os_user = self.keystone.users.create(name=str(elixir_id),  # str
                                                 domain=str(self.target_domain_id),  # str
                                                 email=str(email),  # str
                                                 perun_id=str(perun_id),  # str
                                                 enabled=enabled,  # bool
                                                 deleted=False,  # bool
                                                 flag=self.flag)  # str
            denbi_user = {'id': str(os_user.id),
                          'elixir_id': str(os_user.name),
                          'perun_id': str(os_user.perun_id),
                          'enabled': bool(os_user.enabled),
                          'deleted': False}

            if hasattr(os_user, 'email'):
                denbi_user['email'] = str(os_user.email)
            else:
                denbi_user['email'] = str(None)
        else:
            # Read-only
            denbi_user = {'id': 'read-only',
                          'elixir_id': 'read-only@elixir-europe.org',
                          'perun_id': perun_id,
                          'enabled': enabled,
                          'email': str(email),
                          'deleted': False}

        self.__user_id2perun_id__[denbi_user['id']] = denbi_user['perun_id']
        self.denbi_user_map[denbi_user['perun_id']] = denbi_user

        return denbi_user

    def users_delete(self, perun_id):
        """
        Disable the user and tag it as deleted. Since it is dangerous to delete a user completly, the delete function
        just disable the user and tag it as deleted. To remove an user completely use the function terminate.

        :param perun_id: perunid of user to be deleted

        :return:
        """
        self.users_update(perun_id, enabled=False, deleted=True)

    def users_terminate(self, perun_id):
        """
        Delete a user

        :param perun_id: perunid of user to be deleted

        :return:
        """
        perun_id = str(perun_id)
        if perun_id in self.denbi_user_map:
            denbi_user = self.denbi_user_map[perun_id]
            # delete user
            if not self.ro:
                self.keystone.users.delete(denbi_user['id'])
            # remove entry from map
            del(self.denbi_user_map[perun_id])
        else:
            raise ValueError('User with perun_id %s not found in user_map' % perun_id)

    def users_update(self, perun_id, elixir_id=None, email=None, enabled=None, deleted=False):
        """
        Update an existing user entry.


        :param elixir_id: elixir id
        :param email: email
        :param enabled: status

        :return: the modified denbi_user hash
        """
        perun_id = str(perun_id)
        if perun_id in self.denbi_user_map:
            denbi_user = self.denbi_user_map[perun_id]

            if elixir_id is None:
                elixir_id = denbi_user['elixir_id']
            if email is None:
                email = denbi_user['email']
            if enabled is None:
                enabled = denbi_user['enabled']

            if not self.ro:
                os_user = self.keystone.users.update(denbi_user['id'],  # str
                                                     name=str(elixir_id),  # str
                                                     email=str(email),  # str
                                                     enabled=bool(enabled),  # bool
                                                     deleted=bool(deleted))  # bool

                denbi_user['elixir-id'] = str(os_user.name)
                denbi_user['enabled'] = bool(os_user.enabled)
                denbi_user['deleted'] = bool(os_user.deleted)
                denbi_user['email'] = str(os_user.email)

            self.denbi_user_map[denbi_user['perun_id']] = denbi_user

            return denbi_user
        else:
            raise ValueError('User with perun_id %s not found in user_map' % perun_id)

    def users_map(self):
        """
        Return a  de.NBI user map {elixir-id -> denbi_user }

        :return: a denbi_user map ``{elixir-id: {id:string, elixir_id:string, perun_id:string, email:string, enabled: boolean}}``
        """
        self.denbi_user_map = {}  # clear previous project list
        self.__user_id2perun_id__ = {}
        for os_user in self.keystone.users.list(domain=self.target_domain_id):
            # consider only correct flagged user
            # any other checks (like for name or perun_id are then not neccessary ...
            if hasattr(os_user, "flag") and str(os_user.flag) == self.flag:
                if not hasattr(os_user, 'perun_id'):
                    raise Exception("User ID %s should have perun_id" % (os_user.id, ))

                denbi_user = {'id': str(os_user.id),  # str
                              'perun_id': str(os_user.perun_id),  # str
                              'elixir_id': str(os_user.name),  # str
                              'enabled': bool(os_user.enabled),  # boolean
                              # TODO(hxr): prod did not have os_user.deleted, why?
                              'deleted': bool(getattr(os_user, 'deleted', False))}  # boolean
                # check for optional attribute email
                if hasattr(os_user, 'email'):
                    denbi_user['email'] = str(os_user.email)  # str
                else:
                    denbi_user['email'] = str(None)  # str

                # create entry in maps
                self.denbi_user_map[denbi_user['perun_id']] = denbi_user
                self.__user_id2perun_id__[denbi_user['id']] = denbi_user['perun_id']

        return self.denbi_user_map

    def projects_create(self, perun_id, name=None, description=None, members=None, enabled=True):
        """
        Create a new project in the admins user default domain.

        :param perun_id: perun_id of the project
        :param name: name of the project (optional, if not set the perun_id will be used)
        :param description: description of this project (optional)
        :param members: list of user id, which are members of this project
        :param enabled: default True

        :return: a denbi_project  {id: string, perun_id: string, enabled: boolean, members: [denbi_users]}
        """

        perun_id = str(perun_id)
        if name is None:
            name = perun_id

        if not self.ro:
            os_project = self.keystone.projects.create(name=str(name),
                                                       perun_id=perun_id,
                                                       domain=self.target_domain_id,
                                                       description=description,
                                                       enabled=bool(enabled),
                                                       scratched=False,
                                                       flag=self.flag,
                                                       parent=self.parent_project_id if self.nested else None)
            denbi_project = {'id': str(os_project.id),
                             'name': str(os_project.name),
                             'perun_id': str(os_project.perun_id),
                             'description': os_project.description,
                             'enabled': bool(os_project.enabled),
                             'scratched': bool(os_project.scratched),
                             'members': []}
        else:
            denbi_project = {'id': 'read-only-fake',
                             'name': name,
                             'perun_id': perun_id,
                             'description': description,
                             'enabled': enabled,
                             'scratched': False,
                             'members': []}

        self.denbi_project_map[denbi_project['perun_id']] = denbi_project
        self.__project_id2perun_id__[denbi_project['id']] = denbi_project['perun_id']

        # if a list of  members is given append them to current project
        if members:
            for member in members:
                self.projects_append_user(perun_id, member)

        return denbi_project

    def project_quota(self,
                      perun_id,
                      number_of_vms=None,
                      disk_space=None,
                      special_purpose_hardware=None,
                      ram_per_vm=None,
                      object_storage=None,
                      number_of_cpus=None,
                      number_of_snapshots=None,
                      volume_limit=None,
                      number_of_networks=None,
                      number_of_subnets=None,
                      number_of_router=None):
        """
        Set/Update quota for project

        :param number_of_vms:
        :param disk_space: in GB
        :param special_purpose_hardware: supported values GPU, FPGA
        :param ram_per_vm: in GB
        :param object_storage: in GB
        :param number_of_cpus:
        :param number_of_snapshots:
        :param volume_limit:
        :param number_of_networks:
        :param number_of_subnets:
        :param number_of_router:
        :return:
        """

        perun_id = str(perun_id)

        if self.support_quotas:
            if perun_id in self.denbi_project_map:
                # get project from map
                project = self.denbi_project_map[perun_id]

                # check quota usage (nova quotas)
                vms_in_use = project['quotas']['nova'].instances['in_use']
                cpus_in_use = project['quotas']['nova'].cores['in_use']
                ram_in_use = project['quotas']['nova'].ram['in_use']

                # check quota usage (cinder quotas)
                disk_in_use = project['quotas']['cinder'].gigabytes['in_use']
                volumes_in_use = project['quotas']['cinder'].volumes['in_use']
                snapshots_in_use = project['quotas']['cinder'].snapshots['in_use']

                # check quota usage (neutron quotas)
                networks_in_use = project['quotas']['neutron']['quota']['networks_in_use']
                subnetworks_in_use = project['quotas']['neutron']['quota']['subnetworks_in_use']
                routers_in_use = project['quotas']['neutron']['quota']['routers_in_use']

                self._set_quota(self.nova.quotas, project['id'], 'instances',
                                number_of_vms, vms_in_use)
                self._set_quota(self.nova.quotas, project['id'], 'cores',
                                number_of_cpus, cpus_in_use)
                # TODO: ram_per_vm is wrong name for that value....
                self._set_quota(self.nova.quotas, project['id'], 'ram',
                                ram_per_vm, ram_in_use)
                self._set_quota(self.cinder.quotas, project['id'], 'gigabytes',
                                disk_space, disk_in_use)
                self._set_quota(self.cinder.quotas, project['id'], 'snapshots',
                                number_of_snapshots, snapshots_in_use)
                self._set_quota(self.cinder.quotas, project['id'], 'volumes',
                                volume_limit, volumes_in_use)
                self._set_quota(self.neutron, project['id'], 'network',
                                number_of_networks, networks_in_use,
                                use_body=True)
                self._set_quota(self.neutron, project['id'], 'subnet',
                                number_of_subnets, subnetworks_in_use,
                                use_body=True)
                self._set_quota(self.neutron, project['id'], 'router',
                                number_of_router, routers_in_use,
                                use_body=True)
            else:
                raise ValueError('Project with perun_id ' + perun_id + ' not found in project_map!')

    def _set_quota(self, handler, project_id, name, current_value, new_value,
                   use_body=False):
        """
        Sets a new quota for the project

        :param handler: quota handling instance, e.g. a novaclient object
        :param project_id: project to set the quota for
        :param name: name of the quota field, e.g. 'router' or 'volumes'
        :param current_value: current value of quota (if available, none else),
                              or amount of resources actually in use
        :param new_value: new value for quota
        :param use_body: set quota via body dict, e.g. for neutron quotas

        Checks that the new quota is sane (larger or equal than current value),
        and invokes the update_quota method on the handler with the correct
        parameters.
        """

        # converts new value to integer if given as a string
        if type(new_value) is str:
            new_value = self.convert_str_to_int(new_value)
            # check new value and set it if it is sane
            if self.test_new_number(new_value, current_value):
                if use_body:
                    handler.update_quota(project_id, body={'quota': {name: new_value}})
                else:
                    # TODO: novaclient 2.57 introduces a new method with
                    #       explicit parameter names. Can we convert this?
                    handler.update(project_id, {name: new_value})
            elif new_value is not None:
                raise ValueError(new_value + ' is lower than used or current value for '+name+' or -1!')

    def test_new_number(self, new_number, in_use):
        """
        Tests if given number is valid
        :param new_number: given number
        :param in_use: amount of used quota
        :return: True if given number is valid
        """
        if new_number is not None:
            if isinstance(new_number, numbers.Integral):
                return (in_use <= new_number > -2) or new_number == -1
            else:
                raise ValueError(new_number + ' should be an Integer!')
        else:
            return False

    def convert_str_to_int(self, value):
        """
        Converts string to int
        necessary for the following method test_new_number,
        :param value: given string
        :return: converted integer
        """
        return ast.literal_eval(value)

    def projects_update(self, perun_id, members=None, name=None,
                        description=None, enabled=None, scratched=False):
        """
        Update  a project

        :param perun_id: perun_id of the project to be modified
        :param members: list of perun user id
        :param name:
        :param description:
        :param enabled:
        :param scratched: - tagged for termination

        :return:
        """
        perun_id = str(perun_id)
        add = []
        rem = []

        project = self.denbi_project_map[perun_id]

        # TODO(hxr): removed enabled is none due to update having blank enabled
        if (name is not None or description is not None or enabled is not None or project['scratched'] != scratched):
            if name is None:
                name = project['name']
            if description is None:
                description = project['description']
            if enabled is None:
                enabled = project['enabled']
            if scratched:
                enabled = False

            if not self.ro:
                self.keystone.projects.update(project['id'],
                                              name=str(name),
                                              description=description,
                                              enabled=bool(enabled),
                                              scratched=bool(scratched))
            project['name'] = str(name)
            project['description'] = description
            project['enabled'] = bool(enabled)
            project['scratched'] = bool(scratched)

        # update memberslist
        if members:
            # search for member to be removed or added
            for m in set(members) ^ set(project["members"]):
                if m in project["members"]:
                    # members to remove
                    rem.append(m)
                else:
                    # members to add
                    add.append(m)

            for m in rem:
                self.projects_remove_user(perun_id, m)

            for m in add:
                self.projects_append_user(perun_id, m)

    def projects_delete(self, perun_id):
        """
        Disable and tag project as deleted. Since it is dangerous to delete a project completly, the function just
        disable the project and tag it as deleted. To remove a project from keystone use the function projects_terminate.

        :param perun_id: perun_id of project to be deleted
        :return:
        """
        self.projects_update(perun_id, scratched=True)
        # TODO(hxr): implement real-delete mode?
        # project = self.denbi_project_map[perun_id]
        # print('deleting', project['id'])

    def projects_terminate(self, perun_id):
        """
        Terminate a tagged as deleted project. Raise an exception (ValueError) of invalid perun_id and termination
        of an untagged project.

        :param perun_id: perunid of project to be deleted

        :return:
        """
        perun_id = str(perun_id)
        if perun_id in self.denbi_project_map:
            # get project from map
            denbi_project = self.denbi_project_map[perun_id]

            if denbi_project['scratched']:
                # delete project by id in keystone database
                if not self.ro:
                    self.keystone.projects.delete(denbi_project['id'])
                # delete project from project map
                del(self.denbi_project_map[denbi_project['perun_id']])
            else:
                raise ValueError('Project with perun_id %s must be tagged as deleted before terminate!' % perun_id)
        else:
            raise ValueError('Project with perun_id %s not found in project_map!' % perun_id)

    def projects_map(self):
        """
        Return a map of projects

        :return: a map of denbi projects ``{perun_id: {id: string, perun_id: string, enabled: boolean, members: [denbi_users]}}``
        """
        self.denbi_project_map = {}
        self.__project_id2perun_id_ = {}

        for os_project in self.keystone.projects.list(domain=self.target_domain_id):
            if hasattr(os_project, 'flag') and os_project.flag == self.flag:
                self.logger.debug('Found denbi associated project %s (id %s)',
                                  os_project.name, os_project.id)
                denbi_project = {
                    'id': str(os_project.id),  # str
                    'name': str(os_project.name),  # str
                    'perun_id': str(os_project.perun_id),  # str
                    'description': os_project.description,  #
                    'enabled': bool(os_project.enabled),  # bool
                    'scratched': bool(os_project.scratched),  # bool
                    'members': [],
                    'quotas': {}
                }
                # create entry in maps
                self.__project_id2perun_id__[denbi_project['id']] = denbi_project['perun_id']
                self.denbi_project_map[denbi_project['perun_id']] = denbi_project

                # get all assigned roles for this project
                # this call should be possible with domain admin right
                # include_subtree is necessary since the default policies either
                # allow domain role assignment querie
                for role in self.keystone.role_assignments.list(project=os_project.id, include_subtree=True):
                    if role.user['id'] in self.__user_id2perun_id__:
                        self.logger.debug('Found user %s as member in project %s', role.user['id'], os_project.name)
                        denbi_project['members'].append(self.__user_id2perun_id__[role.user['id']])

        # Check for project specific quota
        if self.support_quotas:
            for perun_id in self.denbi_project_map:
                project_id = self.denbi_project_map[perun_id]['id']
                # Get Quotas (nova and cinder with number of used)
                self.denbi_project_map[perun_id]['quotas']['nova'] = self.nova.quotas.get(tenant_id=project_id, user_id=None, detail=True)
                self.denbi_project_map[perun_id]['quotas']['cinder'] = self.cinder.quotas.get(tenant_id=project_id, usage=True)
                self.denbi_project_map[perun_id]['quotas']['neutron'] = self.neutron.show_quota(project_id)

                # Count number of networks, subnets and routers to find number of used quotas
                netw_list = self.neutron.list_networks()
                subnet_list = self.neutron.list_subnets()
                router_list = self.neutron.list_routers(retrieve_all=True)
                netwcount = netw_list['networks']
                subnetcount = subnet_list['subnets']
                routercount = router_list['routers']
                self.denbi_project_map[perun_id]['quotas']['neutron']['quota']['networks_in_use'] = len(netwcount)
                self.denbi_project_map[perun_id]['quotas']['neutron']['quota']['subnetworks_in_use'] = len(subnetcount)
                self.denbi_project_map[perun_id]['quotas']['neutron']['quota']['routers_in_use'] = len(routercount)

                self.logger.debug("Got quotas for project %s: %s",
                                  project_id,
                                  self.denbi_project_map[perun_id]['quotas'])

        return self.denbi_project_map

    def projects_append_user(self, project_id, user_id):
        """
        Append an user to a project (grant default_role to user/project

        :param project_id: perun id of a project
        :param user_id: perun id of an user
        :return:
        """

        project_id = str(project_id)
        user_id = str(user_id)

        # check if project/user exists
        if not(project_id in self.denbi_project_map):
            raise ValueError('A project with perun_id: %s does not exists!' % project_id)

        if not(user_id in self.denbi_user_map):
            raise ValueError('A user with perun_id: %s does not exists!' % user_id)

        # get keystone id for user and project
        pid = self.denbi_project_map[project_id]['id']
        uid = self.denbi_user_map[user_id]['id']

        if not self.ro:
            self.keystone.roles.grant(role=self.default_role_id, user=uid, project=pid)

        self.denbi_project_map[project_id]['members'].append(user_id)

    def projects_remove_user(self, project_id, user_id):
        """
        Remove an user from a project (revoke default_role from user/project)

        :param project_id: perun id of an project
        :param user_id: could be an openstack or perun id

        :return:
        """

        project_id = str(project_id)
        user_id = str(user_id)
        # check if project/user exists
        if not(project_id in self.denbi_project_map):
            raise ValueError('A project with perun_id: %s does not exists!' % project_id)

        if not(user_id in self.denbi_user_map):
            raise ValueError('A user with perun_id: %s does not exists!' % user_id)

        # get keystone id for user and project
        pid = self.denbi_project_map[project_id]['id']
        uid = self.denbi_user_map[user_id]['id']

        if not self.ro:
            self.keystone.roles.revoke(role=self.default_role_id, user=uid, project=pid)

        self.denbi_project_map[project_id]['members'].remove(user_id)

    def projects_memberlist(self, perun_id):
        """
        Return a list of members

        :param perun_id: perun id of an project

        :return: Return a list of members
        """
        return self.denbi_project_map[perun_id]['members']
