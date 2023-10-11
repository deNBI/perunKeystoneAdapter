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
                    default_role='user', nested=False,
                    support_elixir_name=False,
                    support_quotas=False,
                    support_router=False,
                    external_network_id='',
                    support_network=False,
                    support_default_ssh_sgrule=False):
    """Process a propagated tarball.

    Should contain at least a user.scim and group.scim file in SCIM format.
    """
    directory = tempfile.mkdtemp()

    # extract tar file
    tar = tarfile.open(tarball_path, "r:gz")
    tar.extractall(path=directory)
    tar.close()


    # import into keystone
    keystone = KeyStone(default_role=default_role,
                        create_default_role=True,
                        target_domain_name=target_domain_name,
                        read_only=read_only,
                        nested=nested)
    endpoint = Endpoint(keystone=keystone,
                        mode="denbi_portal_compute_center",
                        support_elixir_name=support_elixir_name,
                        support_quotas=support_quotas,
                        support_router=support_router,
                        external_network_id=external_network_id,
                        support_network=support_network,
                        support_default_ssh_sgrule=support_default_ssh_sgrule
                        )
    endpoint.import_data(directory + '/users.scim', directory + '/groups.scim')

    # Cleanup
    shutil.rmtree(directory)


def main():
    """Main method."""
    parser = argparse.ArgumentParser(description='Process perun tarball')
    parser.add_argument('tarball', type=argparse.FileType('r'), help="Input tarball from perun")
    parser.add_argument('--read-only', action='store_true', default=False,
                        help="Do not make any modifications to keystone")
    parser.add_argument('--domain', default='elixir',
                        help="Domain to create users and projects in, defaults to 'elixir'")
    parser.add_argument('--role', default='user',
                        help="Default role to assign to new users, defaults to 'user'")
    parser.add_argument('--elixir_name',action="store_true", default=False,
                        help="Support Key 'login-namespace:elixir'. This information is normally not propagated by "
                             "default.")
    parser.add_argument("-v", "--verbose", dest="verbose_count",
                        action="count", default=0, help="increases log verbosity for each occurrence.")
    parser.add_argument("--nested", action="store_true", default=False,
                        help="use nested project instead of cloud/domain admin")
    parser.add_argument("--quotas", action="store_true", default=False,
                        help="set quotas for projects")
    parser.add_argument("--router", action="store_true", default=False,
                        help="create a router for created project")
    parser.add_argument("--external_network_id",
                        help="id of external network used for floating ips, needed by --router")
    parser.add_argument("--network", action="store_true", default=False,
                        help="create a network for created project, sets --router")
    parser.add_argument("--ssh_sgrule", action="store_true", default=False,
                        help="create a default ssh rule for default security group, sets --network")
    args = parser.parse_args()

    # Defaults to WARN, with every added -v it goes to INFO then DEBUG
    log_level = max(3 - args.verbose_count, 1) * 10
    logging.getLogger('denbi').setLevel(log_level)

    # Check and set dependencies
    if args.ssh_sgrule:
        args.network=True
    if args.network:
        args.router=True
    if args.router and not args.external_network_id:
        print("External network id is mandatory if router is set.")
        exit(1)


    process_tarball(args.tarball.name, read_only=args.read_only,
                    target_domain_name=args.domain,
                    default_role=args.role, nested=args.nested,
                    support_quotas=args.quotas,
                    support_router=args.router,
                    external_network_id=args.external_network_id,
                    support_network=args.network,
                    support_default_ssh_sgrule=args.ssh_sgrule)


if __name__ == '__main__':
    main()
