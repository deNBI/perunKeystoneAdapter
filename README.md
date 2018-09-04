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
 -  set/modify project quotas (**alpha state**, needs a full openstack  installation like [DevStack](https://docs.openstack.org/devstack/latest/) for testing)
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

   * `user_id` is or `project_id` the OpenStack specific ID
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
The following script unzip and untar the propagated information and  add it to the keystone database. Keystone is addressed by environment variables (sourcing the openstack rc file) or  directly by passing an environemt map (not used in the example). The Openstack user needs at least permission to modify entries in Keystone

```console
$ perun_propagation perun_upload.tar.gz
```

### WSGI script

The python module also contains a built-in server version of the `perun_propagation` script. The script uses [flask](http://flask.pocoo.org/) to provide an upload function and run library functions in a separate thread. It can be simply tested starting the flask built-in webserver ...

```console
$ perun_propagation_service
 * Serving Flask app "denbi.scripts.perun_propagation_service" (lazy loading)
 * Environment: production
   WARNING: Do not use the development server in a production environment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

For running this in production it is typical to use something like `gunicorn` as follows:

```console
$ gunicorn --workers 1 --bind 127.0.0.1:5000 denbi.scripts.perun_propagation_service:app 
```

## Development

### Unit tests

The library comes with a set of unit tests - a running keystone instance is required to perfom the test. The `Makefile` included with the project runs a docker container for providing a keystone server. It is **not** recommended to use your production keystone.

There currently **no** tests for setting/modify project quotas.

### Linting

```
$ make lint
```

will run flake8 on the source code directories.
