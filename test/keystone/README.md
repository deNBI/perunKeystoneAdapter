# Test environment

## Start and configure keystone from a docker container
There are several inoffical container available at docker hub that provides a local keystone in a container. After some short investigations I decided to use the [monasca/keystone](https://hub.docker.com/r/monasca/keystone/) container. At the time of writing the container is based on Ubuntu 16.04 with the Mitaka keystone release installed. Starting of the container with a default setup is quite simple, just run the container as background process and expose the keystone specific network ports to the docker host.

```docker run -d -p 5000:5000 -p 35357:35357 monasca/keystone```

### Default configuration:

| key          | value     |
|--------------|-----------|
| project name | admin     |
| user name    | admin     |
| password     | s3crt     |
| region       | RegionOne |

You can use the [keystone-openrc.sh](keystone-openrc.sh) file to set your shell environment to access the docker keystone container.

```$ source keystone-openrc.sh ```

### Clean up keystone
It could be sometimes usefull to clean up your keystone test setup. A [small script](clean_keystone.sh) do the job perfectly.

```$ clean_keystone.sh```

### Example

```
$ openstack user list
+----------------------------------+------------------------+
| ID                               | Name                   |
+----------------------------------+------------------------+
| 40683fa8ebf841b59506c25caef56cd6 | admin                  |
| f12949f3a8294670a66ec037a1d96c85 | mini-mon               |
| cc54770ce10e4163a10366b440254b2c | monasca-agent          |
| 33b68f4b72304538afc9e6b3bb189737 | demo                   |
| bb01198d45e24670b9a2fa991e583642 | monasca-read-only-user |
+----------------------------------+------------------------+
```
