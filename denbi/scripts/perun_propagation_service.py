#!/usr/bin/env python
import logging
import os
import shutil
import tarfile
import tempfile

from datetime import datetime
from flask import Flask
from flask import request
from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone


app = Flask(__name__)
app.config['cleanup'] = True
app.config['keystone_read_only'] = os.environ.get('KEYSTONE_READ_ONLY', 'False').lower() == 'true'
logging.basicConfig(level=getattr(logging, os.environ.get('PERUN_LOG_LEVEL', 'WARN')))


def process_tarball(tarball_path, base_dir=tempfile.mkdtemp(), read_only=False, target_domain_name='elixir',
                    default_role='user', nested=False, support_quota=False, cloud_admin=True):
    # TODO(hxr): deduplicate
    d = datetime.today()
    dir = base_dir + "/" + str(d.year) + "_" + str(d.month) + "_" + str(d.day) + "-" + str(d.hour) + ":" + str(d.minute) + ":" + str(d.second) + "." + str(d.microsecond)
    os.mkdir(dir)

    logging.info("Processing data uploaded by Perun: %s" % tarball_path)

    # extract tar file
    tar = tarfile.open(tarball_path, "r:gz")
    tar.extractall(path=dir)
    tar.close()

    # import into keystone
    keystone = KeyStone(environ=app.config, default_role=default_role, create_default_role=True,
                        target_domain_name=target_domain_name,
                        read_only=read_only, nested=nested, cloud_admin=cloud_admin)

    endpoint = Endpoint(keystone=keystone, mode="denbi_portal_compute_center",
                        support_quotas=support_quota)
    endpoint.import_data(dir + '/users.scim', dir + '/groups.scim')
    logging.info("Finished processing %s" % tarball_path)

    # Cleanup
    shutil.rmtree(dir)


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

    process_tarball(file.name, read_only=app.config.get('KEYSTONE_READ_ONLY', False),
                    target_domain_name=app.config.get('TARGET_DOMAIN_NAME', 'elixir'),
                    default_role=app.config.get('DEFAULT_ROLE', 'user'),
                    nested=app.config.get('NESTED', False),
                    cloud_admin=app.config.get('CLOUD_ADMIN', True),
                    base_dir=app.config.get('BASE_DIR', tempfile.mkdtemp()),
                    support_quota=app.config.get('SUPPORT_QUOTA', False))

    if app.config.get('CLEANUP', False):
        os.unlink(file)



    return ""


app.config.from_envvar('CONFIG_PATH')
if __name__ == "__main__":
    app.run(host=app.config['HOST'], port=app.config['PORT'])
