import unittest
import uuid
import logging  # NOQA

from denbi.perun.keystone import KeyStone

# If you want detailed logs of what is going on, uncomment this.
# logging.basicConfig(level=logging.INFO)


class TestKeystone(unittest.TestCase):
    """
        Unit test for class Keystone

        Attention: The unit test does currently not support project quotas test.
        The used monasca/keystone container for test  purposes has only support
        for keystone, but not for nova (compute resources), neutron (network resources)
        or  glance (image resources)

    """

    def setUp(self):
        environ = {'OS_AUTH_URL': 'http://localhost:5000/v3/',
                   'OS_PROJECT_NAME': 'admin',
                   'OS_USER_DOMAIN_NAME': 'Default',
                   'OS_USERNAME': 'admin',
                   'OS_PASSWORD': 's3cr3t'}

        self.ks = KeyStone(environ,default_role="user",create_default_role=True,support_quotas=True,target_domain_name='elixir')

    def __uuid(self):
        return str(uuid.uuid4())

    def test_user_create_list_delete(self):
        '''
        Test the methods users_create users_list and users_delete from KeyStone object.
        :return:
        '''

        print("Run 'test_user_create_list_delete'")

        perunid = self.__uuid()
        elixirid = perunid + "@elixir-europe.org"

        # create a new user
        denbi_user = self.ks.users_create(elixirid, perunid)

        # check internal user list
        denbi_user_map = self.ks.denbi_user_map
        self.assertTrue(perunid in denbi_user_map, "User with PerunId '" + perunid + "' does not exists in local user map.")

        # ask keystone for a fresh user list
        denbi_user_map = self.ks.users_map()
        # user should also be provided to keystone
        self.assertTrue(perunid in denbi_user_map, "User with PerunId does not exists.")

        # delete previous created user
        self.ks.users_delete(denbi_user['perun_id'])

        # user should still exists but marked as deleted
        self.assertTrue(perunid in denbi_user_map, "User with PerunId does not exists.")
        tmp = denbi_user_map[perunid]
        self.assertTrue(tmp['deleted'], "User with PerunID '" + perunid + "' should marked as deleted.")

        # terminate user
        self.ks.users_terminate(denbi_user['perun_id'])

        # check internal user list
        denbi_user_map = self.ks.denbi_user_map
        self.assertFalse(perunid in denbi_user_map, "User with PerunId '" + perunid + "' does exists in local user map.")
        # check keystone user list
        denbi_user_map = self.ks.users_map()
        self.assertFalse(perunid in denbi_user_map, "User with PerunId does exists.")

    def test_project_create_list_delete(self):
        '''
        Test the methods project_create, project_list and project_delete from KeyStone object.
        :return:
        '''

        print("Run 'test_project_create_list_delete'")

        perunid = self.__uuid()

        denbi_project = self.ks.projects_create(perunid)

        # check internal project list
        denbi_project_map = self.ks.denbi_project_map
        self.assertTrue(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does not exists in local project map.")

        # check keystone project list
        denbi_project_map = self.ks.projects_map()
        self.assertTrue(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does not exists.")

        # delete previous created project
        self.ks.projects_delete(perunid)

        # project should still exists but marked as deleted
        self.assertTrue(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does not exists.")
        tmp = denbi_project_map[perunid]
        self.assertTrue(tmp['scratched'], "Project with PerunId '" + perunid + "' not marked as deleted (but should be).")

        # terminate previous marked project
        self.ks.projects_terminate(denbi_project['perun_id'])

        # check internal project list
        denbi_project_map = self.ks.denbi_project_map
        self.assertFalse(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does exists in local project map.")

        # check keystone project list
        denbi_project_map = self.ks.projects_map()
        self.assertFalse(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does exists.")

    def test_project_set_and_get_quotas(self):
        '''
        Test setting project quotas using the method project_quota and get results to compare quotas with method
        projects_map from KeyStone object.
        :return:
        '''
        # TODO: write error messages
        # TODO: test to be included quotas

        print("Run 'test_project_quota'")

        perunid = self.__uuid()

        denbi_project = self.ks.projects_create(perunid)

        # TODO: test ValueError if the project is not found in project_map

        # TODO: test if the value matches the expected type

        # receiving project quotas
        project_map_original = self.ks.projects_map()

        # call method project_quota without setting any quota
        self.ks.project_quota(perunid, number_of_vms=None, \
                              disk_space=None, \
                              special_purpose_hardware=None, \
                              ram_per_vm=None, \
                              object_storage=None,
                              number_of_cpus=None)

        # receiving project quotas
        project_map = self.ks.projects_map()

        # project quota should not have changed
        self.assertEqual(project_map_original[perunid]['quotas']['nova'].instances,
                         project_map[perunid]['quotas']['nova'].instances, "Message")

        # call method project_quota with negative values
        # TODO: test all quotas with negative values
        self.ks.project_quota(perunid, number_of_vms=-1, \
                              disk_space=-1, \
                              special_purpose_hardware=None, \
                              ram_per_vm=-1, \
                              object_storage=None,
                              number_of_cpus=-1)

        # receiving project quotas
        project_map = self.ks.projects_map()

        # project quota should not have changed
        self.assertEqual(project_map_original[perunid]['quotas']['nova'].instances,
                         project_map[perunid]['quotas']['nova'].instances, "Message")

        NUMBER_OF_VMS = project_map_original[perunid]['quotas']['nova'].instances + 1
        RAM_PER_VM = project_map_original[perunid]['quotas']['nova'].ram + 1
        NUMBER_OF_CPUS = project_map_original[perunid]['quotas']['nova'].cores + 1
        DISK_SPACE = project_map_original[perunid]['quotas']['cinder'].gigabytes + 1

        # call method project_quota with predefined values
        # TODO: test all quotas with predefined values
        self.ks.project_quota(perunid, number_of_vms=NUMBER_OF_VMS, \
                      disk_space=DISK_SPACE, \
                      special_purpose_hardware=None, \
                      ram_per_vm=RAM_PER_VM, \
                      object_storage=None,
                      number_of_cpus=NUMBER_OF_CPUS)

        # receiving project quotas
        project_map = self.ks.projects_map()

        # project quotas should match the predefined values
        self.assertEqual(NUMBER_OF_VMS, project_map[perunid]['quotas']['nova'].instances, "Message")
        self.assertEqual(DISK_SPACE, project_map[perunid]['quotas']['cinder'].gigabytes, "Message")
        self.assertEqual(RAM_PER_VM, project_map[perunid]['quotas']['nova'].ram, "Message")
        self.assertEqual(NUMBER_OF_CPUS, project_map[perunid]['quotas']['nova'].cores, "Message")

        # delete previous created project
        self.ks.projects_delete(perunid)

        # terminate previous marked project
        self.ks.projects_terminate(denbi_project['perun_id'])

    def test_all(self):
        '''
        Test a typically scenario, create two project (a, b), create two users (a, b, c), users ab are members of project a,
        and users abc are members of project b. Check the projects memberlist and clean up everything.

        :return:
        '''

        print("Run 'test_all'")

        count_projects = len(self.ks.projects_map().keys())
        count_users = len(self.ks.users_map().keys())

        # create two projects
        project_a = self.ks.projects_create(self.__uuid())
        project_b = self.ks.projects_create(self.__uuid())

        # create three user
        id = self.__uuid()
        user_a = self.ks.users_create(id, id + "@elixir-europe.org")
        id = self.__uuid()
        user_b = self.ks.users_create(id, id + "@elixir-europe.org")
        id = self.__uuid()
        user_c = self.ks.users_create(id, id + "@elixir-europe.org")

        # append user a, b to project a
        self.ks.projects_append_user(project_a['perun_id'], user_a['perun_id'])
        self.ks.projects_append_user(project_a['perun_id'], user_b['perun_id'])

        # append user a, b, c to project b
        self.ks.projects_append_user(project_b['perun_id'], user_a['perun_id'])
        self.ks.projects_append_user(project_b['perun_id'], user_b['perun_id'])
        self.ks.projects_append_user(project_b['perun_id'], user_c['perun_id'])

        projects = self.ks.denbi_project_map

        # Some tests if everything is stored in our project map
        self.assertEqual(projects[project_a['perun_id']], project_a)
        self.assertEqual(projects[project_b['perun_id']], project_b)

        list = project_a['members']
        expected_list = [user_a['perun_id'], user_b['perun_id']]
        self.assertListEqual(list, expected_list,
                             "Memberlist project_a contains [" + (", ".join(list)) + "] but expected [" + (", ".join(expected_list)) + "]")

        list = project_b['members']
        expected_list = [user_a['perun_id'], user_b['perun_id'], user_c['perun_id']]

        self.assertListEqual(list, expected_list,
                             "Memberlist project_b contains [" + (", ".join(list)) + "] but expected [" + (", ".join(expected_list)) + "]")

        # try to add an user that does not exists
        try:
            self.ks.projects_append_user(project_b['perun_id'], '0815')
            self.assertFalse(True)
        except Exception:
            pass

        # try to remove an user that does not exists
        try:
            self.ks.projects_remove_user(project_a['perun_id'], "0815")
            self.assertFalse(True)
        except Exception:
            pass

        # remove user a, b from project_a
        self.ks.projects_remove_user(project_a['perun_id'], user_a['perun_id'])
        self.ks.projects_remove_user(project_a['perun_id'], user_b['perun_id'])

        # remove user a, b, c from project b
        self.ks.projects_remove_user(project_b['perun_id'], user_a['perun_id'])
        self.ks.projects_remove_user(project_b['perun_id'], user_b['perun_id'])
        self.ks.projects_remove_user(project_b['perun_id'], user_c['perun_id'])

        self.assertEqual(len(project_a['members']), 0)
        self.assertEqual(len(project_b['members']), 0)

        # tag user a, b, c for deletion
        self.ks.users_delete(user_a['perun_id'])
        self.ks.users_delete(user_b['perun_id'])
        self.ks.users_delete(user_c['perun_id'])

        # and terminate them
        self.ks.users_terminate(user_a['perun_id'])
        self.ks.users_terminate(user_b['perun_id'])
        self.ks.users_terminate(user_c['perun_id'])

        # ask keystone for new user map
        user_map = self.ks.users_map()

        self.assertEqual(len(user_map.keys()), count_users,
                         "Termination of users failed ... count " + str(len(user_map.keys())) + " but expect " + str(count_users) + "!")

        # tag projects a, b for deletion
        self.ks.projects_delete(project_a['perun_id'])
        self.ks.projects_delete(project_b['perun_id'])

        # and terminate them
        self.ks.projects_terminate(project_a['perun_id'])
        self.ks.projects_terminate(project_b['perun_id'])

        # ask keystone for new project_map
        project_map = self.ks.projects_map()

        self.assertEqual(len(project_map.keys()), count_projects,
                         "Termination of projects failed ... count " + str(len(project_map.keys())) + " but expect " + str(count_projects) + "!")


if __name__ == '__main__':
    unittest.main()
