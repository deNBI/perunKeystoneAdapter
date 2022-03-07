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


import logging
import unittest
import uuid
import test

from denbi.perun.keystone import KeyStone

logging.basicConfig(level=logging.INFO)


class TestKeystone(unittest.TestCase):
    """Unit test for class Keystone.

    You need a full functional Openstack setup to make the test run properly.
    """

    def setUp(self):
        """Setup test environment.

        Lets keystone search for clouds.yml in ~/.config/openstack or /etc/openstack.
        See https://docs.openstack.org/python-openstackclient/pike/configuration/index.html for a description.
        """

        self.ks = KeyStone(environ=None, default_role="user", create_default_role=True, target_domain_name='elixir',
                           cloud_admin=True)

    def __uuid(self):
        return str(uuid.uuid4())

    def test_user_create_update_list_delete(self):
        """Test the methods users_create users_list and users_delete from KeyStone object.

        :return:
        """

        print("Run 'test_user_create_list_delete'")

        perun_id = self.__uuid()
        elixir_id = perun_id + "@elixir-europe.org"
        elixir_name = "juser"
        ssh_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIIBXwgYwPBMDEkSN5opn0mFu488iqtxJBgV5H3yctRi jkrueger@jkrueger-ThinkPad-T14s-Gen-1"
        email = elixir_name + "@no-mail.nix"

        # create a new user
        self.ks.users_create(elixir_id=elixir_id, perun_id=perun_id, elixir_name=elixir_name, ssh_key=None, email=email)

        # check internal user list
        denbi_user_map = self.ks.denbi_user_map
        self.assertTrue(perun_id in denbi_user_map,
                        f"User with perun id '{perun_id}' does not exists in local user map.")

        # ask keystone for a fresh user list
        denbi_user_map = self.ks.users_map()
        # user should also be provided to keystone
        self.assertTrue(perun_id in denbi_user_map, f"User with perun id '{perun_id}' does not exists.")

        test.test_user(self, denbi_user_map[perun_id],
                       perun_id=perun_id,
                       elixir_name=elixir_name,
                       elixir_id=elixir_id,
                       ssh_key=None,
                       email=email
                       )
        # update user
        self.ks.users_update(elixir_id=elixir_id, perun_id=perun_id, elixir_name=elixir_name, ssh_key=ssh_key,
                             email=email)

        # ask keystone for a fresh user list ...
        denbi_user_map = self.ks.users_map()

        # check updated data
        test.test_user(self, denbi_user_map[perun_id],
                       perun_id=perun_id,
                       elixir_name=elixir_name,
                       elixir_id=elixir_id,
                       ssh_key=ssh_key,
                       email=email
                       )

        # delete previous created user
        self.ks.users_delete(perun_id)

        # user should still exists but marked as deleted
        self.assertTrue(perun_id in denbi_user_map, f"User with perun id '{perun_id}' does not exists.")
        tmp = denbi_user_map[perun_id]
        self.assertTrue(tmp['deleted'], f"User with PerunID '{perun_id}' should marked as deleted.")

        # terminate user
        self.ks.users_terminate(perun_id)

        # check internal user list
        denbi_user_map = self.ks.denbi_user_map
        self.assertFalse(perun_id in denbi_user_map, f"User with perun id '{perun_id}' does exists in local user map.")
        # check keystone user list
        denbi_user_map = self.ks.users_map()
        self.assertFalse(perun_id in denbi_user_map, f"User with perun id '{perun_id}' does exists.")

    def test_project_create_list_delete(self):
        """Test the methods project_create, project_list and project_delete from KeyStone object.

        :return:
        """

        print("Run 'test_project_create_list_delete'")

        perunid = self.__uuid()

        denbi_project = self.ks.projects_create(perunid)

        # check internal project list
        denbi_project_map = self.ks.denbi_project_map
        self.assertTrue(perunid in denbi_project_map,
                        "Project with PerunId '" + perunid + "' does not exists in local project map.")

        # check keystone project list
        denbi_project_map = self.ks.projects_map()
        self.assertTrue(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does not exists.")

        # delete previous created project
        self.ks.projects_delete(perunid)

        # project should still exists but marked as deleted
        self.assertTrue(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does not exists.")
        tmp = denbi_project_map[perunid]
        self.assertTrue(tmp['scratched'],
                        "Project with PerunId '" + perunid + "' not marked as deleted (but should be).")

        # terminate previous marked project
        self.ks.projects_terminate(denbi_project['perun_id'])

        # check internal project list
        denbi_project_map = self.ks.denbi_project_map
        self.assertFalse(perunid in denbi_project_map,
                         "Project with PerunId '" + perunid + "' does exists in local project map.")

        # check keystone project list
        denbi_project_map = self.ks.projects_map()
        self.assertFalse(perunid in denbi_project_map, "Project with PerunId '" + perunid + "' does exists.")

    def test_project_set_and_get_quotas(self):
        """Test project_set and get_quotas.
        - setting project quotas using the method project_quota
        - get results to compare quotas with method projects_map from KeyStone object

        :return:
        """

        print("Run 'test_project_quota'")

        denbi_project = self.ks.projects_create(self.__uuid())

        # get quota_factory
        quota_mgr = self.ks.quota_factory.get_manager(denbi_project['id'])

        # set (non-deprecated) NOVA quotas
        quota_mgr.set_value('cores', 111)
        self.assertEqual(111, quota_mgr.get_current_quota('cores'))

        quota_mgr.set_value('instances', 33)
        self.assertEqual(33, quota_mgr.get_current_quota('instances'))

        quota_mgr.set_value('key_pairs', 34)
        self.assertEqual(34, quota_mgr.get_current_quota('key_pairs'))

        quota_mgr.set_value('metadata_items', 35)
        self.assertEqual(35, quota_mgr.get_current_quota('metadata_items'))

        quota_mgr.set_value('ram', 200000)
        self.assertEqual(200000, quota_mgr.get_current_quota('ram'))

        # set (non-deprecated) CINDER quotas
        quota_mgr.set_value('volumes', 36)
        self.assertEqual(36, quota_mgr.get_current_quota('volumes'))

        quota_mgr.set_value('snapshots', 37)
        self.assertEqual(37, quota_mgr.get_current_quota('snapshots'))

        quota_mgr.set_value('backups', 38)
        self.assertEqual(38, quota_mgr.get_current_quota('backups'))

        quota_mgr.set_value('groups', 39)
        self.assertEqual(39, quota_mgr.get_current_quota('groups'))

        quota_mgr.set_value('per_volume_gigabytes', 40)
        self.assertEqual(40, quota_mgr.get_current_quota('per_volume_gigabytes'))

        quota_mgr.set_value('gigabytes', 41)
        self.assertEqual(41, quota_mgr.get_current_quota('gigabytes'))

        quota_mgr.set_value('backup_gigabytes', 42)
        self.assertEqual(42, quota_mgr.get_current_quota('backup_gigabytes'))

        # set (non-deprecated) neutron quotas
        quota_mgr.set_value('floatingip', 43)
        self.assertEqual(43, quota_mgr.get_current_quota('floatingip'))

        quota_mgr.set_value('rbac_policy', 44)
        self.assertEqual(44, quota_mgr.get_current_quota('rbac_policy'))

        quota_mgr.set_value('subnet', 45)
        self.assertEqual(45, quota_mgr.get_current_quota('subnet'))

        quota_mgr.set_value('subnetpool', 46)
        self.assertEqual(46, quota_mgr.get_current_quota('subnetpool'))

        quota_mgr.set_value('security_group_rule', 47)
        self.assertEqual(47, quota_mgr.get_current_quota('security_group_rule'))

        quota_mgr.set_value('security_group', 48)
        self.assertEqual(48, quota_mgr.get_current_quota('security_group'))

        quota_mgr.set_value('port', 49)
        self.assertEqual(49, quota_mgr.get_current_quota('port'))

        quota_mgr.set_value('router', 50)
        self.assertEqual(50, quota_mgr.get_current_quota('router'))

        quota_mgr.set_value('network', 51)
        self.assertEqual(51, quota_mgr.get_current_quota('network'))

        # tag previous created project as deleted
        self.ks.projects_delete(denbi_project['perun_id'])

        # terminate previous marked project
        self.ks.projects_terminate(denbi_project['perun_id'])

    def test_all(self):
        """Test a typically scenario.
        - create two project (a, b)
        - create three users (a, b, c)
          - users (a,b) are members of project a
          - users abc are members of project b.
        - check the projects memberlist and clean up everything.

        :return:
        """
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
                             "Memberlist project_a contains [" + (", ".join(list)) + "] but expected [" + (
                                 ", ".join(expected_list)) + "]")

        list = project_b['members']
        expected_list = [user_a['perun_id'], user_b['perun_id'], user_c['perun_id']]

        self.assertListEqual(list, expected_list,
                             "Memberlist project_b contains [" + (", ".join(list)) + "] but expected [" + (
                                 ", ".join(expected_list)) + "]")

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
                         "Termination of users failed ... count " + str(len(user_map.keys())) + " but expect " + str(
                             count_users) + "!")

        # tag projects a, b for deletion
        self.ks.projects_delete(project_a['perun_id'])
        self.ks.projects_delete(project_b['perun_id'])

        # and terminate them
        self.ks.projects_terminate(project_a['perun_id'])
        self.ks.projects_terminate(project_b['perun_id'])

        # ask keystone for new project_map
        project_map = self.ks.projects_map()

        self.assertEqual(len(project_map.keys()), count_projects,
                         "Termination of projects failed ... count " + str(
                             len(project_map.keys())) + " but expect " + str(count_projects) + "!")


if __name__ == '__main__':
    unittest.main()
