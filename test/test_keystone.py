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

        print("Run 'test_project_quota'")

        perunid = self.__uuid()
        # id, which is not in the list for testing error
        perunid_without_list = self.__uuid()

        print(perunid)

        denbi_project = self.ks.projects_create(perunid)

        # sest ValueError if the project is not found in project_map
        self.assertRaises(ValueError, self.ks.project_quota, perunid_without_list)

        # receiving project quotas
        project_map_original = self.ks.projects_map()

        # call method project_quota without setting any quota
        self.ks.project_quota(perunid, number_of_vms=None, \
                              number_of_cpus=None, \
                              ram_per_vm=None, \
                              disk_space=None, \
                              volume_limit=None, \
                              number_of_snapshots=None, \
                              number_of_networks=None, \
                              number_of_subnets=None, \
                              number_of_router=None)

        # receiving project quotas
        project_map = self.ks.projects_map()

        # project quota should not have changed
        self.assertEqual(
            project_map_original[perunid]['quotas']['nova'].instances, project_map[perunid]['quotas']['nova'].instances,
            "project_quota with None changed number_of_vms")
        self.assertEqual(
            project_map_original[perunid]['quotas']['nova'].cores, project_map[perunid]['quotas']['nova'].cores,
            "project_quota with None changed number_of_cpus")
        self.assertEqual(
            project_map_original[perunid]['quotas']['nova'].ram, project_map[perunid]['quotas']['nova'].ram,
            "project_quota with None changed ram_per_vm")
        self.assertEqual(
            project_map_original[perunid]['quotas']['cinder'].gigabytes,
            project_map[perunid]['quotas']['cinder'].gigabytes,
            "project_quota with None changed  disc_space")
        self.assertEqual(
            project_map_original[perunid]['quotas']['cinder'].volumes, project_map[perunid]['quotas']['cinder'].volumes,
            "project_quota with None changed volume_limit")
        self.assertEqual(
            project_map_original[perunid]['quotas']['cinder'].snapshots,
            project_map[perunid]['quotas']['cinder'].snapshots,
            "project_quota with None changed snapshots")
        self.assertEqual(
            project_map_original[perunid]['quotas']['neutron']['quota']['network'],
            project_map[perunid]['quotas']['neutron']['quota']['network'],
            "project_quota with None changed number_of_networks")
        self.assertEqual(
            project_map_original[perunid]['quotas']['neutron']['quota']['subnet'],
            project_map[perunid]['quotas']['neutron']['quota']['subnet'],
            "project_quota with None changed number_of_subnets")
        self.assertEqual(
            project_map_original[perunid]['quotas']['neutron']['quota']['router'],
            project_map[perunid]['quotas']['neutron']['quota']['router'],
            "project_quota with None changed number_of_router")

        # call method project_quota with strings
        self.ks.project_quota(perunid, number_of_vms="11", \
                              number_of_cpus="9", \
                              ram_per_vm="11", \
                              disk_space="7", \
                              volume_limit="57", \
                              number_of_snapshots="21", \
                              number_of_networks="99", \
                              number_of_subnets="97", \
                              number_of_router="63")

        # receiving project quotas
        project_map = self.ks.projects_map()

        # project quotas should match the given numbers
        self.assertEqual(
            11, project_map[perunid]['quotas']['nova'].instances['limit'],
            "project_quota with string did not set number_of_vms")
        self.assertEqual(
            9, project_map[perunid]['quotas']['nova'].cores['limit'],
            "project_quota with string did not set number_of_cpus")
        self.assertEqual(
            11, project_map[perunid]['quotas']['nova'].ram['limit'],
            "project_quota with string did not set ram_per_vm")
        self.assertEqual(
            7, project_map[perunid]['quotas']['cinder'].gigabytes['limit'],
            "project_quota with string did not set disk_space")
        self.assertEqual(
            57, project_map[perunid]['quotas']['cinder'].volumes['limit'],
            "project_quota with string did not set volume_limit")
        self.assertEqual(
            21, project_map[perunid]['quotas']['cinder'].snapshots['limit'],
            "project_quota with string did not set snapshots")
        self.assertEqual(
            99, project_map[perunid]['quotas']['neutron']['quota']['network'],
            "project_quota with string did not set number_of_networks")
        self.assertEqual(
            97, project_map[perunid]['quotas']['neutron']['quota']['subnet'],
            "project_quota with string did not set number_of_subnets")
        self.assertEqual(
            63, project_map[perunid]['quotas']['neutron']['quota']['router'],
            "project_quota with string did not set number_of_routers")

        NUMBER_OF_VMS = project_map_original[perunid]['quotas']['nova'].instances['limit'] + 1
        RAM_PER_VM = project_map_original[perunid]['quotas']['nova'].ram['limit'] + 1
        NUMBER_OF_CPUS = project_map_original[perunid]['quotas']['nova'].cores['limit'] + 1
        DISK_SPACE = project_map_original[perunid]['quotas']['cinder'].gigabytes['limit'] + 1
        VOLUME_LIMIT = project_map_original[perunid]['quotas']['cinder'].volumes['limit'] + 1
        NUMBER_OF_SNAPSHOTS = project_map_original[perunid]['quotas']['cinder'].snapshots['limit'] + 1
        NUMBER_OF_NETWORKS = project_map_original[perunid]['quotas']['neutron']['quota']['network'] + 1
        NUMBER_OF_SUBNETS = project_map_original[perunid]['quotas']['neutron']['quota']['subnet'] + 1
        NUMBER_OF_ROUTER = project_map_original[perunid]['quotas']['neutron']['quota']['router'] + 1

        # call method project_quota with predefined values
        self.ks.project_quota(perunid, number_of_vms=NUMBER_OF_VMS, \
                              number_of_cpus=NUMBER_OF_CPUS,
                              ram_per_vm=RAM_PER_VM, \
                              disk_space=DISK_SPACE, \
                              volume_limit=VOLUME_LIMIT, \
                              number_of_snapshots=NUMBER_OF_SNAPSHOTS, \
                              number_of_networks=NUMBER_OF_NETWORKS,
                              number_of_subnets=NUMBER_OF_SUBNETS,
                              number_of_router=NUMBER_OF_ROUTER)

        # receiving project quotas
        project_map = self.ks.projects_map()

        # project quotas should match the predefined values
        self.assertEqual(
            NUMBER_OF_VMS, project_map[perunid]['quotas']['nova'].instances['limit'],
            "project_quota with valid value did not set number_of_vms")
        self.assertEqual(
            NUMBER_OF_CPUS, project_map[perunid]['quotas']['nova'].cores['limit'],
            "project_quota with valid value did not set number_of_cpus")
        self.assertEqual(
            RAM_PER_VM, project_map[perunid]['quotas']['nova'].ram['limit'],
            "project_quota with valid value did not set ram_per_vm")
        self.assertEqual(
            DISK_SPACE, project_map[perunid]['quotas']['cinder'].gigabytes['limit'],
            "project_quota with valid value did not set disk_space")
        self.assertEqual(
            VOLUME_LIMIT, project_map[perunid]['quotas']['cinder'].volumes['limit'],
            "project_quota with valid value did not set volume_limit")
        self.assertEqual(
            NUMBER_OF_SNAPSHOTS, project_map[perunid]['quotas']['cinder'].snapshots['limit'],
            "project_quota with valid value did not set snapshots")
        self.assertEqual(
            NUMBER_OF_NETWORKS, project_map[perunid]['quotas']['neutron']['quota']['network'],
            "project_quota with valid value did not set number_of_networks")
        self.assertEqual(
            NUMBER_OF_SUBNETS, project_map[perunid]['quotas']['neutron']['quota']['subnet'],
            "project_quota with valid value did not set number_of_subnets")
        self.assertEqual(
            NUMBER_OF_ROUTER, project_map[perunid]['quotas']['neutron']['quota']['router'],
            "project_quota with valid value did not set number_of_routers")

        # call method project_quota with negative values
        self.assertRaises(ValueError, self.ks.project_quota(perunid), number_of_vms=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), number_of_cpus=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), ram_per_vm=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), disk_space=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), volume_limit=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), number_of_snapshots=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), number_of_networks=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), number_of_subnets=-2)
        self.assertRaises(ValueError, self.ks.project_quota(perunid), number_of_router=-2)

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
