# Development and test environment

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

## Integrate DevStack
A simple solution to integrate a running DevStack vm into your test environment is to
use [shuttle](https://github.com/sshuttle/sshuttle) as a poors' man VPN connection.

You just need access to the remote network via ssh and don't necessarily have admin access
on it.

### Example:

An Openstack based vm is accessible through its floating ip (129.70.51.100)  and  has the local
ip 192.168.93.10. All DevStack Openstack services are bind to the local ip address.

```
sshuttle -r 129.70.51.100 192.168.93.10/32
```

The DevStack UI (with default configuration) is then accessible at http://192.168.93.10/dashboard.





