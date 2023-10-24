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

import os
import unittest
import logging
import test
import uuid

import denbi.perun.endpoint

from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone

TESTDIR = os.path.dirname(os.path.realpath(__file__))

# configure logger
logging.basicConfig(level=logging.INFO)


class TestEndpoint(unittest.TestCase):
    """Unit test for class endpoint.

    You need a full functional Openstack setup to make the test run properly.
    """

    global log_domain, report_domain
    log_domain = "denbi"
    report_domain = "report"

    def setUp(self):
        # update logger format
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s -%(message)s')
        # set log level for logger_domain
        denbi = logging.getLogger(log_domain)
        denbi.setLevel(logging.ERROR)
        # set log level for report_domain
        report = logging.getLogger(report_domain)
        report.setLevel(logging.INFO)

        self.keystone = KeyStone(environ=None, default_role="user", create_default_role=True,
                                 target_domain_name='elixir', cloud_admin=True)
        self.neutron = self.keystone._neutron

        # Get an external network
        self.external_network_id = ''
        for network in self.neutron.list_networks()['networks']:
            if network['router:external']:
                self.external_network_id = network['id']
        if not self.external_network_id:
            self.fail("No external network found (Search for 'router:external' = True ")

    def __uuid(self):
        return str(uuid.uuid4())

    def test_validate_cidr(self):
        print("Run 'validate_cidr'")
        validate = denbi.perun.endpoint.validate_cidr
        self.assertTrue(validate("192.168.33.0/24"))
        self.assertTrue(validate("10.0.0.0/8"))
        self.assertTrue(validate("0.0.0.0/0"))
        self.assertFalse(validate("192.168.33/24"))
        self.assertFalse(validate("192.168.33.0/33"))
        self.assertFalse(validate("192.168.33.0"))

    def test_create_router(self):
        """ Test of a create_router."""

        print("Run 'test_create_router'")

        # create endpoint -> must fail, since no network_id is set
        try:
            Endpoint(keystone=self.keystone, mode="scim",
                     support_quotas=False,
                     support_router=True,
                     support_network=True,
                     support_default_ssh_sgrule=True)
            self.fail("Since no network_id is set, an exception MUST be thrown.")
        except Exception:
            pass

        # create endpoint -> should be successful
        endpoint = Endpoint(keystone=self.keystone, mode="scim",
                            support_quotas=False,
                            support_router=True,
                            support_network=True,
                            support_default_ssh_sgrule=True,
                            external_network_id=self.external_network_id)

        # create project manually
        denbi_project = self.keystone.projects_create(self.__uuid())

        # create router without network
        endpoint._create_router(denbi_project, router_only=True)

        # test if created project has one router
        router_list = self.neutron.list_routers(project_id=denbi_project["id"])["routers"]
        self.assertEqual(len(router_list), 1, "Expect exact one router.")

        # and delete it afterwards
        self.neutron.delete_router(router_list[0]['id'])

        # create router with network
        endpoint._create_router(denbi_project, router_only=False)
        # creat

        # test if created project has one router
        router_list = self.neutron.list_routers(project_id=denbi_project["id"])["routers"]
        self.assertEqual(len(router_list), 1, "Expect exact one router.")
        router = router_list[0]

        # test if created project has one network
        network_list = self.neutron.list_networks(project_id=denbi_project["id"])["networks"]
        self.assertEqual(len(network_list), 1, "Expect exact one network.")
        network = network_list[0]

        # test if created project has one subnet
        subnet_list = self.neutron.list_subnets(project_id=denbi_project["id"])["subnets"]
        self.assertEqual(len(subnet_list), 1, "Expect exact one subnet.")
        subnet = subnet_list[0]

        # test if found subnet is associated to found network
        self.assertEqual(subnet["network_id"], network["id"],
                         f"Expect subnet {subnet['id']} is associated to network {network['id']}.")

        # test if pro
        port_list = self.neutron.list_ports(device_owner='network:router_interface',
                                            project_id=denbi_project['id'])["ports"]
        self.assertEqual(len(port_list), 1, "Expect exact one router_interface.")
        port = port_list[0]

        self.assertEqual(port["device_id"], router["id"],
                         f"Expect router_interface port {port['id']} is associated to router {router['id']}.")
        self.assertEqual(port["fixed_ips"][0]["subnet_id"], subnet["id"],
                         f"Expect subnet {subnet['id']} is associated to router {router['id']}.")

        # cleanup
        endpoint._delete_routers(denbi_project['perun_id'])

        # tag previous created project as deleted
        self.keystone.projects_delete(denbi_project['perun_id'])
        # terminate previous marked project
        self.keystone.projects_terminate(denbi_project['perun_id'])

    def test_add_ssh_sgrule(self):
        print("Run 'test_add_ssh_sgrule'")

        endpoint = Endpoint(keystone=self.keystone, mode="scim",
                            support_quotas=False,
                            support_router=True,
                            support_network=True,
                            support_default_ssh_sgrule=True,
                            external_network_id=self.external_network_id)

        # create project manually
        denbi_project = self.keystone.projects_create(self.__uuid())

        # create sg_rule
        endpoint._add_ssh_sgrule(denbi_project["id"])

        # check if default security contains ssh-rule
        default_sg = self.neutron.list_security_groups(project_id=denbi_project["id"], name="default")["security_groups"]
        self.assertEqual(len(default_sg), 1, "Only one default sg expected.")

        found = False
        for rule in default_sg[0]['security_group_rules']:
            if rule['description'] == 'Allow ssh access.':
                found = True
        self.assertTrue(found, "Expected default sg has a ssh rule set.")

        # cleanup
        # tag previous created project as deleted
        self.keystone.projects_delete(denbi_project['perun_id'])
        # terminate previous marked project
        self.keystone.projects_terminate(denbi_project['perun_id'])

    def test_import_scim(self):
        print("Run 'test_import_scim'")

        # initialize endpoint  with 'scim' mode
        self.endpoint = Endpoint(keystone=self.keystone, mode="scim",
                                 support_quotas=False, support_router=False, support_network=False)

        # import 1st test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'scim', 'users.scim'),
                                  os.path.join(TESTDIR, 'resources', 'scim', 'groups.scim'))

        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()

        # check for "Jens Mustermann" with perun_id == "1"
        self.assertTrue("1" in after_import_users)
        test.test_user(self, denbiuser=after_import_users['1'], perun_id='1',
                       elixir_id='d877b2f6-3b90-4483-89ce-91eab1bdba99@elixir-europe.org',
                       email='jens.mustermann@test.de', enabled=True)

        # check for "Thomas Mueller" with perun_id == "2"
        self.assertTrue("2" in after_import_users)
        test.test_user(self, denbiuser=after_import_users['2'], perun_id='2',
                       elixir_id='afec0f6d-acd4-4dff-939d-208bfc272512@elixir-europe.org', email='thomas@mueller.de',
                       enabled=False)

        # check for "Paul Paranoid" with perun_id == "3"
        self.assertTrue("3" in after_import_users)
        test.test_user(self, denbiuser=after_import_users['3'], perun_id='3',
                       elixir_id='b3d216a7-8696-451a-9cbf-b8d5e17a6ec2@elixir-europe.org', email=None, enabled=True)

        # check for "Test Project" with perun_id =="9845"
        self.assertTrue("9845" in after_import_projects)
        test.test_project(self, after_import_projects['9845'],
                          perun_id='9845',
                          members=['1', '2', '3'])

        # check for "Sample Project" with perun_id == "9874"
        self.assertTrue("9874" in after_import_projects)
        test.test_project(self, after_import_projects['9874'],
                          perun_id='9874',
                          members=['3'])

        # now import 2nd test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'scim', 'users_2nd.scim'),
                                  os.path.join(TESTDIR, 'resources', 'scim', 'groups_2nd.scim'))

        after_import_users_2 = self.keystone.users_map()
        after_import_projects_2 = self.keystone.projects_map()

        # user with perun_id == "1" not changed
        self.assertTrue("1" in after_import_users_2)
        test.test_user(self, after_import_users_2['1'],
                       perun_id='1',
                       elixir_id='d877b2f6-3b90-4483-89ce-91eab1bdba99@elixir-europe.org',
                       email='jens.mustermann@test.de',
                       enabled=True)

        # user with perun_id == "2" tagged as deleted
        self.assertTrue("2" in after_import_users_2)
        test.test_user(self, after_import_users_2['2'],
                       perun_id='2',
                       elixir_id='afec0f6d-acd4-4dff-939d-208bfc272512@elixir-europe.org',
                       email='thomas@mueller.de',
                       enabled=False,
                       deleted=True)

        # user with perun_id == "3" disabled
        self.assertTrue("3" in after_import_users_2)
        test.test_user(self, after_import_users_2['3'],
                       perun_id='3',
                       elixir_id='b3d216a7-8696-451a-9cbf-b8d5e17a6ec2@elixir-europe.org',
                       enabled=False)

        # user with perun_id == "4" added
        self.assertTrue("4" in after_import_users_2)
        test.test_user(self, after_import_users_2['4'],
                       perun_id='4',
                       elixir_id='bb01cabe-eae7-4e46-955f-b35db6e3d552@elixir-europe.org',
                       enabled=True)

        # group with perun_id == "9845" not changed
        self.assertTrue("9845" in after_import_projects_2)
        test.test_project(self, after_import_projects_2['9845'],
                          perun_id='9845',
                          members=['1', '3'])

        # group with perun_id == "9874" tagged as deleted
        self.assertTrue("9874" in after_import_projects_2)
        test.test_project(self, after_import_projects_2['9874'],
                          perun_id='9874',
                          members=['3'],
                          deleted=True)

        # group with perun_id == "9999" added
        self.assertTrue("9999" in after_import_projects_2)
        test.test_project(self, after_import_projects_2['9999'],
                          perun_id='9999',
                          members=['1', '4'])

        # clean up everything
        ids = set(self.keystone.users_map())
        for perun_id in ids:
            self.keystone.users_delete(perun_id)
            self.keystone.users_terminate(perun_id)

        ids = set(self.keystone.projects_map())
        for perun_id in ids:
            self.keystone.projects_delete(perun_id)
            self.keystone.projects_terminate(perun_id)

    def test_import_denbi_portal_compute_center_legacy(self):
        '''
        Initialize endpoint  with 'denbi_portal_compute_center' mode and legacy options
        (no support for email, elixir_name and ssh_key). Test just loads first test set and check
        first user.
        '''

        print("Run 'test_import_denbi_portal_compute_center_legacy'")
        self.endpoint = Endpoint(keystone=self.keystone,
                                 mode="denbi_portal_compute_center",
                                 store_email=False,
                                 support_elixir_name=False,
                                 support_ssh_key=False,
                                 support_quotas=True)

        # import 1st test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'users.scim'),
                                  os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'groups.scim'))

        after_import_users = self.keystone.users_map()

        # check for 2nd user, elixir_name, email and ssh_key must be unset (Null)
        self.assertTrue('50001' in after_import_users)
        test.test_user(self, after_import_users['50001'],
                       perun_id='50001',
                       elixir_id='b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org',
                       elixir_name=None,
                       email=None,
                       enabled=True,
                       ssh_key=None)

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
        '''
        Initialize with 'denbi_portal_compute_center' mode
        '''

        print("Run 'test_import_denbi_portal_compute_center'")

        self.endpoint = Endpoint(keystone=self.keystone,
                                 mode="denbi_portal_compute_center")

        # import 1st test data set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'users.scim'),
                                  os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'groups.scim'))

        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()

        # user 1 - enabled
        self.assertTrue('50000' in after_import_users)
        test.test_user(self, after_import_users['50000'],
                       perun_id='50000',
                       elixir_id='d877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org',
                       elixir_name='user1',
                       email='user1@donot.use',
                       enabled=True)
        # user 2 - enabled
        self.assertTrue('50001' in after_import_users)
        test.test_user(self, after_import_users['50001'],
                       perun_id='50001',
                       elixir_id='b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org',
                       elixir_name='user2',
                       email='user2@donot.use',
                       enabled=True,
                       ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDAVHWAYM0dsLYsW9BRZYWHBgxlmWS1V58jaQLFpUOpS"
                               "6lRajwoorLcSJu0HOEtNi0JV4K43Sq/zQQsYe49NBxNcwYxmO1mRtA2tuz+azB1AvPLtE4WQHz6W09wMp"
                               "ZeRA28Njjclm+2kuHKDYGr6miWwtyPRQtYMipVWVcE7w/TAevn05uwbvTW5IeekR6QD1DXHarRzfWwPiH"
                               "Y5QwN+6emKQqIeWENBitkWAAD3NLI5UP581kk3SlrJ8Rgx6OZ1BLOh3mt/l4dEjmjFKJLZITReLVDRnUd"
                               "2EycKpwFRTnn9ToH5dYIn+e7kPHtW9uSpVL5dbsC323Iq/pfOj5zucPV/xhDMSS3HoQgaoAN0pySSuwvJ"
                               "MoRBwSBcjXZ0+0TwMSkLUoe3s6gfPpOsiJECa2w0ZsHALgvutzqkQ+vpcBWiZhrCPOQBa4sjvaucHxl3e"
                               "U/MjwjJieRQMycvLjle10A7j1OoHWHxWAkYtrSVeB4Qiw4x/aw0DsjFPonOKYM/Q3kI9fAC4G5YcYtgil"
                               "Vg/CqHsPOUJr6OkdW2ERVU+Z8wblC6yqRyw4ZP5FFiJxwZu6PVwAJCcvT5AB/+V3Rx3db98N23C2fZLbK"
                               "p87gAYbKNqtWJfzRAzS6ZJfXkb1u7a3kIY2gTA8lCAj6p/o66CgKqc5XnomOt+Hg1fFJOrvaHw== hxr@mk")
        # user 3 - enabled
        self.assertTrue('50002' in after_import_users)
        test.test_user(self, after_import_users['50002'],
                       perun_id='50002',
                       elixir_id='bb01cabe-eae7-4e46-955f-b35db6e3d552__@elixir-europe.org',
                       elixir_name='user3',
                       email='user3@donotuse',
                       enabled=True)
        # user 4 - enabled
        self.assertTrue('50003' in after_import_users)
        test.test_user(self, after_import_users['50003'],
                       perun_id='50003',
                       elixir_id='ce317030-288f-4712-9e5c-922539777c62__@elixir-europe.org',
                       elixir_name='user4',
                       email='user4@donotuse',
                       enabled=True)
        # user 5 - disabled
        self.assertTrue('50004' in after_import_users)
        test.test_user(self, after_import_users['50004'],
                       perun_id='50004',
                       elixir_id='60420cf9-eb3e-45f4-8e1b-f8a2b317b042__@elixir-europe.org',
                       elixir_name='user5',
                       email='user5@donotuse',
                       enabled=False)

        # project 1
        self.assertTrue("9999" in after_import_projects)
        test.test_project(self, after_import_projects['9999'],
                          perun_id='9999',
                          members=['50000', '50001', '50002'])

        # project 2
        self.assertTrue("10000" in after_import_projects)
        test.test_project(self, after_import_projects['10000'],
                          perun_id='10000',
                          members=['50003'])

        # import 2nd test data set, which should update the 1st data-set
        self.endpoint.import_data(os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'users_2nd.scim'),
                                  os.path.join(TESTDIR, 'resources', 'denbi_portal_compute_center', 'groups_2nd.scim'))

        # reread users and project map from database
        after_import_users = self.keystone.users_map()
        after_import_projects = self.keystone.projects_map()

        # user 1 - enabled, add ssh-key
        self.assertTrue('50000' in after_import_users)
        test.test_user(self, after_import_users['50000'],
                       perun_id='50000',
                       elixir_id='d877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org',
                       elixir_name='user1',
                       email='user1@donot.use',
                       enabled=True,
                       ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC580K3zIwR59Ur+A6NkcWYufWTUaSmrDFWiobhtLUXauq"
                               "QFyYpJHXOfp4ZtPYtnlLDRFhlCdIta1NgYGx2klJa/ySObSmbaasg7gCRClTMRS/6vCOg3Vkw6JbQX1Si8x"
                               "LVsy1dlpR9rf5PW3o7pPVZ8nRMwDN+qtqLNdFjhzjEmpEsFSFWDvXgGvCqWBEI0Zhutv3xdtb3yBI0oM2pJ"
                               "gGNbUCr3Hz2X2bVoLIxx0BvjWMjxGztBDDAcxGmaoJS6W0sTqWOX5EagA7fQAY3XTRJ6PMGJWfsdTsztmos"
                               "BNYfOGtdq6/Gbjo40d/fxCWVY9z/a9o/kyls/XghwLIAZl4h user1@unkown.de")
        # user 2, deleted
        self.assertTrue('50001' in after_import_users)
        test.test_user(self, after_import_users['50001'],
                       perun_id='50001',
                       deleted=True)
        # user 3 - enabled
        self.assertTrue('50002' in after_import_users)
        test.test_user(self, after_import_users['50002'],
                       perun_id='50002',
                       elixir_id='bb01cabe-eae7-4e46-955f-b35db6e3d552__@elixir-europe.org',
                       elixir_name='user3',
                       email='user3@donotuse',
                       ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC580K3zIwR59Ur+A6NkcWYufWTUaSmrDFWiobhtLUXauq"
                               "QFyYpJHXOfp4ZtPYtnlLDRFhlCdIta1NgYGx2klJa/ySObSmbaasg7gCRClTMRS/6vCOg3Vkw6JbQX1Si8x"
                               "LVsy1dlpR9rf5PW3o7pPVZ8nRMwDN+qtqLNdFjhzjEmpEsFSFWDvXgGvCqWBEI0Zhutv3xdtb3yBI0oM2pJ"
                               "gGNbUCr3Hz2X2bVoLIxx0BvjWMjxGztBDDAcxGmaoJS6W0sTqWOX5EagA7fQAY3XTRJ6PMGJWfsdTsztmos"
                               "BNYfOGtdq6/Gbjo40d/fxCWVY9z/a9o/kyls/XghwLIAZl4h user3@unkown.de",
                       enabled=False)
        # user 4 - enabled
        self.assertTrue('50003' in after_import_users)
        test.test_user(self, after_import_users['50003'],
                       perun_id='50003',
                       elixir_id='ce317030-288f-4712-9e5c-922539777c62__@elixir-europe.org',
                       elixir_name='user4',
                       email='user4@donotuse',
                       enabled=True)
        # user 5 - deleted
        self.assertTrue('50004' in after_import_users)
        test.test_user(self, after_import_users['50004'],
                       perun_id='50004',
                       deleted=True)

        # project 1
        self.assertTrue('9999' in after_import_projects)
        test.test_project(self, after_import_projects['9999'],
                          perun_id='9999',
                          members=['50000', '50002'])

        # project 2 - deleted
        self.assertTrue('10000' in after_import_projects)
        test.test_project(self, after_import_projects['10000'],
                          perun_id='10000',
                          deleted=True)

        # project 3
        self.assertTrue('10001' in after_import_projects)
        test.test_project(self, after_import_projects['10001'],
                          perun_id='10001',
                          members=['50003'])

        # clean up everything
        ids = set(self.keystone.users_map())
        for perun_id in ids:
            self.keystone.users_delete(perun_id)
            self.keystone.users_terminate(perun_id)

        ids = set(self.keystone.projects_map())
        for perun_id in ids:
            self.keystone.projects_delete(perun_id)
            self.keystone.projects_terminate(perun_id)


if __name__ == '__main__':
    unittest.main()
