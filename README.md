# Perun Keystone Adapter

Provides a small library that parses data propagated by [Perun](https://perun.elixir-czech.cz) and modifies a connected [Openstack](https://www.openstack.org) [Keystone]().

## Properties
 -  abstract keystone to simply often used tasks (create/delete/update/list users and projects) 
 -  parse SCIM propagation data for users and projects 
 -  ...


## Unit tests
The library comes with a set of unit tests - a running keystone instance is required to perfom the test. However, I suggest __not__ using a keystone that is used in a production environent. See [test/keystone/](/test/keystone) to retain a ready to-use docker container for this task.


## Todo
 - add support for de.NBI propagation data 
 - ...