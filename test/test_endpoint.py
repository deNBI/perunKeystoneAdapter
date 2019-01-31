import os
import unittest

from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone

TESTDIR = os.path.dirname(os.path.realpath(__file__))


class TestEndpoint(unittest.TestCase):
    """
    Unit test for class endpoint.

    You need a full functional Openstack setup to make the test run properly.
    """

    def setUp(self):
        environ = {'OS_AUTH_URL': 'http://localhost:5000/v3/',
                   'OS_PROJECT_NAME': 'admin',
                   'OS_USER_DOMAIN_NAME': 'Default',
                   'OS_PROJECT_DOMAIN_NAME': 'Default',
                   'OS_USERNAME': 'admin',
                   'OS_PASSWORD': 's3cr3t'}

        self.keystone = KeyStone(environ, default_role="user", create_default_role=True, target_domain_name='elixir', cloud_admin=True)

    def _test_user(self, denbiuser, perun_id, elixir_id, email, enabled, deleted=False):
        self.assertEqual(denbiuser['perun_id'], perun_id)
        self.assertEqual(denbiuser['elixir_id'], elixir_id)
        if email is not None:
            self.assertEqual(denbiuser['email'], email)
        if deleted:
            self.assertEqual(denbiuser['enabled'], False)
            self.assertEqual(denbiuser['deleted'], True)
        else:
            self.assertEqual(denbiuser['enabled'], enabled)

    def _test_project(self, denbiproject, perun_id, members, enabled=True, deleted=False):
        self.assertEqual(denbiproject['perun_id'], perun_id)
        self.assertSetEqual(set(denbiproject['members']), set(members))
        if deleted:
            self.assertEqual(denbiproject['enabled'], False)
            self.assertEqual(denbiproject['scratched'], True)
        else:
            self.assertEqual(denbiproject['enabled'], enabled)

    def test_import_scim(self):

        # initialize endpoint  with 'scim' mode
        self.endpoint = Endpoint(keystone=self.keystone, mode="scim", support_quotas=False)

        # import 1st test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'scim', 'users.scim'),
                                  os.path.join(TESTDIR, 'resources', 'scim', 'groups.scim'))

        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()

        # check for "Jens Mustermann" with perun_id == "1"
        self.assertTrue("1" in after_import_users)
        self._test_user(after_import_users['1'], '1', 'd877b2f6-3b90-4483-89ce-91eab1bdba99@elixir-europe.org', 'jens.mustermann@test.de', True)

        # check for "Thomas Mueller" with perun_id == "2"
        self.assertTrue("2" in after_import_users)
        self._test_user(after_import_users['2'], '2', 'afec0f6d-acd4-4dff-939d-208bfc272512@elixir-europe.org', 'thomas@mueller.de', False)

        # check for "Paul Paranoid" with perun_id == "3"
        self.assertTrue("3" in after_import_users)
        self._test_user(after_import_users['3'], '3', 'b3d216a7-8696-451a-9cbf-b8d5e17a6ec2@elixir-europe.org', None, True)

        # check for "Test Project" with perun_id =="9845"
        self.assertTrue("9845" in after_import_projects)
        self._test_project(after_import_projects['9845'], '9845', ['1', '2', '3'])

        # check for "Sample Project" with perun_id == "9874"
        self.assertTrue("9874" in after_import_projects)
        self._test_project(after_import_projects['9874'], '9874', ['3'])

        # now import 2nd test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'scim', 'users_2nd.scim'),
                                  os.path.join(TESTDIR, 'resources', 'scim', 'groups_2nd.scim'))

        after_import_users_2 = self.keystone.users_map()
        after_import_projects_2 = self.keystone.projects_map()

        # user with perun_id == "1" not changed
        self.assertTrue("1" in after_import_users_2)
        self._test_user(after_import_users_2['1'], '1', 'd877b2f6-3b90-4483-89ce-91eab1bdba99@elixir-europe.org', 'jens.mustermann@test.de', True)

        # user with perun_id == "2" tagged as deleted
        self.assertTrue("2" in after_import_users_2)
        self._test_user(after_import_users_2['2'], '2', 'afec0f6d-acd4-4dff-939d-208bfc272512@elixir-europe.org', 'thomas@mueller.de', False, deleted=True)

        # user with perun_id == "3" disabled
        self.assertTrue("3" in after_import_users_2)
        self._test_user(after_import_users_2['3'], '3', 'b3d216a7-8696-451a-9cbf-b8d5e17a6ec2@elixir-europe.org', None, False)

        # user with perun_id == "4" added
        self.assertTrue("4" in after_import_users_2)
        self._test_user(after_import_users_2['4'], '4', 'bb01cabe-eae7-4e46-955f-b35db6e3d552@elixir-europe.org', None, True)

        # group with perun_id == "9845" not changed
        self.assertTrue("9845" in after_import_projects_2)
        self._test_project(after_import_projects_2['9845'], '9845', ['1', '3'])

        # group with perun_id == "9874" tagged as deleted
        self.assertTrue("9874" in after_import_projects_2)
        self._test_project(after_import_projects_2['9874'], '9874', ['3'], deleted=True)

        # group with perun_id == "9999" added
        self.assertTrue("9999" in after_import_projects_2)
        self._test_project(after_import_projects_2['9999'], '9999', ['1', '4'])

        # clean up everything
        ids = set(self.keystone.users_map())
        for perun_id in ids:
            self.keystone.users_delete(perun_id)
            self.keystone.users_terminate(perun_id)

        ids = set(self.keystone.projects_map())
        for perun_id in ids:
            self.keystone.projects_delete(perun_id)
            self.keystone.projects_terminate(perun_id)

    def test_import_denbi_portal_compute_center(self):
        # initialize endpoint  with 'scim' mode
        self.endpoint = Endpoint(keystone=self.keystone, mode="denbi_portal_compute_center", support_quotas=False)

        # import 1st test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'users.scim'),
                                  os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'groups.scim'))

        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()

        # user 1 - enabled
        self.assertTrue('50000' in after_import_users)
        self._test_user(after_import_users['50000'], '50000', 'd877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org', None, True)
        # user 2 - enabled
        self.assertTrue('50001' in after_import_users)
        self._test_user(after_import_users['50001'], '50001', 'b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org', None, True)
        # user 3 - enabled
        self.assertTrue('50002' in after_import_users)
        self._test_user(after_import_users['50002'], '50002', 'bb01cabe-eae7-4e46-955f-b35db6e3d552__@elixir-europe.org', None, True)
        # user 4 - enabled
        self.assertTrue('50003' in after_import_users)
        self._test_user(after_import_users['50003'], '50003', 'ce317030-288f-4712-9e5c-922539777c62__@elixir-europe.org', None, True)
        # user 5 - disabled
        self.assertTrue('50004' in after_import_users)
        self._test_user(after_import_users['50004'], '50004', '60420cf9-eb3e-45f4-8e1b-f8a2b317b042__@elixir-europe.org', None, False)

        # project 1
        self.assertTrue("9999" in after_import_projects)
        self._test_project(after_import_projects['9999'], '9999', ['50000', '50001', '50002'])

        # project 2
        self.assertTrue("10000" in after_import_projects)
        self._test_project(after_import_projects['10000'], '10000', ['50003'])

        # import 2nd test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'users_2nd.scim'),
                                  os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'groups_2nd.scim'))

        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()

        # user 1 - enabled
        self.assertTrue('50000' in after_import_users)
        self._test_user(after_import_users['50000'], '50000', 'd877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org', None, True)
        # user 2 - deleted
        self.assertTrue('50001' in after_import_users)
        self._test_user(after_import_users['50001'], '50001', 'b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org', None, True, deleted=True)
        # user 3 - enabled
        self.assertTrue('50002' in after_import_users)
        self._test_user(after_import_users['50002'], '50002', 'bb01cabe-eae7-4e46-955f-b35db6e3d552__@elixir-europe.org', None, True)
        # user 4 - enabled
        self.assertTrue('50003' in after_import_users)
        self._test_user(after_import_users['50003'], '50003', 'ce317030-288f-4712-9e5c-922539777c62__@elixir-europe.org', None, True)
        # user 5 - deleted
        self.assertTrue('50004' in after_import_users)
        self._test_user(after_import_users['50004'], '50004', '60420cf9-eb3e-45f4-8e1b-f8a2b317b042__@elixir-europe.org', None, False, deleted=True)

        # project 1
        self.assertTrue('9999' in after_import_projects)
        self._test_project(after_import_projects['9999'], '9999', ['50000', '50002'])

        # project 2 - deleted
        self.assertTrue('10000' in after_import_projects)
        self._test_project(after_import_projects['10000'], '10000', ['50003'], deleted=True)

        # project 3
        self.assertTrue('10001' in after_import_projects)
        self._test_project(after_import_projects['10001'], '10001', ['50003'])

        # clean up everything
        ids = set(self.keystone.users_map())
        for perun_id in ids:
            self.keystone.users_delete(perun_id)
            self.keystone.users_terminate(perun_id)

        ids = set(self.keystone.projects_map())
        for perun_id in ids:
            self.keystone.projects_delete(perun_id)
            self.keystone.projects_terminate(perun_id)
