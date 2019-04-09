#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Simple Perun propagation service.

Using this service in a real world scenario makes it possibly necessary
to implement the upload function in a thread. But the 'process_tarball'
method shouldn't run parallel.
"""

import logging
import os
import shutil
import tarfile
import tempfile

from concurrent.futures import ThreadPoolExecutor

from datetime import datetime

from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone

from flask import Flask
from flask import request


app = Flask(__name__)
app.config['cleanup'] = True
app.config['keystone_read_only'] = os.environ.get('KEYSTONE_READ_ONLY', 'False').lower() == 'true'

#  configure basic logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s -%(message)s')

# logging formatter
fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s -%(message)s')

# create a FileHandler for reporting
report_ch = logging.FileHandler("report.log")
report_ch.setLevel(logging.INFO)
report_ch.setFormatter(fmt)

# configure logger for report_domain using default name
report = logging.getLogger('report')
report.setLevel(logging.INFO)
report.addHandler(report_ch)

# create a FileHandler for logging
log_ch = logging.FileHandler("pka.log")
log_ch.setLevel(logging.Error)
log_ch.setFormatter(fmt)

# set log level for logger_domain using default name
denbi = logging.getLogger('denbi')
denbi.setLevel(logging.ERROR)
denbi.addHandler(log_ch)


executor = ThreadPoolExecutor(max_workers=1)


def process_tarball(tarball_path, base_dir=tempfile.mkdtemp(), read_only=False, target_domain_name='elixir',
                    default_role='user', nested=False, support_quota=False, cloud_admin=True):
    """Process Perun tarball."""
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
    """Recieve a perun tarball, store it in a temporary file and process it."""

    # Create a tempfile to write the data to. delete=False because we will
    # close after writing, before processing, and this would normally cause a
    # tempfile to disappear.
    file = tempfile.NamedTemporaryFile(prefix='perun_upload', suffix='.tar.gz', delete=False)

    # store uploaded data
    file.write(request.get_data())
    file.close()

    # execute
    executor.submit(process_tarball, file.name, read_only=app.config.get('KEYSTONE_READ_ONLY', False),
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
