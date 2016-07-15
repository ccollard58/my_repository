#!/usr/bin/env python

import argparse
import ipaddress
import json
import os
import requests
import sys
import time
import yaml

import sshtools

from os import environ as env
from xml.etree import ElementTree as ET

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import keystoneclient.v2_0.client as ksclient
import heatclient.client as heatclient
import novaclient.client as novaclient
import neutronclient.neutron.client as neutronclient

from keystoneclient.auth.identity import v2
from keystoneclient import session

def configure():
    parser = argparse.ArgumentParser(description="Configures a stack created using stackcreate.py")
    parser.add_argument("stackname", help="Name of the stack to configure.", type=str)
    parser.add_argument("keyfile", help="Path to SSH key to use for authentication.", type=str)
    parser.add_argument("-g", "--generate_only", help="Generate XML only", action="store_true")
    args = parser.parse_args()

    osauthurl    = env.get('OS_AUTH_URL', '')
    osusername   = env.get('OS_USERNAME', '')
    ospassword   = env.get('OS_PASSWORD', '')
    ostenantname = env.get('OS_TENANT_NAME', '')
    osregionname = env.get('OS_REGION_NAME', '')

    if osauthurl == '':
        print "OS_AUTH_URL must be set! Did you source an openrc file?"
        sys.exit(-1)
    if osusername == '':
        print "OS_USERNAME must be set! Did you source an openrc file?"
        sys.exit(-1)
    if ospassword == '':
        print "OS_PASSWORD must be set! Did you source an openrc file?"
        sys.exit(-1)
    if ostenantname == '':
        print "OS_TENANT_NAME must be set! Did you source an openrc file?"
        sys.exit(-1)
    if osregionname == '':
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
    nova = novaclient.Client('2.1', session=sess)
    neutron = neutronclient.Client('2.0', session=sess)

    # allnets    = neutron.list_networks()
    # allservers = nova.servers.list()
    servers      = {}
    nets         = {}

    stack = heat.stacks.get(args.stackname)

    while stack.to_dict()['stack_status'] == 'CREATE_IN_PROGRESS':
        stack = heat.stacks.get(args.stackname)
        status = stack.to_dict()['stack_status']
        print "Stack is in state '{0}'".format(status)
        if status == 'CREATE_FAILED':
            print 'Stack creation failed!'
            sys.exit(-1)
        time.sleep(3)

    # stack = heat.stacks.get(stackname)
    noafloatingip = None
    soafloatingip = None

    for output in stack.outputs:
        if output['output_key'] == 'floatingip_noa':
            noafloatingip = output['output_value']
        if output['output_key'] == 'floatingip_soa1':
            soafloatingip = output['output_value']

    resources = heat.resources.list(args.stackname)

    configtree = ET.Element('configuration')

    hostmap = {}

    # print "Fetching resources..."
    vlanId = 2

    for r in resources:
        if r.resource_type == "OS::Nova::Server":
            meta = heat.resources.metadata(args.stackname, r.resource_name)
            server = nova.servers.get(r.physical_resource_id).to_dict()
            server['awmeta'] = meta
            if not meta['extra']:
                servers[server['name']] = server
            if meta['noa']:

                # elem = ET.SubElement(configtree, 'configHostname')
                # ET.SubElement(elem, 'hostname').text = server['name']

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
            meta = heat.resources.metadata(args.stackname, r.resource_name)
            net = neutron.show_network(r.physical_resource_id)['network']
            net['awmeta'] = meta
            net['awmeta']['vlanId'] = vlanId
            vlanId += 1

            # Only 1 subnet per network for now
            net['subnet'] = neutron.show_subnet(net['subnets'][0])['subnet']
            nets[net['name']] = net

    mplist = []

    for servername in servers:
        server = servers[servername]
        out = ET.SubElement(configtree, 'server')

        ET.SubElement(out, 'hostname').text = servername
        ET.SubElement(out, 'networkElementName').text = server['awmeta']['neName']
        ET.SubElement(out, 'serverGroupName').text = server['awmeta']['sgName']
        ET.SubElement(out, 'profileName').text = server['awmeta']['hwprofile']
        if 'haRolePref' in server['awmeta']:
            ET.SubElement(out, 'haRolePref').text = server['awmeta']['haRolePref']
        ET.SubElement(out, 'location').text = 'OpenStack'
        ET.SubElement(out, 'role').text = server['awmeta']['role']
        if server['awmeta']['role'] == "roleMP":
            mplist.append(servername)

        ET.SubElement(out, 'systemId').text = 'OpenStack'

        ntp = ET.SubElement(out, 'ntpServers')
        ntp = ET.SubElement(ntp, 'ntpServer')
        ET.SubElement(ntp, 'ipAddress').text = '10.75.137.245'
        ET.SubElement(ntp, 'prefer').text = 'yes'

        for netname in server['addresses']:
            net = nets[netname]

            interfaces = server['addresses'][netname]

            devout = ET.SubElement(configtree, 'networkDevice')

            ET.SubElement(devout, 'port').text = server['awmeta']['portmap'][net['awmeta']['name']]
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
        if net['awmeta']['neName'] != "GLOBAL":
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

        if net['awmeta']['neName'] != "GLOBAL":
            ET.SubElement(out, 'locked').text = 'true'
        else:
            ET.SubElement(out, 'locked').text = 'false'

    for s in ['Replication', 'OAM', 'Signaling']:
        svc = ET.SubElement(configtree, 'servicePath')
        ET.SubElement(svc, 'name').text = s
        ET.SubElement(svc, 'intraSitePath').text = 'LAN'
        ET.SubElement(svc, 'interSitePath').text = 'WAN'

    xmlstring = ET.tostring(configtree)

    if args.generate_only:
        print xmlstring
        sys.exit(0)

    with open("/tmp/{0}.xml".format(args.stackname), 'w') as f:
        f.write(xmlstring)

    hoststr = ""
    nodestr = ""

    for host in hostmap:
        hoststr += "'{0}': '{1}',\n".format(host, hostmap[host])
    for mp in mplist:
        nodestr += "'{0}',\n".format(mp)

    scriptdir = os.path.dirname(__file__)

    with open('{0}/bootstrap.py.tmpl'.format(scriptdir), 'r') as f:
        script = f.read().replace("$$NOAIP$$", noaip).replace("$$HOSTS$$", hoststr)
    with open("/tmp/{0}.py".format(args.stackname), 'w') as f:
        f.write(script)

    with open('{0}/appinit.php.tmpl'.format(scriptdir), 'r') as f:
        script = f.read().replace("$$HOSTS$$", nodestr)
    with open("/tmp/{0}_appinit.php".format(args.stackname), 'w') as f:
        f.write(script)

    sys.stdout.write("Waiting for NOA MMI to become ready...")
    sys.stdout.flush()

    r = requests.get("https://{0}/".format(noafloatingip), verify = False)
    while r.status_code != 200:
        time.sleep(5)
        sys.stdout.write('.')
        sys.stdout.flush()

        r = requests.get("https://{0}/".format(noafloatingip), verify = False)
    print "up!"

    sshtools.putFile(noafloatingip, "{0}/soapwait.php".format(scriptdir), "/tmp/soapwait.php", "admusr", args.keyfile)
    sshtools.runCommand(noafloatingip, "php /tmp/soapwait.php", "admusr", args.keyfile, printoutput=True)

    def getToken(server):
        print "Fetching token from {0}...".format(server)

        url = "https://{0}/mmi/alexa/v1.0/auth/tokens".format(server)
        credentials = {"username":"guiadmin", "password":"tekware"}

        r = requests.post(url, verify=False, data=credentials)
        return r.json()['data']['token']

    url = "https://{0}/mmi/alexa/v1.0/bulk/configurator".format(noafloatingip)
    print "Configuring NOA using the bulk configurator MMI..."

    # Actually send the configurator request
    token = getToken(noafloatingip)
    headers = {"X-Auth-Token": token}
    resp = requests.post(url, verify=False, data=xmlstring, headers=headers)

    try:
        r = resp.json()

        for message in r['messages']:
            print message['message']
            if 'details' in message:
                for detail in message['details']:
                    print detail

    except Exception as ex:
        print ex

    sshtools.putFile(noafloatingip, "/tmp/{0}.py".format(args.stackname), "/tmp/bootstrap.py", "admusr", args.keyfile)
    sshtools.runCommand(noafloatingip, "/usr/bin/python /tmp/bootstrap.py", "admusr", args.keyfile, printoutput = True)

    os.unlink("/tmp/{0}.xml".format(args.stackname))
    os.unlink("/tmp/{0}.py".format(args.stackname))

    # Wait for everything to come up
    url = "https://{0}/mmi/alexa/v1.0/topo/servers/status".format(noafloatingip)

    # Actually send the configurator request
    headers = {"X-Auth-Token": token}

    ret = {}

    for host in hostmap:
        ret[host] = False

    elapsed = 0
    while (elapsed < 600):

        try:
            resp = requests.get(url, verify=False, headers=headers)
            r = resp.json()
            for server in r['data']:
                hostname = server['hostname']
                if (not ret[hostname]):
                    print "{0} is now up!".format(hostname)
                ret[hostname] = True

            done = all(up for up in ret.values())
            if done:
                break
            else:
                elapsed += 1
        except Exception as ex:
            print "{0}: {1}".format(url, ex)

        time.sleep(1)

    min, sec = divmod(elapsed, 60)

    for server in ret:
        if not ret[server]:
            print "Server {0} never came up!".format(server)

    if done:
        print "Finished in {0}:{1:02d}!".format(min,sec)
    else:
        print "Timed out after {0}:{1:02d}!".format(min,sec)

    print "Enabling application!"

    for server in ret:
        url = "https://{0}/mmi/alexa/v1.0/topo/servers/{1}/appl".format(noafloatingip, server)
        if ret[server]:
            print "Enabling application on {0}...".format(server)
            data = json.dumps({'applState': 'Enabled'})
            resp = requests.put(url, verify=False, headers=headers, data=data)
        else:
            print "Server {0} never came up... Not going to enable the application.".format(server)

    # TODO: generate and run this for more than one SO Network Element.
    print "Performing UDR configuration..."
    sshtools.putFile(soafloatingip, "/tmp/{0}_appinit.php".format(args.stackname), "/tmp/appinit.php", "admusr", args.keyfile)
    sshtools.runCommand(soafloatingip, "/usr/bin/php /tmp/appinit.php", "admusr", args.keyfile, printoutput = True)

    os.unlink("/tmp/{0}_appinit.php".format(args.stackname))

    sshtools.runCommand(noafloatingip, "source /etc/profile; sudo prod.stop -i; sudo prod.start -i", "admusr", args.keyfile, printoutput = True)

    print "Complete!"
    print "NOA is accessible at https://{0}/".format(noafloatingip)
    print "SOA is accessible at https://{0}".format(soafloatingip)
