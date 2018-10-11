#!/usr/bin/env python3
import argparse

from denbi import scripts


def main():
    parser = argparse.ArgumentParser(description='Set project flag')
    parser.add_argument('project_id')
    parser.add_argument('flag')
    args = parser.parse_args()

    keystone = scripts.obtain_keystone()

    # Update the project
    keystone.projects.update(args.project_id, flag=args.flag)


if __name__ == '__main__':
    main()
