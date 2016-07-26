#!/usr/bin/env python

import argparse
import ipaddress
import json
import os
import requests
import sys
import time

from os import environ as env

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import keystoneclient.v2_0.client as ksclient
import heatclient.client as heatclient

from keystoneclient.auth.identity import v2
from keystoneclient import session

def create():
    parser = argparse.ArgumentParser(description="Creates a stack from a HOT template")
    parser.add_argument("name", help="Name of the stack to create.", type=str)
    parser.add_argument("imagename", help="Name of the image to use for the stack", type=str)
    parser.add_argument("yaml", help="HOT template for the stack.", type=str)
    parser.add_argument("keyname", help="Name of the keypair to use.", type=str)
    args = parser.parse_args()

    if not os.path.isfile(args.yaml):
        print "Template '{0}' does not exist!".format(args.yaml)
        sys.exit(-1)

    osauthurl    = env.get('OS_AUTH_URL', False)
    osusername   = env.get('OS_USERNAME', False)
    ospassword   = env.get('OS_PASSWORD', False)
    ostenantname = env.get('OS_TENANT_NAME', False)
    osregionname = env.get('OS_REGION_NAME', False)

    if not osauthurl:
        print "OS_AUTH_URL must be set! Did you source an openrc file?"
        sys.exit(-1)
    if not osusername:
        print "OS_USERNAME must be set! Did you source an openrc file?"
        sys.exit(-1)
    if not ospassword:
        print "OS_PASSWORD must be set! Did you source an openrc file?"
        sys.exit(-1)
    if not ostenantname:
        print "OS_TENANT_NAME must be set! Did you source an openrc file?"
        sys.exit(-1)
    if not osregionname:
        print "OS_REGION_NAME must be set! Did you source an openrc file?"
        sys.exit(-1)

    keystone = ksclient.Client(auth_url=osauthurl,
                               username=osusername,
                               password=ospassword,
                               tenant_name=ostenantname,
                               region_name=osregionname)

    auth = v2.Password(auth_url=osauthurl,
                       username=osusername,
                       password=ospassword,
                       tenant_name=ostenantname)

    sess  = session.Session(auth=auth)
    token = keystone.auth_token

    heaturl = keystone.service_catalog.get_endpoints()['orchestration'][0]['publicURL']
    heat = heatclient.Client('1', endpoint=heaturl, token=token)

    stack = None
    # Create the stack!
    with open(args.yaml, 'r') as yamlfile:
        yamldata = yamlfile.read()
        print "Creating stack '{0}'...".format(args.name)
        stack = heat.stacks.create(stack_name=args.name, template=yamldata,
                parameters={
                    "image": args.imagename,
                    "sshkeypair": args.keyname,
                })

    stackid = stack['stack']['id']
    stack = heat.stacks.get(stack_id=stackid)
