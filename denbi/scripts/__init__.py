"""Perun Keystone adapter scripts"""
import os

from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client


def obtain_keystone():
    auth = v3.Password(
        auth_url=os.environ['OS_AUTH_URL'],
        username=os.environ['OS_USERNAME'],
        password=os.environ['OS_PASSWORD'],
        project_name=os.environ['OS_PROJECT_NAME'],
        user_domain_name=os.environ['OS_USER_DOMAIN_NAME'],
        project_domain_name=os.environ['OS_USER_DOMAIN_NAME']
    )
    sess = session.Session(auth=auth)
    keystone = client.Client(session=sess, interface="public")
    return keystone
