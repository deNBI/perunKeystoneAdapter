#!/usr/bin/env python
import tarfile
import tempfile

from flask import Flask
from flask import request
from denbi.bielefeld.perun.endpoint import Endpoint
from denbi.bielefeld.perun.keystone import KeyStone
from threading import Thread

app = Flask(__name__)


def process_tarball(tarball_path):
    # TODO(hxr): deduplicate
    directory = tempfile.TemporaryDirectory()
    app.logging.info("Processing data uploaded by Perun: %s", tarball_path)

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
    app.logging.info("Finished processing %s", tarball_path)

    # Cleanup
    directory.cleanup()


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
    t = Thread(target=_perun_propagation, args=(file,))
    t.start()

    # return immediately
    return ""


def _perun_propagation(file):
    process_tarball(file)
    # TODO: cleanup uploaded tarballs?


def main():
    app.run()


if __name__ == "__main__":
    main()
