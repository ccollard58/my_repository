#!/usr/bin/env python

import argparse
import ipaddress
import json
import os
import requests
import sys
import yaml

import sshtools

from os import environ as env
from xml.etree import ElementTree as ET

def dump(data):
    return yaml.safe_dump(data, default_flow_style=False)

import keystoneclient.v2_0.client as ksclient
import heatclient.client as heatclient
import novaclient.client as novaclient
import neutronclient.neutron.client as neutronclient

from keystoneclient.auth.identity import v2
from keystoneclient import session

parser = argparse.ArgumentParser(description="Generates a configuration XML from a stack.")
parser.add_argument("name", help="Name of the stack to configure.", type=str)
parser.add_argument("keyfile", help="Path to SSH key to use for authentication.", type=str)
args = parser.parse_args()

if not os.path.isfile(args.keyfile):
    print "SSH key '{0}' does not exist!".format(args.keyfile)
    sys.exit(-1)

keystone = ksclient.Client(auth_url=env['OS_AUTH_URL'],
                           username=env['OS_USERNAME'],
                           password=env['OS_PASSWORD'],
                           tenant_name=env['OS_TENANT_NAME'],
                           region_name=env['OS_REGION_NAME'])

auth = v2.Password(auth_url=env['OS_AUTH_URL'],
                   username=env['OS_USERNAME'],
                   password=env['OS_PASSWORD'],
                   tenant_name=env['OS_TENANT_NAME'])

sess  = session.Session(auth=auth)
token = keystone.auth_token

heaturl = "http://ccp1.us.oracle.com:8004/v1/{0}".format(env['OS_TENANT_ID'])
heat = heatclient.Client('1', endpoint=heaturl, token=token)
nova = novaclient.Client('2.1', session=sess)
neutron = neutronclient.Client('2.0', session=sess)

# allnets    = neutron.list_networks()
# allservers = nova.servers.list()
servers      = {}
nets         = {}

# import code
# code.InteractiveConsole(locals=globals()).interact()
stack = heat.stacks.get(args.name)
floatingip = None

for output in stack.outputs:
    if output['output_key'] == 'floatingip':
        floatingip = output['output_value']

resources = heat.resources.list(args.name)

configtree = ET.Element('configuration')

hostmap = {}

config = {
    'configHostname': [],
    'networkElement': [],
    'network': [],
    'servicePath': [],
    'server': [],
    'networkDevice': [],
    'serverGroup': [],
    'vip': [],
}

# print "Fetching resources..."
vlanId = 2

for r in resources:
    if r.resource_type == "OS::Nova::Server":
        meta = heat.resources.metadata(args.name, r.resource_name)
        server = nova.servers.get(r.physical_resource_id).to_dict()
        server['awmeta'] = meta
        servers[server['name']] = server
        if meta['noa']:
            elem = ET.SubElement(configtree, 'configHostname')
            ET.SubElement(elem, 'hostname').text = server['name']

            for ne in meta['appworks']['networkelements']:
                elem = ET.SubElement(configtree, 'networkElement')
                ET.SubElement(elem, 'name').text = ne['name']

            for sg in meta['appworks']['servergroups']:
                elem = ET.SubElement(configtree, 'serverGroup')
                ET.SubElement(elem, 'name').text = sg['name']
                ET.SubElement(elem, 'level').text = sg['level']
                ET.SubElement(elem, 'parentSgName').text = sg['parentSgName']
                ET.SubElement(elem, 'functionName').text = sg['functionName']
                ET.SubElement(elem, 'numWanRepConn').text = str(sg['numWanRepConn'])

    elif r.resource_type == "OS::Neutron::Net":
        meta = heat.resources.metadata(args.name, r.resource_name)
        net = neutron.show_network(r.physical_resource_id)['network']
        net['awmeta'] = meta
        net['awmeta']['vlanId'] = vlanId
        vlanId += 1

        # Only 1 subnet per network for now
        net['subnet'] = neutron.show_subnet(net['subnets'][0])['subnet']
        nets[net['name']] = net


for servername in servers:
    server = servers[servername]
    out = ET.SubElement(configtree, 'server')

    ET.SubElement(out, 'hostname').text = servername
    ET.SubElement(out, 'networkElementName').text = server['awmeta']['neName']
    ET.SubElement(out, 'serverGroupName').text = server['awmeta']['sgName']
    ET.SubElement(out, 'profileName').text = 'UDR VMware'
    if 'haRolePref' in server['awmeta']:
        ET.SubElement(out, 'haRolePref').text = server['awmeta']['haRolePref']
    ET.SubElement(out, 'location').text = 'OpenStack'
    ET.SubElement(out, 'role').text = server['awmeta']['role']
    ET.SubElement(out, 'systemId').text = 'BREAKFAST'

    ntp = ET.SubElement(out, 'ntpServers')
    ntp = ET.SubElement(ntp, 'ntpServer')
    ET.SubElement(ntp, 'ipAddress').text = '10.75.137.245'
    ET.SubElement(ntp, 'prefer').text = 'yes'

    for netname in server['addresses']:
        net = nets[netname]
        interfaces = server['addresses'][netname]

        devout = ET.SubElement(configtree, 'networkDevice')

        if net['subnet']['gateway_ip']:
            ET.SubElement(devout, 'port').text = 'eth0'
        else:
            ET.SubElement(devout, 'port').text = 'eth1'

        ET.SubElement(devout, 'type').text = 'Ethernet'
        ET.SubElement(devout, 'hostname').text = servername

        for interface in interfaces:
            if interface['OS-EXT-IPS:type'] == 'fixed':
                addr = interface['addr']
                break

        intf = ET.SubElement(devout, 'interfaces')
        intf = ET.SubElement(intf, 'interface')
        ET.SubElement(intf, 'ipAddress').text = addr
        ET.SubElement(intf, 'networkName').text = net['awmeta']['name']

        opts = ET.SubElement(devout, 'options')
        ET.SubElement(opts, 'onboot').text = 'yes'
        ET.SubElement(opts, 'bootProto').text = 'none'

        if net['subnet']['gateway_ip']:
            hostmap[servername] = addr
            if server['awmeta']['noa']:
                noaip = addr
                noahostname = servername

for netname in nets:
    net = nets[netname]

    out = ET.SubElement(configtree, 'network')

    ET.SubElement(out, 'name').text = net['awmeta']['name']
    ET.SubElement(out, 'neName').text = net['awmeta']['neName']
    ET.SubElement(out, 'vlanId').text = str(net['awmeta']['vlanId'])

    networkAddr = ipaddress.ip_network(net['subnet']['cidr'])

    ET.SubElement(out, 'ipAddress').text = str(networkAddr.network_address)
    ET.SubElement(out, 'subnetMask').text = str(networkAddr.netmask)

    gateway = net['subnet']['gateway_ip']

    if gateway == None:
        ET.SubElement(out, 'isDefault').text = 'false'
        ET.SubElement(out, 'isRoutable').text = 'false'
    else:
        ET.SubElement(out, 'gatewayAddress').text = gateway
        ET.SubElement(out, 'isDefault').text = 'true'
        ET.SubElement(out, 'isRoutable').text = 'true'

    ET.SubElement(out, 'locked').text = 'true'

for s in ['Replication', 'OAM', 'Signaling']:
    svc = ET.SubElement(configtree, 'servicePath')
    ET.SubElement(svc, 'name').text = s
    ET.SubElement(svc, 'intraSitePath').text = 'LAN'
    ET.SubElement(svc, 'interSitePath').text = 'WAN'

xmlstring = ET.tostring(configtree)
with open("{0}.xml".format(args.name), 'w') as f:
    f.write(xmlstring)

hoststr = ""

for host in hostmap:
    hoststr += "'{0}': '{1}',\n".format(host, hostmap[host])

with open('bootstrap.py.tmpl', 'r') as f:
    script = f.read().replace("$$NOAIP$$", noaip).replace("$$HOSTS$$", hoststr)

with open("{0}.py".format(args.name), 'w') as f:
    f.write(script)


def getToken(server):
    print "Fetching token from {0}...".format(server)

    url = "https://{0}/mmi/alexa/v1.0/auth/tokens".format(server)
    credentials = {"username":"guiadmin", "password":"tekware"}

    r = requests.post(url, verify=False, data=credentials)
    return r.json()['data']['token']

url = "https://{0}/mmi/alexa/v1.0/bulk/configurator".format(floatingip)
print "Configuring NOA..."

# Actually send the configurator request
token = getToken(floatingip)
headers = {"X-Auth-Token": token}
resp = requests.post(url, verify=False, data=xmlstring, headers=headers)

try:
    r = resp.json()

    for message in r['messages']:
        print message
except Exception as ex:
    print ex

sshtools.putFile(floatingip, "{0}.py".format(args.name), "/tmp/bootstrap.py", "admusr", args.keyfile)

os.unlink("{0}.xml".format(args.name))
os.unlink("{0}.py".format(args.name))

sshtools.runCommand(floatingip, "python /tmp/bootstrap.py", "admusr", args.keyfile, printoutput=True)
