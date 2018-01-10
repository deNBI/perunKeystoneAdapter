import unittest

from denbi.bielefeld.perun.endpoint import Endpoint
from denbi.bielefeld.perun.keystone import KeyStone

class TestEndpoint(unittest.TestCase):
    """
    Unit test for class endpoint.

    Perquisites : Running monasca/keystone with default credentials for admin user.

    Start the container:
    $ docker run -d -p 5000:5000 -p 35357:35357 monasca/keystone

    see test/keystone/README.md for a more detailed

    """


    def setUp(self):
        environ = {'OS_AUTH_URL':'http://localhost:5000/v3/',
                   'OS_PROJECT_NAME':'admin',
                   'OS_USER_DOMAIN_NAME':'Default',
                   'OS_USERNAME':'admin',
                   'OS_PASSWORD':'s3cr3t'}

        self.keystone = KeyStone(environ,default_role="user",create_default_role=True, support_quotas= False)


    def _test_user(self, denbiuser, perun_id, elixir_id,email, enabled):
        self.assertEquals(denbiuser['perun_id'],perun_id)
        self.assertEquals(denbiuser['elixir_id'], elixir_id)
        if email != None:
            self.assertEquals(denbiuser['email'],email)
        self.assertEquals(denbiuser['enabled'],enabled)

    def _test_project(self,denbiproject, perun_id, members):
        self.assertEquals(denbiproject['perun_id'],perun_id)
        self.assertSetEqual(set(denbiproject['members']),set(members))

    def test_import_scim(self):

        #initialize endpoint  with 'scim' mode
        self.endpoint = Endpoint(keystone=self.keystone,mode="scim",support_quotas=False)

        # import 1st test data set
        self.endpoint.import_data('resources/scim/users.scim','resources/scim/groups.scim')

        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()

        # check for "Jens Mustermann" with perun_id == "1"
        self.assertTrue(after_import_users.has_key("1"))
        self._test_user(after_import_users['1'],'1','d877b2f6-3b90-4483-89ce-91eab1bdba99@elixir-europe.org','jens.mustermann@test.de',True)

        # check for "Thomas Mueller" with perun_id == "2"
        self.assertTrue(after_import_users.has_key("2"))
        self._test_user(after_import_users['2'],'2','afec0f6d-acd4-4dff-939d-208bfc272512@elixir-europe.org','thomas@mueller.de',False)

        # check for "Paul Paranoid" with perun_id == "3"
        self.assertTrue(after_import_users.has_key("3"))
        self._test_user(after_import_users['3'],'3','b3d216a7-8696-451a-9cbf-b8d5e17a6ec2@elixir-europe.org',None,True)

        # check for "Test Project" with perun_id =="9845"
        self.assertTrue(after_import_projects.has_key("9845"))
        self._test_project(after_import_projects['9845'],'9845',['1','2','3'])

        # check for "Sample Project" with perun_id == "9874"
        self.assertTrue(after_import_projects.has_key("9874"))
        self._test_project(after_import_projects['9874'],'9874',['3'])


        # now import 2nd test data set
        self.endpoint.import_data('resources/scim/users_2nd.scim','resources/scim/groups_2nd.scim')

        after_import_users_2 = self.keystone.users_map()
        after_import_projects_2 = self.keystone.projects_map()

        # user with perun_id == "1" not changed
        self.assertTrue(after_import_users_2.has_key("1"))
        self._test_user(after_import_users_2['1'],'1','d877b2f6-3b90-4483-89ce-91eab1bdba99@elixir-europe.org','jens.mustermann@test.de',True)

        # user with perun_id == "2" deleted
        self.assertFalse(after_import_users_2.has_key("2"))

        # user with perun_id == "3" disabled
        self.assertTrue(after_import_users_2.has_key("3"))
        self._test_user(after_import_users_2['3'],'3','b3d216a7-8696-451a-9cbf-b8d5e17a6ec2@elixir-europe.org',None,False)

        # user with perun_id == "4" added
        self.assertTrue(after_import_users_2.has_key("4"))
        self._test_user(after_import_users_2['4'],'4','bb01cabe-eae7-4e46-955f-b35db6e3d552@elixir-europe.org',None,True)

        # group with perun_id == "9845" not changed
        self.assertTrue(after_import_projects_2.has_key("9845"))
        self._test_project(after_import_projects_2['9845'],'9845',['1','3'])

        # group with perun_id == "9874" deleted
        self.assertFalse(after_import_projects_2.has_key("9874"))

        # group with perun_id == "9999" added
        self.assertTrue(after_import_projects_2.has_key("9999"))
        self._test_project(after_import_projects_2['9999'],'9999',['1','4'])


    def test_import_denbi_portal_compute_center(self):

        #initialize endpoint  with 'scim' mode
        self.endpoint = Endpoint(keystone=self.keystone,mode="denbi_portal_compute_center",support_quotas=False)

        # import 1st test data set
        self.endpoint.import_data('resources/denbi_portal_compute_center/users.scim','resources/denbi_portal_compute_center/groups.scim')

        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()


        # user 1 - enabled
        self.assertTrue(after_import_users.has_key('50000'))
        self._test_user(after_import_users['50000'],'50000','d877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org',None,True)
        # user 2 - enabled
        self.assertTrue(after_import_users.has_key('50001'))
        self._test_user(after_import_users['50001'],'50001','b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org',None,True)
        # user 3 - enabled
        self.assertTrue(after_import_users.has_key('50002'))
        self._test_user(after_import_users['50002'],'50002','bb01cabe-eae7-4e46-955f-b35db6e3d552__@elixir-europe.org',None,True)
        # user 4 - enabled
        self.assertTrue(after_import_users.has_key('50003'))
        self._test_user(after_import_users['50003'],'50003','ce317030-288f-4712-9e5c-922539777c62__@elixir-europe.org',None,True)
        # user 5 - disabled
        self.assertTrue(after_import_users.has_key('50004'))
        self._test_user(after_import_users['50004'],'50004','60420cf9-eb3e-45f4-8e1b-f8a2b317b042__@elixir-europe.org',None,False)

        # project 1
        self.assertTrue(after_import_projects.has_key("9999"))
        self._test_project(after_import_projects['9999'],'9999',['50000','50001','50002'])

        # project 2
        self.assertTrue(after_import_projects.has_key("10000"))
        self._test_project(after_import_projects['10000'],'10000',['50003'])