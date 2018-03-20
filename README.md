# Perun Keystone Adapter

The *Perun Keystone Adapter* is a library written in Python that parses data propagated by [Perun](https://perun.elixir-czech.cz) and modifies a connected [Openstack](https://www.openstack.org) [Keystone](https://docs.openstack.org/keystone/latest/).

## Install

Install a specific version of this library by providing a tag of the [releases page](https://github.com/deNBI/perunKeystoneAdapter/releases):

E.g: for version **0.1.1**:

~~~BASH
pip install git+https://github.com/deNBI/perunKeystoneAdapter@0.1.1
~~~

## Caveats
Before installing Perun Keystone Adapter you must be sure that used openstack domain for propagation is empty *or*  all existing projects and users that also exists in perun must be tagged to avoid naming conflicts and the project names must
have the same names as the groups in perun.
Per default everything created by the library is tagged as *perun_propagation*. This can be overwritten in the constructor of the KeyStone class.

## Properties
 -  abstract keystone to simplify often used tasks (create/delete/update/list users and projects) 
 -  parse SCIM or de.NBI portal compute center propagation data for users and projects
 -  modify Keystone according the propagated data: 
 -  creates items (users or projects) in Keystone if they not exists but propagated
 -  modify items properties if they changed
 -  mark items as deleted and disable them in Keystone if they are not propagated any more
 -  deleting (marked and disabled) items functionality is available but not integrated in the normal workflow.
 -  set/modify project quotas (**alpha state**, needs a full openstack  installation like [DevStack](https://docs.openstack.org/devstack/latest/) for testing)
 -  compatible with python 2.7.x and python 3
   

## Unit tests
The library comes with a set of unit tests - a running keystone instance is required to perfom the test. However, I suggest __not__ using a keystone that is used in a production enviroment. See [test/keystone/](/test/keystone) to retain a ready to-use docker container solution for this task.

There currently **no** tests for setting/modify project quotas.

## Example usage

### Commandline client

The perun propagation service transfers a zipped tar file containing a users and groups file in scim format.
The following script unzip and untar the propagated information and  add it to the keystone database. Keystone is addressed by environment variables (sourcing the openstack rc file) or  directly by passing an environemt map (not used in the example). The Openstack user needs at least permission to modifies Keystone

```
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
```

### WSGI script

The [example directory](python/example) also contains an [example](python/example/perun_propagation_service.py) for using the Perun Keystone Adapter library in a Python wsgi script. The script uses [flask](http://flask.pocoo.org/) to provide an upload function and run library functions in a separate thread. It can be simply tested starting the flask built-in webserver ...

```
$ python3 service.py
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
127.0.0.1 - - [23/Feb/2018 09:54:16] "PUT /upload HTTP/1.1" 200 -
...
```
... and using curl to upload sample propagation data.

```
$ curl -T file http://127.0.0.1:5000/upload
```

_However, the script is a proof of concept and it is **not recommend** using it as it is._
