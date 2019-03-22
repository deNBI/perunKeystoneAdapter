#!/usr/bin/env python3

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

import argparse

from denbi import scripts


def main():
    parser = argparse.ArgumentParser(description='Set user flag')
    parser.add_argument('user_id')
    parser.add_argument('flag')
    args = parser.parse_args()

    keystone = scripts.obtain_keystone()

    # Update the user
    # TODO(hxr): support setting perun_id as well
    keystone.users.update(args.user_id, flag=args.flag)


if __name__ == '__main__':
    main()
