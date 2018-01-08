import unittest
import uuid

from denbi.bielefeld.perun.keystone import KeyStone


class TestKeystone(unittest.TestCase):
    """
        Unit test for class Keystone

    """

    def setUp(self):
        environ = {'OS_AUTH_URL':'http://localhost:5000/v3/',
                'OS_PROJECT_NAME':'admin',
                'OS_USER_DOMAIN_NAME':'Default',
                'OS_USERNAME':'admin',
                'OS_PASSWORD':'s3cr3t'}

        self.ks = KeyStone(environ,default_role="user",create_default_role=True)


    def __uuid(self):
        return str(uuid.uuid4())


    def test_user_create_list_delete(self):
        '''
        Test the methods users_create users_list and users_delete from KeyStone object.
        :return:
        '''

        print("Run 'test_user_create_list_delete'")

        perunid = self.__uuid()
        elixirid = perunid+"@elixir-europe.org"

        # create a new user
        denbi_user = self.ks.users_create(elixirid,perunid)

        # check internal user list
        denbi_user_map = self.ks.denbi_user_map
        self.assertTrue(denbi_user_map.has_key(perunid),"User with PerunId '"+perunid+"' does not exists in local user map.")

        # ask keystone for a fresh user list
        denbi_user_map =  self.ks.users_map()
        # user should also be provided to keystone
        self.assertTrue(denbi_user_map.has_key(perunid),"User with PerunId does not exists.")



        # delete previous created user
        self.ks.users_delete(denbi_user['perun_id'])

        # delete same user a second time should
        self.assertRaises(ValueError,self.ks.users_delete,denbi_user['perun_id'])

        # check internal user list
        denbi_user_map = self.ks.denbi_user_map
        self.assertFalse(denbi_user_map.has_key(perunid),"User with PerunId '"+perunid+"' does exists in local user map.")
        # check keystone user list
        denbi_user_map = self.ks.users_map()
        self.assertFalse(denbi_user_map.has_key(perunid),"User with PerunId does exists.")


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
        self.assertTrue(denbi_project_map.has_key(perunid),"Project with PerunId '"+perunid+"' does not exists in local project map.")

        # check keystone project list
        denbi_project_map = self.ks.projects_map()
        self.assertTrue(denbi_project_map.has_key(perunid),"Project with PerunId '"+perunid+"' does not exists.")

        # delete previous created project
        self.ks.projects_delete(denbi_project['perun_id'])

        # deleting it a second time should raise a ValueError
        self.assertRaises(ValueError,self.ks.projects_delete,denbi_project['perun_id'])


        # check internal project list
        denbi_project_map = self.ks.denbi_project_map
        self.assertFalse(denbi_project_map.has_key(perunid),"Project with PerunId '"+perunid+"' does exists in local project map.")

        # check keystone project list
        denbi_project_map = self.ks.projects_map()
        self.assertFalse(denbi_project_map.has_key(perunid),"Project with PerunId '"+perunid+"' does exists.")


    def test_all(self):
        '''
        Test a typically scenario, create two project (a,b), create two users (a,b,c), users ab are members of project a,
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
        user_a = self.ks.users_create(id,id+"@elixir-europe.org")
        id = self.__uuid()
        user_b = self.ks.users_create(id,id+"@elixir-europe.org")
        id = self.__uuid()
        user_c = self.ks.users_create(id,id+"@elixir-europe.org")


        #append user a,b to project a
        self.ks.projects_append_user(project_a['perun_id'],user_a['perun_id'])
        self.ks.projects_append_user(project_a['perun_id'],user_b['perun_id'])

        #append user a,b,c to project b
        self.ks.projects_append_user(project_b['perun_id'],user_a['perun_id'])
        self.ks.projects_append_user(project_b['perun_id'],user_b['perun_id'])
        self.ks.projects_append_user(project_b['perun_id'],user_c['perun_id'])


        projects = self.ks.denbi_project_map

        # Some tests if everything is stored in our project map
        self.assertEqual(projects[project_a['perun_id']], project_a)
        self.assertEqual(projects[project_b['perun_id']], project_b)

        list = project_a['members']
        expected_list = [user_a['perun_id'],user_b['perun_id']]
        self.assertListEqual(list,expected_list,
                         "Memberlist project_a contains ["+(",".join(list)) +"] but expected ["+(",".join(expected_list))+"]")

        list = project_b['members']
        expected_list = [user_a['perun_id'],user_b['perun_id'],user_c['perun_id']]

        self.assertListEqual(list,expected_list,
                         "Memberlist project_b contains ["+(",".join(list)) +"] but expected ["+(",".join(expected_list))+"]")


        # try to add an user that does not exists
        try:
            self.ks.projects_append_user(project_b['perun_id'],'0815')
            self.assertFalse(True)
        except:
            pass

        # try to remove an user that does not exists
        try:
            self.ks.projects_remove_user(project_a['perun_id'],"0815")
            self.assertFalse(True)
        except:
            pass

        # remove user a,b from project_a
        self.ks.projects_remove_user(project_a['perun_id'],user_a['perun_id'])
        self.ks.projects_remove_user(project_a['perun_id'],user_b['perun_id'])

        # remove user a,b,c from project b
        self.ks.projects_remove_user(project_b['perun_id'],user_a['perun_id'])
        self.ks.projects_remove_user(project_b['perun_id'],user_b['perun_id'])
        self.ks.projects_remove_user(project_b['perun_id'],user_c['perun_id'])

        self.assertEqual(len(project_a['members']),0)
        self.assertEqual(len(project_b['members']),0)

        # remove user a,b,c
        self.ks.users_delete(user_a['perun_id'])
        self.ks.users_delete(user_b['perun_id'])
        self.ks.users_delete(user_c['perun_id'])

        # ask keystone for new user map
        user_map = self.ks.users_map()

        self.assertEquals(len(user_map.keys()),count_users,
                          "Remove of users failed ... count "
                          +str(len(user_map.keys()))
                          +" but expect "+str(count_users)+"!")

        # remove project a,b
        self.ks.projects_delete(project_a['perun_id'])
        self.ks.projects_delete(project_b['perun_id'])

        # ask keystone for new project_map
        project_map = self.ks.projects_map()

        self.assertEquals(len(project_map.keys()),count_projects,
                          "Remove of projects failed ... count "
                          +str(len(project_map.keys()))
                               +" but expect "+str(count_projects)+"!")



if __name__ == '__main__':
    unittest.main()
