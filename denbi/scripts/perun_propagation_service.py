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

import json
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

# check if config file named 'pka.json' is found
if os.path.isfile("/etc/pka.json"):
    report.info(f"Load Configuration from file '/etc/pka.json'")
    app.config.from_file(os.getcwd() + "/etc/pka.json", load=json.load)
elif os.path.isfile(os.getcwd()+"/pka.json"):
    report.info(f"Load Configuration from file '{os.getcwd()}/pka.json'")
    app.config.from_file(os.getcwd() + "/pka.json", load=json.load)
else:
    report.info("Get Configuration from environment")
    app.config.from_prefixed_env("PKA")

report.info("Check CONFIG options.")

if not app.config.get('BASE_DIR', False):
    app.config['BASE_DIR'] = tempfile.mkdtemp()

if not app.config.get('LOG_DIR', False):
    app.config['LOG_DIR'] = "."

if not app.config.get('TARGET_DOMAIN_NAME', False):
    app.config['TARGET_DOMAIN_NAME'] = 'elixir'

if not app.config.get('DEFAULT_ROLE', False):
    app.config['DEFAULT_ROLE'] = 'user'

if app.config.get('SUPPORT_DEFAULT_SSH_SGRULE', False) and not app.config.get('SUPPORT_NETWORK', False):
    app.config['SUPPORT_NETWORK'] = True

if app.config.get('SUPPORT_NETWORK', False) and not app.config.get('SUPPORT_ROUTER', False):
    app.config['SUPPORT_ROUTER'] = True

if app.config.get('SUPPORT_ROUTER', False) and not app.config.get('EXTERNAL_NETWORK_ID', False):
    report.error("if 'SUPPORT_ROUTER' is enabled, 'EXTERNAL_NETWORK_ID' must be set.")
    sys.exit(4)
    
if not app.config.get('SSH_KEY_BLOCKLIST', False):
    app.config['SSH_KEY_BLOCKLIST'] = []

PKA_KEYS = ('BASE_DIR', 'KEYSTONE_READ_ONLY', 'CLEANUP',
            'TARGET_DOMAIN_NAME', 'DEFAULT_ROLE', 'NESTED',
            'ELIXIR_NAME', 'SUPPORT_QUOTAS', 'SUPPORT_ROUTER',
            'SUPPORT_NETWORK', 'SUPPORT_DEFAULT_SSH_SGRULE',
            'EXTERNAL_NETWORK_ID', 'LOG_DIR',
            'SSH_KEY_BLOCKLIST')

config_str_list = []
config_str_list.append("I'm using the following configuration:")
config_str_list.append(f"+{'-' * 32}+{'-' * 42}+")
for key in sorted(PKA_KEYS):
    config_str_list.append(f"| {key:30} | {app.config.get(key, 'False'):40} |")
config_str_list.append(f"+{'-' * 32}+{'-' * 42}+")

report.info('\n'.join(config_str_list))

# if app.config contains Openstack specific variables (starting with OS_)
# put them in an extra environment
# check if minimum set of OS keys is provided.
local_environment = {}

necessary_keys = ["OS_AUTH_URL",
                  "OS_USERNAME",
                  "OS_USER_DOMAIN_NAME",
                  "OS_PROJECT_NAME",
                  "OS_PASSWORD"]
for key in app.config.keys():
    if key.startswith("OS_"):
        local_environment[key] = app.config.get(key)
        if key in necessary_keys:
            necessary_keys.remove(key)

if not local_environment:
    local_environment = None
else:
    if necessary_keys:
        report.error(f"{','.join(necessary_keys)} is/are mandatory and is/are missing in configuration or environment.")
        sys.exit(4)

# create a FileHandler for logging
log_ch = logging.FileHandler(app.config.get("LOG_DIR", ".") + "/pka.log")
log_ch.setLevel(logging.INFO)
log_ch.setFormatter(fmt)

# configure 'denbi' logger
denbi = logging.getLogger('denbi')
denbi.setLevel(logging.INFO)
denbi.addHandler(log_ch)

# Create thread executor
executor = ThreadPoolExecutor(max_workers=1)


def strtobool(val):
    """Convert a string representation of truth to true or false .
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = str(val).lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


def process_tarball(tarball_path,
                    base_dir=tempfile.mkdtemp(),
                    read_only=False,
                    cleanup=False,
                    target_domain_name='elixir',
                    default_role='user',
                    nested=False,
                    support_elixir_name=False,
                    support_quotas=False,
                    support_router=False,
                    external_network_id='',
                    support_network=False,
                    support_default_ssh_sgrule=False,
                    ssh_key_blocklist=None):
    """
    Process Perun propagated tarball.
    """
    if ssh_key_blocklist is None:
        ssh_key_blocklist = []
    d = datetime.today()
    dir = f"{base_dir}/{d.year}_{d.month}_{d.day}_{d.hour}:{d.minute}:{d.second}.{d.microsecond}"
    os.mkdir(dir)

    report.info("Processing data uploaded by Perun: %s" % tarball_path)

    # extract tar file
    tar = tarfile.open(tarball_path, "r:gz")
    tar.extractall(path=dir)
    tar.close()

    # import into keystone
    keystone = KeyStone(default_role=default_role,
                        create_default_role=True,
                        target_domain_name=target_domain_name,
                        read_only=read_only,
                        nested=nested,
                        environ=local_environment)
    endpoint = Endpoint(keystone=keystone,
                        mode="denbi_portal_compute_center",
                        support_elixir_name=support_elixir_name,
                        support_quotas=support_quotas,
                        support_router=support_router,
                        external_network_id=external_network_id,
                        support_network=support_network,
                        support_default_ssh_sgrule=support_default_ssh_sgrule,
                        ssh_key_blocklist=ssh_key_blocklist
                        )
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
    result = executor.submit(process_tarball,
                             file.name,
                             base_dir=app.config.get('BASE_DIR'),
                             read_only=strtobool(app.config.get('KEYSTONE_READ_ONLY', "False")),
                             cleanup=strtobool(app.config.get('CLEANUP', "False")),
                             target_domain_name=app.config.get('TARGET_DOMAIN_NAME'),
                             default_role=app.config.get('DEFAULT_ROLE'),
                             nested=strtobool(app.config.get('NESTED', "False")),
                             support_elixir_name=strtobool(app.config.get('ELIXIR_NAME', "False")),
                             support_quotas=strtobool(app.config.get('SUPPORT_QUOTA', "False")),
                             support_router=strtobool(app.config.get('SUPPORT_ROUTER', "False")),
                             external_network_id=app.config.get('EXTERNAL_NETWORK_ID'),
                             support_network=strtobool(app.config.get('SUPPORT_NETWORK', "False")),
                             support_default_ssh_sgrule=strtobool(app.config.get('SUPPORT_DEFAULT_SSH_SGRULE', "False")),
                             ssh_blocklist=app.config.get('SSH_KEY_BLOCKLIST', None)
                             )

    # if task fails with an exception, the thread pool catches the exception,
    # stores it, then re-raises it when we call the result() function.
    try:
        result.result()
    except Exception:
        traceback.print_exc()

    if app.config.get('CLEANUP', False):
        os.unlink(file)

    return ""


if __name__ == "__main__":
    app.run(host=app.config['HOST'], port=app.config['PORT'])
