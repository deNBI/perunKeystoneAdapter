#!/usr/bin/env python
import argparse
import logging
import shutil
import tarfile
import tempfile

from denbi.perun.endpoint import Endpoint
from denbi.perun.keystone import KeyStone

logging.basicConfig(level=logging.WARN)


def process_tarball(tarball_path, read_only=False, target_domain_name='elixir',
                    default_role='user', nested=False):
    directory = tempfile.mkdtemp()

    # extract tar file
    tar = tarfile.open(tarball_path, "r:gz")
    tar.extractall(path=directory)
    tar.close()

    # import into keystone
    keystone = KeyStone(default_role=default_role, create_default_role=True,
                        support_quotas=False, target_domain_name=target_domain_name,
                        read_only=read_only, nested=nested)
    endpoint = Endpoint(keystone=keystone, mode="denbi_portal_compute_center",
                        support_quotas=False)
    endpoint.import_data(directory + '/users.scim', directory + '/groups.scim')

    # Cleanup
    shutil.rmtree(directory)


def main():
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
    args = parser.parse_args()

    # Defaults to WARN, with every added -v it goes to INFO then DEBUG
    log_level = max(3 - args.verbose_count, 1) * 10
    logging.getLogger('denbi').setLevel(log_level)

    process_tarball(args.tarball.name, read_only=args.read_only,
                    target_domain_name=args.domain,
                    default_role=args.role, nested=args.nested)


if __name__ == '__main__':
    main()
