#!/usr/bin/env python3
import argparse

from denbi import scripts


def main():
    parser = argparse.ArgumentParser(description='Set user flag')
    parser.add_argument('user_id')
    parser.add_argument('flag')
    args = parser.parse_args()

    keystone = scripts.obtain_keystone()

    # Update the user
    keystone.users.update(args.user_id, flag=args.flag)


if __name__ == '__main__':
    main()
