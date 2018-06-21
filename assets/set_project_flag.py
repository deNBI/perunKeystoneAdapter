#!/usr/bin/env python3

import os
import sys
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client

auth_url = os.environ['OS_AUTH_URL']
username = os.environ['OS_USERNAME']
password = os.environ['OS_PASSWORD']
project_name = os.environ['OS_PROJECT_NAME']
domain_name = os.environ['OS_USER_DOMAIN_NAME']

project_id=sys.argv[1]
flag=sys.argv[2]

auth = v3.Password(auth_url=auth_url,
        username=username,
        password=password,
        project_name=project_name,
        user_domain_name=domain_name,
        project_domain_name=domain_name)

sess = session.Session(auth=auth)

keystone = client.Client(session=sess,  interface="public")

keystone.projects.update(project_id, flag=flag)
