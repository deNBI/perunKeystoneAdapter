import sys
import tarfile
import os

from denbi.bielefeld.perun.endpoint import Endpoint
from denbi.bielefeld.perun.keystone import KeyStone

if len (sys.argv) != 2:
    print("usage: "+sys.argv[0]+" [perun_upload.tar.gz]")
    sys.exit(1)

fname = sys.argv[1]

cwd = os.getcwd()

# extract tar file
tar = tarfile.open(fname, "r:gz")
tar.extractall(path=cwd)
tar.close()

# import into keystone
keystone = KeyStone(default_role="user",create_default_role=True, support_quotas= False, target_domain_name='elixir')
endpoint = Endpoint(keystone=keystone,mode="denbi_portal_compute_center",support_quotas=False)
endpoint.import_data(cwd+'/users.scim',cwd+'/groups.scim')