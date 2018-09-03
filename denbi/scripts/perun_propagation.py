#!/usr/bin/env python
import tarfile
import argparse
import tempfile

from denbi.bielefeld.perun.endpoint import Endpoint
from denbi.bielefeld.perun.keystone import KeyStone


def process_tarball(tarball_path):
    directory = tempfile.TemporaryDirectory()

    # extract tar file
    tar = tarfile.open(tarball_path, "r:gz")
    tar.extractall(path=directory)
    tar.close()

    # import into keystone
    keystone = KeyStone(default_role="user", create_default_role=True,
                        support_quotas=False, target_domain_name='elixir')
    endpoint = Endpoint(keystone=keystone, mode="denbi_portal_compute_center",
                        support_quotas=False)
    endpoint.import_data(directory + '/users.scim', directory + '/groups.scim')

    # Cleanup
    directory.cleanup()


def main():
    parser = argparse.ArgumentParser(description='Process perun tarball')
    parser.add_argument('tarball', type=argparse.FileType('r'), help="Input tarball from perun")
    args = parser.parse_args()

    process_tarball(args.tarball)


if __name__ == '__main__':
    main()
