# Perun Keystone Adapter

Provides a small library that parses data propagated by [Perun](https://perun.elixir-czech.cz) and modifies a connected [Openstack](https://www.openstack.org) [Keystone]().

## Properties
 -  abstract keystone to simplify often used tasks (create/delete/update/list users and projects) 
 -  parse SCIM or de.NBI portal compute center propagation data for users and projects 


## Unit tests
The library comes with a set of unit tests - a running keystone instance is required to perfom the test. However, I suggest __not__ using a keystone that is used in a production enviroment. See [test/keystone/](/test/keystone) to retain a ready to-use docker container for this task.

## Example usage

ToDo