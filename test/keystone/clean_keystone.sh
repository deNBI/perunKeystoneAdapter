#!/usr/bin/env bash
echo    "#######################################################################"
echo    "##                              Attention!                           ##"
echo    "## ----------------------------------------------------------------- ##"
echo    "## work on Keystone located at ${OS_AUTH_URL} ##"
echo    "#######################################################################"
read -p "Do you really want clean the keystone database beside the admin user|project (y/n) ? " choice
case ${choice} in
    y|Y ) echo "Wait a moment ..."; \
          openstack user list -f value | grep -v admin | cut -f 1  -d " " | xargs openstack user delete; \
          openstack project list -f value | grep -v admin | cut -f 1  -d " " | xargs openstack project delete; \
          echo "... cleaned";;
esac

