# Test environment

We need a full functional installation to test PerunKeystoneAdapter.
[DevStack](https://docs.openstack.org/devstack/latest/) seems to be 
the best solution for this use case.

## Setup an Openstack DevStack on VM

DevStack is a series of extensible scripts used to quickly bring up a complete 
OpenStack environment based on the latest versions of everything from git master. 
It is used interactively as a development environment and as the basis for much of 
the OpenStack project’s functional testing.

Setting up a fully functional Openstack Setup on a single vm is just a matter of time.
Depending on your VM "hardware"  and  the connection speed it takes about 20 minutes.

See the [DevStack](https://docs.openstack.org/devstack/latest/) page on 
[docs.openstack.org](https://docs.openstack.org) for installation manual. From my 
experiences this work out of box since the Openstack Pike release.

## poor's man ssh-connection 
- sshuttle
- 




