#!/usr/bin/env python
import argparse
import logging
import os
import shutil
import tarfile
import tempfile

from flask import Flask
from flask import request
from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone
from threading import Thread

app = Flask(__name__)
app.config['cleanup'] = True
app.config['keystone_read_only'] = os.environ.get('KEYSTONE_READ_ONLY', 'False').lower() == 'true'
logging.basicConfig(level=getattr(logging, os.environ.get('PERUN_LOG_LEVEL', 'WARN')))


def process_tarball(tarball_path, read_only=False, target_domain_name='elixir',
                    default_role='user'):
    # TODO(hxr): deduplicate
    directory = tempfile.mkdtemp()
    logging.info("Processing data uploaded by Perun: %s" % tarball_path)

    # extract tar file
    tar = tarfile.open(tarball_path, "r:gz")
    tar.extractall(path=directory)
    tar.close()

    # import into keystone
    keystone = KeyStone(default_role=default_role, create_default_role=True,
                        support_quotas=False, target_domain_name=target_domain_name, read_only=read_only)
    endpoint = Endpoint(keystone=keystone, mode="denbi_portal_compute_center",
                        support_quotas=False)
    endpoint.import_data(directory + '/users.scim', directory + '/groups.scim')
    logging.info("Finished processing %s" % tarball_path)

    # Cleanup
    shutil.rmtree(directory)


@app.route("/upload", methods=['PUT'])
def upload():
    # Create a tempfile to write the data to. delete=False because we will
    # close after writing, before processing, and this would normally cause a
    # tempfile to disappear.
    file = tempfile.NamedTemporaryFile(prefix='perun_upload', suffix='.tar.gz', delete=False)

    # TODO: buffered writing
    # store uploaded data
    file.write(request.get_data())
    file.close()

    # parse propagated data in separate thread
    t = Thread(target=_perun_propagation, args=(file.name,),
               kwargs={'read_only': app.config.get('keystone_read_only', False),
                       'target_domain_name': app.confg.get('target_domain_name', 'elixir'),
                       'default_role': app.config.get('default_role', 'user')})
    t.start()

    # return immediately
    return ""


def _perun_propagation(file, read_only=False, target_domain_name="elixir"):
    process_tarball(file, read_only=read_only, target_domain_name=target_domain_name)

    if app.config['cleanup']:
        os.unlink(file)


def main():
    parser = argparse.ArgumentParser(description='Run perunKeystoneAdapter service')
    parser.add_argument('--host', default='0.0.0.0', help="Address to bind to")
    parser.add_argument('--port', type=int, default=5000, help="Port to bind to")
    parser.add_argument('--read-only', action='store_true', help="Do not make any modifications to keystone")
    parser.add_argument('--domain', default='elixir',
                        help="Domain to create users and projects in, defaults to 'elixir'")
    parser.add_argument('--role', default='user',
                        help="Defaut role to assign to new users, defaults to 'user'")
    args = parser.parse_args()

    app.config['keystone_read_only'] = args.read_only
    app.config['target_domain_name'] = args.domain
    app.config['default_role'] = args.role

    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
