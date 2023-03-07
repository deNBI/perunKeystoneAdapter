[![Documentation Status](https://readthedocs.org/projects/perunkeystoneadapter/badge/?version=latest)](https://perunkeystoneadapter.readthedocs.io/en/latest/?badge=latest)

# Perun Keystone Adapter

The *Perun Keystone Adapter* is a library written in Python that parses data propagated by [Perun](https://perun.elixir-czech.cz) and modifies a connected [Openstack](https://www.openstack.org) [Keystone](https://docs.openstack.org/keystone/latest/).

## Features

 -  abstract keystone to simplify often used tasks (create/delete/update/list users and projects)
 -  parse SCIM or de.NBI portal compute center propagation data for users and projects
 -  modify Keystone according the propagated data:
 -  creates items (users or projects) in Keystone if they not exists but propagated
 -  modify items properties if they changed
 -  mark items as deleted and disable them in Keystone if they are not propagated any more
 -  deleting (marked and disabled) items functionality is available but not integrated in the normal workflow.
 -  set/modify project quotas (needs a full openstack  installation like [DevStack](https://docs.openstack.org/devstack/latest/) for testing)
 -  compatible with python 2.7.x and python 3

## Preparation

Before installing Perun Keystone Adapter you must be sure that used openstack domain for propagation is empty *or*  all existing projects and users that also exists in perun must be tagged to avoid naming conflicts and the project names must have the same names as the groups in perun. By default everything created by the library is tagged as *perun_propagation*. This can be overwritten in the constructor of the KeyStone class.

As a help there are two scripts included in the assets directory of this repository that set a flag of your choice for a user and for a project.

1. First install all necessary dependencies (maybe in your virtual environment) by running

   ```console
   $ pip install -r requirements.txt
   ```

2. The scripts expect that you sourced your OpenStack rc file:

   ```console
   $ source env.rc
   ```

3. Run the python script

   ```console
   $ python set_project_flag.py  project_id flag_name
   ```

   or

   ```console
   $ python set_user_flag.py  user_id flag_name
   ```

   where

   * `user_id` and `project_id` are OpenStack specific IDs
   * `flag_name` can be any value which is set for the `flag` attribute. If you do not modify the perunKeystoneAdapter, it expects `perun_propagation` as the value.

## Installation

Install a specific version of this library by providing a tag of the [releases page](https://github.com/deNBI/perunKeystoneAdapter/releases):

E.g: for version **0.1.1**:

```bash
pip install git+https://github.com/deNBI/perunKeystoneAdapter@0.1.1
```

## Usage

### Commandline client

The perun propagation service transfers a zipped tar file containing a users and groups file in scim format.
The following script unzips and untars the propagated information and adds it to the keystone database. Keystone is addressed by environment variables (sourcing the openstack rc file) or directly by passing an environemt map (not used in the example). The Openstack user needs at least permission to modify entries in Keystone

```console
$ perun_propagation perun_upload.tar.gz
```

### WSGI script

The python module also contains a built-in server version of the `perun_propagation` script. The script uses [flask](http://flask.pocoo.org/) to provide an upload function and run library functions in a separate thread. It can be simply tested starting the flask built-in webserver.

```console
$ perun_propagation_service
 * Serving Flask app "denbi.scripts.perun_propagation_service" (lazy loading)
 * Environment: production
   WARNING: Do not use the development server in a production environment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

For running this in production it is easy to use `gunicorn` as follows:

```console
$ gunicorn --workers 1 --bind 127.0.0.1:5000 denbi.scripts.perun_propagation_service:app
```

### Docker

Build docker container.

```docker build -t denbi/pka .```

Create configuration file (`pka.cfg`), for example (with cloud admin credentials) :

```
OS_REGION_NAME="XXX"
OS_PROJECT_DOMAIN_ID="XXX"
OS_INTERFACE="public"
OS_AUTH_URL="https://XXX"
OS_USERNAME="admin"
OS_PROJECT_ID="XXX"
OS_USER_DOMAIN_NAME="Default"
OS_PROJECT_NAME="admin"
OS_PASSWORD="XXX"
OS_IDENTITY_API_VERSION="3"

# Domain to create users and projects in, defaults to 'elixir'
TARGET_DOMAIN_NAME="elixir"
# Decides if Cloud admin or domain admin should be used
CLOUD_ADMIN=True
# Do not make any modifications to keystone
KEYSTONE_READ_ONLY=False
# Default role to assign to new users, defaults to 'user'
DEFAULT_ROLE="member"
# Use nested project instead of cloud/domain admin
NESTED=False
# Set quotas for projects
SUPPORT_QUOTA=False
# base dir for storing uploaded perun files
BASE_DIR="/perun/upload/"
# log dir
LOG_DIR="/perun/log/"
# clean up uploaded data
CLEANUP=False
```

and  run container:

```docker run -v $(pwd)/pka.cfg:/perun_propagation_sevice.cfg -v $(pwd)/perun/upload:/perun/upload -v $(pwd)/perun/log:/perun/log denbi/pka```

There are [additional deployment options available](https://flask.palletsprojects.com/en/1.1.x/deploying/) if you prefer to run WSGI applications with Apache, or other setups.

### Logging 
The Library supports two different logger domains, which can be configured when instantiating the Keystone/Endpoint class (default "denbi" and "report").
All changes concerning the Openstack database (project, identity and quotas) are logged to the logging domain, everything else 
is logged to the report domain. The loggers are standard Python logger, therefore all possibilities of Python's logging API 
are supported.
See [service script](denbi/scripts/perun_propagation_service.py) for an example  how to configure logging. 


## Development

### Unit tests

The library comes with a set of unit tests - a full functional keystone is required to perfom all tests.

For testing the user/project management only a running keystone is enough. The `Makefile` included with 
the project runs a docker container for providing a keystone server. 

It is recommended to configure and use a [DevStack](https://docs.openstack.org/devstack/latest/) installation
to test all functionalities.

In every case it is **not** recommended to use your production keystone/setup .


### Linting

```
$ make lint
```

will run flake8 on the source code directories.

### DevStack

- Install Devstack in 
- optional: use sshuttle to connect
- add admin endpoint for identity service
- build docker container
- run docker container 
