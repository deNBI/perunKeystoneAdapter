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
import sys
import tarfile
import tempfile

from concurrent.futures import ThreadPoolExecutor

from datetime import datetime

from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone

from flask import Flask
from flask import request

import traceback

# logging formatter
fmt = logging.Formatter('[%(asctime)s] - (%(name)s/%(levelname)s) - %(message)s')

# create a StreamHandler for reporting
report_ch = logging.StreamHandler(sys.stdout)
report_ch.setLevel(logging.INFO)
report_ch.setFormatter(fmt)

# configure 'report' logger
report = logging.getLogger('report')
report.setLevel(logging.INFO)
report.addHandler(report_ch)

app = Flask(__name__)

# Load configuration from file
if "CONFIG_PATH" not in os.environ:
    os.environ['CONFIG_PATH'] = os.getcwd()+"/perun_propagation_service.cfg"


if os.path.exists(os.environ['CONFIG_PATH']):
    report.info(f"Loading configuration from {os.environ['CONFIG_PATH']}.")
    app.config.from_pyfile(os.environ['CONFIG_PATH'])
else:
    report.info(f"Configuration file {os.environ['CONFIG_PATH']} not found. Using defaults.")

# create a FileHandler for logging
log_ch = logging.FileHandler(app.config.get("LOG_DIR","")+"pka.log")
log_ch.setLevel(logging.INFO)
log_ch.setFormatter(fmt)

# configure 'denbi' logger
denbi = logging.getLogger('denbi')
denbi.setLevel(logging.INFO)
denbi.addHandler(log_ch)

# Create thread executor
executor = ThreadPoolExecutor(max_workers=1)


def process_tarball(tarball_path, base_dir=tempfile.mkdtemp(), read_only=False, target_domain_name='elixir',
                    default_role='user', nested=False, support_quota=False, cloud_admin=True, cleanup=False):
    """Process Perun tarball."""
    d = datetime.today()
    #dir = base_dir + "/" + str(d.year) + "_" + str(d.month) + "_" + str(d.day) + "-" + str(d.hour) + ":" + str(d.minute) + ":" + str(d.second) + "." + str(d.microsecond)
    dir = f"{base_dir}/{d.year}_{d.month}_{d.day}_{d.hour}:{d.minute}:{d.second}.{d.microsecond}"
    os.mkdir(dir)

    report.info("Processing data uploaded by Perun: %s" % tarball_path)

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
    report.info("Finished processing %s" % tarball_path)

    # Cleanup
    if cleanup:
        shutil.rmtree(dir)


@app.route("/upload", methods=['PUT'])
def upload():
    """Receive a perun tarball, store it in a temporary file and process it."""

    # Create a tempfile to write the data to. delete=False because we will
    # close after writing, before processing, and this would normally cause a
    # tempfile to disappear.
    file = tempfile.NamedTemporaryFile(prefix='perun_upload', suffix='.tar.gz', delete=False)

    # store uploaded data
    file.write(request.get_data())
    file.close()

    # execute task
    result = executor.submit(process_tarball, file.name, read_only=app.config.get('KEYSTONE_READ_ONLY', False),
                    target_domain_name=app.config.get('TARGET_DOMAIN_NAME', 'elixir'),
                    default_role=app.config.get('DEFAULT_ROLE', 'user'),
                    nested=app.config.get('NESTED', False),
                    cloud_admin=app.config.get('CLOUD_ADMIN', True),
                    base_dir=app.config.get('BASE_DIR', tempfile.mkdtemp()),
                    support_quota=app.config.get('SUPPORT_QUOTA', False),
                    cleanup=app.config.get('CLEANUP',False))

    # if task fails with an exception, the thread pool catches the exception,
    # stores it, then re-raises it when we call the result() function.
    try:
        result.result()
    except Exception as e:
        traceback.print_exc()

    if app.config.get('CLEANUP', False):
        os.unlink(file)

    return ""

if __name__ == "__main__":
    app.run(host=app.config['HOST'], port=app.config['PORT'])
