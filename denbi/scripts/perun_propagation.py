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

"""Process propagated user/project as 'perun tarball'."""

import argparse
import logging
import shutil
import tarfile
import tempfile

from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone


logging.basicConfig(level=logging.WARN)


def process_tarball(tarball_path, read_only=False, target_domain_name='elixir',
                    default_role='user', nested=False, support_quotas=False):
    """Process a propagated tarball.

    Should contain at least a user.scim and group.scim file in SCIM format.
    """
    directory = tempfile.mkdtemp()

    # extract tar file
    tar = tarfile.open(tarball_path, "r:gz")
    tar.extractall(path=directory)
    tar.close()

    # import into keystone
    keystone = KeyStone(default_role=default_role, create_default_role=True,
                        target_domain_name=target_domain_name,
                        read_only=read_only, nested=nested)
    endpoint = Endpoint(keystone=keystone, mode="denbi_portal_compute_center",
                        support_quotas=support_quotas)
    endpoint.import_data(directory + '/users.scim', directory + '/groups.scim')

    # Cleanup
    shutil.rmtree(directory)


def main():
    """Main method."""
    parser = argparse.ArgumentParser(description='Process perun tarball')
    parser.add_argument('tarball', type=argparse.FileType('r'), help="Input tarball from perun")
    parser.add_argument('--read-only', action='store_true', help="Do not make any modifications to keystone")
    parser.add_argument('--domain', default='elixir',
                        help="Domain to create users and projects in, defaults to 'elixir'")
    parser.add_argument('--role', default='user',
                        help="Defaut role to assign to new users, defaults to 'user'")
    parser.add_argument("-v", "--verbose", dest="verbose_count",
                        action="count", default=0, help="increases log verbosity for each occurence.")
    parser.add_argument("-n", "--nested", action="store_true", default=False,
                        help="use nested project instead of cloud/domain admin")
    parser.add_argument("-q", "--quotas", action="store_true", default=False,
                        help="set quotas for projects")
    args = parser.parse_args()

    # Defaults to WARN, with every added -v it goes to INFO then DEBUG
    log_level = max(3 - args.verbose_count, 1) * 10
    logging.getLogger('denbi').setLevel(log_level)

    process_tarball(args.tarball.name, read_only=args.read_only,
                    target_domain_name=args.domain,
                    default_role=args.role, nested=args.nested,
                    support_quotas=args.quotas)


if __name__ == '__main__':
    main()
