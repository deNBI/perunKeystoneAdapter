Introduction
============

perunKeystoneAdapter is written to receive data from ELIXIR's Perun
system, and convert this into users and group in Keystone.

It receives data in the form of a tarball from Perun. This tarball
contains numerous files, the most important of which are the
``users.json`` and ``groups.json``:

Here is an example user file:

.. code:: json

    [
       {
          "blacklisted" : null,
          "status" : "VALID",
          "login-namespace:elixir-persistent" : "b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org",
          "denbiVmsRunning" : null,
          "id" : 50001,
          "preferredMail" : "user2@donot.use",
          "sshPublicKey" : [
             "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDAVHWAYM0dsLYsW9BRZYWHBgxlmWS1V58jaQLFpUOpS6lRajwoorLcSJu0HOEtNi0JV4K43Sq/zQQsYe49NBxNcwYxmO1mRtA2tuz+azB1AvPLtE4WQHz6W09wMpZeRA28Njjclm+2kuHKDYGr6miWwtyPRQtYMipVWVcE7w/TAevn05uwbvTW5IeekR6QD1DXHarRzfWwPiHY5QwN+6emKQqIeWENBitkWAAD3NLI5UP581kk3SlrJ8Rgx6OZ1BLOh3mt/l4dEjmjFKJLZITReLVDRnUd2EycKpwFRTnn9ToH5dYIn+e7kPHtW9uSpVL5dbsC323Iq/pfOj5zucPV/xhDMSS3HoQgaoAN0pySSuwvJMoRBwSBcjXZ0+0TwMSkLUoe3s6gfPpOsiJECa2w0ZsHALgvutzqkQ+vpcBWiZhrCPOQBa4sjvaucHxl3eU/MjwjJieRQMycvLjle10A7j1OoHWHxWAkYtrSVeB4Qiw4x/aw0DsjFPonOKYM/Q3kI9fAC4G5YcYtgilVg/CqHsPOUJr6OkdW2ERVU+Z8wblC6yqRyw4ZP5FFiJxwZu6PVwAJCcvT5AB/+V3Rx3db98N23C2fZLbKp87gAYbKNqtWJfzRAzS6ZJfXkb1u7a3kIY2gTA8lCAj6p/o66CgKqc5XnomOt+Hg1fFJOrvaHw== hxr@mk"
          ]
       },
       ...
    ]

And an example of the groups file:

.. code:: json

    [
         {
              "denbiProjectInstitute" : null,
              "denbiProjectObjectStorage" : null,
              "denbiProjectStatus" : null,
              "name" : "Test Projekt",
              "denbiProjectRamPerVm" : 8,
              "description" : "---",
              "denbiDirectAccess" : null,
              "denbiProjectMembers" : [
                 {
                    "login-namespace:elixir" : "user1",
                    "login-namespace:elixir-persistent" : "d877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org",
                    "id" : 50000,
                    "preferredMail" : "user1@donot.use"
                 },
                 ...
              ],
              "parentGroupId" : null,
              "denbiProjectNumberOfVms" : 10,
              "denbiProjectDiskSpace" : null,
              "denbiProjectNumberOfCpus" : 80,
              "id" : 9999,
              "denbiProjectLifetime" : null,
              "denbiProjectSpecialPurposeHardware" : null
         },
         ...
    ]

perunKeystoneAdapter functions to **sync** this data with your keystone.
All pre-existing users in your keystone will be completely unaffected.
From here, perunKeystoneAdapter will manage only the users that are
tagged with their associated perun ID.

Quickstart
==========

This will help you get setup with the perunKeystoneAdapter at your local
OpenStack deployment.

Prerequisites
-------------

-  A **non-production** keystone server
-  Python, Pip

Installation
------------

You can install the latest version of this repository with python's pip:

.. code:: console

    pip install git+https://github.com/deNBI/perunKeystoneAdapter@master

Running
-------

There are two alternatives for running the adapter. A CLI version that
is useful for testing, and a web-server version that is more useful in
production.

CLI
~~~

Given an `example Perun
tarball <https://github.com/deNBI/perunKeystoneAdapter/blob/freiburg/test/resources/perun.tar.gz>`__
We have some commands available to us to try syncing that data to our
keystone:

.. code:: console

    perun_propagation [--read-only] [-v] tarball

The ``--read-only`` and ``--verbose`` flags are great when you're
testing, if you are nervous about what changes could be applied to your
openstack. If you are running on a brand new keystone (e.g. from a
container) it will fail due to the domain not having been created yet.
``'KeyStone' object has no attribute 'target_domain_id'``

.. code:: console

    $ perun_propagation -v test/resources/perun.tar.gz
    INFO:denbi.bielefeld.perun.endpoint:Importing data mode=denbi_portal_compute_center users_path=/tmp/tmpaqduxj3q/users.scim groups_path=/tmp/tmpaqduxj3q/groups.scim
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50000 elixir_id=d877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org email=user1@donot.use, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50001 elixir_id=b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org email=user2@donot.use, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50002 elixir_id=bb01cabe-eae7-4e46-955f-b35db6e3d552__@elixir-europe.org email=user3@donotuse, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50003 elixir_id=ce317030-288f-4712-9e5c-922539777c62__@elixir-europe.org email=user4@donotuse, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50004 elixir_id=60420cf9-eb3e-45f4-8e1b-f8a2b317b042__@elixir-europe.org email=user5@donotuse, enabled=False
    INFO:denbi.bielefeld.perun.endpoint:Creating project 9999 with name=Test Projekt members={50000,50001,50002}
    INFO:denbi.bielefeld.perun.endpoint:Creating project 10000 with name=Test Projekt 2 members={50003}

Server
~~~~~~

There is a flask app included as well:

.. code:: console

    $ PERUN_LOG_LEVEL=INFO perun_propagation_service  --port 8000
     * Serving Flask app "denbi.scripts.perun_propagation_service" (lazy loading)
     * Environment: production
       WARNING: Do not use the development server in a production environment.
       Use a production WSGI server instead.
     * Debug mode: off
    INFO:werkzeug: * Running on http://0.0.0.0:8000/ (Press CTRL+C to quit)

You can upload the tarball using curl:

.. code:: console

    $ curl -T test/resources/perun.tar.gz \
        http://localhost:8000/upload

Which will produce an identical output

.. code:: console

    INFO:werkzeug:127.0.0.1 - - [13/Sep/2018 12:35:44] "PUT /upload HTTP/1.1" 200 -
    INFO:root:Processing data uploaded by Perun: /tmp/perun_uploadk34p4gg0.tar.gz
    INFO:denbi.bielefeld.perun.endpoint:Importing data mode=denbi_portal_compute_center users_path=/tmp/tmpd9ooj5wo/users.scim groups_path=/tmp/tmpd9ooj5wo/groups.scim
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50000 elixir_id=d877b2f6-3b90-4483-89ce-91eab1bdba99__@elixir-europe.org email=user1@donot.use, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50001 elixir_id=b3d216a7-8696-451a-9cbf-b8d5e17a6ec2__@elixir-europe.org email=user2@donot.use, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50002 elixir_id=bb01cabe-eae7-4e46-955f-b35db6e3d552__@elixir-europe.org email=user3@donotuse, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50003 elixir_id=ce317030-288f-4712-9e5c-922539777c62__@elixir-europe.org email=user4@donotuse, enabled=True
    INFO:denbi.bielefeld.perun.endpoint:Creating user 50004 elixir_id=60420cf9-eb3e-45f4-8e1b-f8a2b317b042__@elixir-europe.org email=user5@donotuse, enabled=False
    INFO:denbi.bielefeld.perun.endpoint:Creating project 9999 with name=Test Projekt members={50000,50001,50002}
    INFO:denbi.bielefeld.perun.endpoint:Creating project 10000 with name=Test Projekt 2 members={50003}
    INFO:root:Finished processing /tmp/perun_uploadk34p4gg0.tar.gz

Production
==========

For production usage you should use ``gunicorn``:

.. code:: console

    $ gunicorn \
        --workers 1 \
        --bind localhost:9000 \
        denbi.scripts.perun_propagation_service:app

SSL Verification
----------------

Which should be placed behind a reverse proxy. When Perun posts data,
they will use an SSL client certificate:

-  `elixir.pem <elixir.pem>`__
-  `elixir\_chain.pem <elixir_chain.pem>`__

You *must* verify the SSL client certificate.

haproxy
~~~~~~~

::

    listen perun_propagation
      bind {{ controller.public_ip  }}:5005 ssl crt /etc/haproxy/cert.pem ca-file /etc/haproxy/elixir.pem verify required
      mode http
      balance source

nginx
~~~~~

.. code:: nginx

    server {
        ssl_client_certificate /etc/nginx/elixir.pem;
        ssl_verify_client optional;

        location /perun/ {
            if ($ssl_client_verify != SUCCESS) {
                return 403;
            }

            proxy_pass http://localhost:5000/;
        }
    }


Generating an SSL Client Certificate for Testing
------------------------------------------------

Create server certificate
~~~~~~~~~~~~~~~~~~~~~~~~~

We create a new self-signed server certifcate to sign our client
certificates later.

``openssl req -new > server.cert.csr``

-  Country name : *DE*
-  State or province name: *Nordrhein-Westfalen*
-  Organization name : *Universitaet Bielefeld*

``openssl rsa -in privkey.pem -out server.cert.key``

``openssl x509 -in server.cert.csr -out server.cert.crt  -req -signkey server.cert.key -days 365``

Create client certificate
~~~~~~~~~~~~~~~~~~~~~~~~~

After creating a self-signed cerver certificate, we create a client
certificate and sign it with the server certificate.

Before we start we have to do some prerequites, depending on openssl
configuration this may be different on your system. The following works
using OSX with an openssl macports setup, but should also work on any
linux based system.

``mkdir -p demoCA/newcerts touch demoCA/index.txt echo 1001 > demoCA/serial``
Create your private key ...

``openssl genrsa -des3 -out jkrueger.key``

... and the certificate request ...

``openssl req -new -key jkrueger.key -out jkrueger.req``

-  Country Name: *DE*
-  State or Province Name: *Nordrhein-Westfalen*
-  Organization Name : *Universitaet Bielefeld*

... and sign with our previously generated server certificate.

``openssl ca -cert server.cert.crt -keyfile server.cert.key -out jkrueger.crt -in jkrueger.req``

HAProxy configuration
~~~~~~~~~~~~~~~~~~~~~

::

    ...
    bind YOUR_SERVER_IP:443 ssl crt YOUR_SERVER_CERT ca-file YOUR_SELF_SIGNED_SERVER_CERT verify optional
      http-request set-header X-SSL-Client-Verify    %[ssl_c_verify]
      http-request set-header X-SSL-Client-DN        %{+Q}[ssl_c_s_dn]
      http-request set-header X-SSL-Client-CN        %{+Q}[ssl_c_s_dn(cn)]
      http-request set-header X-SSL-Issuer           %{+Q}[ssl_c_i_dn]
      http-request set-header X-SSL-Client-NotBefore %{+Q}[ssl_c_notbefore]
      http-request set-header X-SSL-Client-NotAfter  %{+Q}[ssl_c_notafter]
    ...

With http-request set-header directive haproxy add (and possible
overwrite) some additional http header for cleint

Example request using curl
~~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to use our client certificate is to pass a combined key
- certifcate file in pem format to curl. Generating a combined key -
certificate file is quite simple, just cat the key and the certificate
into one file:

::

    cat jkrueger.key jkrueger.crt > jkrueger.pem

The curl request is then straightforward ...

::

    curl --cert jkrueger.pem https://YOUR_SERVER
