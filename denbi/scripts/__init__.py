import os
from keystoneauth1.identity import v3
from keystoneauth1 import session
import keystoneclient.v3
import novaclient


def obtain_keyston_session():
    auth = v3.Password(
        auth_url=os.environ['OS_AUTH_URL'],
        username=os.environ['OS_USERNAME'],
        password=os.environ['OS_PASSWORD'],
        project_name=os.environ['OS_PROJECT_NAME'],
        user_domain_name=os.environ['OS_USER_DOMAIN_NAME'],
        project_domain_name=os.environ['OS_USER_DOMAIN_NAME']
    )
    return session.Session(auth=auth)

def obtain_keystone():
    return keystoneclient.v3.Client(session=obtain_keyston_session(), interface="public")

def obtain_nova():
    return novaclient.Client(2,session=obtain_keyston_session())