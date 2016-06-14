#!/usr/bin/env python

import argparse
import ipaddress
import math
import os
import sys

from yaml import dump
import yaml

def gennet(name, nename, cidr, routed=True):
    net = {}
    meta = {}
    subnet = {}
    interface = None

    resourceName = "{0}_{1}".format(nename, name)
    paramName = resourceName + "_cidr"

    param = {
        paramName: {
            'type': 'string',
            'label': "{0} {1} Network Address".format(nename, name),
            'default': cidr
        }
    }

    meta['name'] = name
    meta['neName'] = nename

    net['type'] = 'OS::Neutron::Net'
    net['metadata'] = meta

    subnet['type'] = 'OS::Neutron::Subnet'

    props = {}
    props['network_id'] = {'get_resource': resourceName}
    props['cidr'] = {'get_param': paramName}

    if routed:
        props['dns_nameservers'] = ['192.168.56.180', '10.75.137.245', '10.75.137.246']
    else:
        props['gateway_ip'] = None

    subnet['properties'] = props

    if routed:
        interface = {}
        interface['type'] = "OS::Neutron::RouterInterface"
        props = {}
        props['router_id'] = {'get_resource': 'router'}
        props['subnet'] = {'get_resource': "{0}_subnet".format(resourceName)}

        interface['properties'] = props

    return {
        'name': resourceName,
        'net': net,
        'subnet': subnet,
        'interface': interface,
        'params': param
    }

def genserver(name, nename, sgname, nets, role, flavor, primary = False, haRolePref = None,
              extra = False, user_data = None, image = None):
    instance = {}
    props = {}
    meta  = {}
    ports = {}
    floatingips = {}

    ipname = None

    instance['type'] = "OS::Nova::Server"

    props["flavor"] = flavor

    if not image:
        image = {"get_param":"image"}

    props["image"] = image

    props["key_name"] = {"get_param": "sshkeypair"}
    props["name"] = {
        'str_replace': {
            'template': '$name-{0}'.format(name),
            'params': {
                '$name': {'get_param': 'OS::stack_name'}
            }
        }
    }

    props['user_data_format'] = "RAW"

    if not user_data:
        user_data = open("{0}/cloudconfig.yaml.tmpl".format(os.path.dirname(__file__))).read()

    props["user_data"] = {
        'str_replace':{
            'template': user_data,
            'params': {
                '$stack': {'get_param': 'OS::stack_name'},
                '$name': name
            }
        }
    }

    meta['neName'] = nename
    meta['sgName'] = sgname
    meta['role']   = role
    meta['extra'] = extra

    if role == "roleNOAMP" and primary:
        meta['noa'] = True
    else:
        meta['noa'] = False

    if haRolePref:
        meta['haRolePref'] = haRolePref


    props['networks'] = []

    for net in nets:
        portname = "{0}_{1}_port".format(name, net['name'])
        ports[portname] = {
            'type': 'OS::Neutron::Port',
            'properties': {
                'network': {'get_resource': net['name']}
            }
        }

        if primary and net['interface']:
            ipname = portname + "_fip"
            floatingips[ipname] = {
                'type': 'OS::Neutron::FloatingIP',
                'depends_on': net['name'] + '_intf',
                'properties': {
                    'floating_network': {'get_param': 'public_network'},
                    'port_id' : {'get_resource': portname}
                }
            }

        props['networks'].append({'port': {'get_resource': portname}})

    instance['properties'] = props
    instance['metadata'] = meta

    return {
        'name': name,
        'instance': instance,
        'ports': ports,
        'floatingips': floatingips,
        'floatingipout': ipname,
    }

def genyaml(input):
    nes = 0
    sgs = 0
    mps = 0

    nofunction = input['params']['noampfunction']

    for ne in input['params']['networkelements']:
        nes += 1

    # supernet = u"23.42.0.0/23"
    supernet = unicode(input['params']['supernet'])
    supernet = ipaddress.ip_interface(supernet)
    prefixdiff = int(math.ceil(math.log(nes + 1, 2)))

    try:
        subnets = list(supernet.network.subnets(prefixdiff))
        subnets.reverse()
    except Exception as e:
        message = "Not enough subnets in provided supernet: "
        message += str(e)
        return message

    if sgs * mps + 2 > subnets[0].num_addresses - 2:
        message = "Not enough addresses in subnets: "
        message += "Need {0}, got {1}!".format(sgs * mps + 2, subnets[0].num_addresses - 2)
        return message

    if nes > 64:
        message = "Too many NEs! Max: 64 Requested: {0}".format(nes)
        return message

    if nes * sgs * mps + (2 * sgs) + 2> 1024:
        message = "Too many servers! Max: 1024 Requested: {0}".format(nes * sgs * mps + (2 * sgs) + 2)
        return message

    params = {
        'image': {
            'type': 'string',
            'label': 'Image Name'
        },
        'public_network': {
            'type': 'string',
            'label': 'Public Network ID',
            'default': 'db3b2356-17c7-491e-9b7b-01fc1e946f8d',
        },
        'sshkeypair': {
            'type': 'string',
            'label': 'SSH keypair name',
            'default': 'sshkey'
        }
    }
    paramGroups = [
        {
            'label': 'VM Options',
            'parameters': [ 'image', 'sshkeypair' ]
        }
    ]
    netParams = ['public_network']

    resources = {}
    appworks = {
        'networkelements': [],
        'servergroups': []
    }

    nets = []
    servers = []
    outputs = {}

    resources['router'] = {
        'type': 'OS::Neutron::Router',
        'properties':{
            'external_gateway_info': {
                'network': {'get_param': 'public_network'}
            }
        }
    }

# NO Network Element stuff. This will always be here.

    appworks['networkelements'].append({'name': 'NO_NE'})
    appworks['servergroups'].append({'name': 'NO_SG',
                                     'level':'A',
                                     'parentSgName':'NONE',
                                     'functionName': nofunction,
                                     'numWanRepConn': 1})

    wan = gennet("WAN", "NO_NE", str(subnets.pop()))
    lan = gennet("LAN", "NO_NE", "172.30.0.0/24", False)
    xsi = gennet("XSI", "GLOBAL", "192.168.99.0/24", False)

    nets += [wan,lan,xsi]

    noampflavor = input['params']['noampflavor']

    noa = genserver("noa", "NO_NE", "NO_SG", [wan,lan,xsi], "roleNOAMP", noampflavor, primary = True)
    noa['instance']['metadata']['appworks'] = appworks

    nob = genserver("nob", "NO_NE", "NO_SG", [wan,lan,xsi], "roleNOAMP", noampflavor, haRolePref = "SPARE")
    servers += [noa, nob]

    # Add any extra servers
    for server in input['extras']:
        s = genserver(server['name'],"NONE","NONE",[wan,xsi],"NONE",server['flavor'], extra = True, user_data = server['user-data'], image = server['image'])
        servers += [s]
    nenum = 1

    for ne in input['params']['networkelements']:
        mpnum = 1
        nename = "SO_NE{0}".format(nenum)
        appworks['networkelements'].append({'name': nename})

        wan = gennet("WAN", nename, str(subnets.pop()))
        lan = gennet("LAN", nename, "172.30.0.0/24", False)
        nets += [wan,lan]

        sosgname = "SO_SG{0}".format(nenum)
        appworks['servergroups'].append({'name': sosgname,
                                         'level':'B',
                                         'parentSgName':'NO_SG',
                                         'functionName': ne['soamfunction'],
                                         'numWanRepConn': 1})

        soa = genserver("soa{0}".format(nenum), nename, sosgname, [wan,lan], "roleSOAM", ne['soamflavor'], primary = True)
        sob = genserver("sob{0}".format(nenum), nename, sosgname, [wan,lan], "roleSOAM", ne['soamflavor'], haRolePref = "SPARE")
        servers += [soa, sob]

        sgnum = 1
        for sg in ne['mpservergroups']:
        # for rawsgnum in range(0, sgs):
            mpsgname = "SO{0}MP_SG{1}".format(nenum, sgnum)
            appworks['servergroups'].append({'name': mpsgname,
                                             'level':'C',
                                             'parentSgName': sosgname,
                                             'functionName': sg['function'],
                                             'numWanRepConn': 1})

            for rawmpnum in range(0, sg['mpcount']):
                mp = genserver("so{0}mp{1}".format(nenum, mpnum), nename, mpsgname, [wan,lan,xsi], "roleMP", sg['mpflavor'])
                servers += [mp]
                mpnum += 1
            sgnum += 1
        nenum += 1

# put it all together!
    for net in nets:
        name = net['name']
        resources[name] = net['net']
        resources[name+"_subnet"] = net['subnet']
        if net['interface']:
            resources[name+"_intf"] = net['interface']
        for key in net['params']:
            params[key] = net['params'][key]
            netParams.append(key)

    for server in servers:
        name = server['name']
        resources[name] = server['instance']
        for port in server['ports']:
            resources[port] = server['ports'][port]
        for fip in server['floatingips']:
            resources[fip] = server['floatingips'][fip]

        floatingipout = server['floatingipout']
        if floatingipout:
            outputs['floatingip_{0}'.format(name)] = {
                "description": "The floating IP used to access '{0}'.".format(name),
                "value": {
                    "get_attr": [floatingipout, 'floating_ip_address']
                }
            }

    paramGroups.append({
        'label': 'Network Options',
        'parameters': netParams
    })

    doc = {"heat_template_version": "2015-04-30", "parameter_groups": paramGroups,
           "parameters": params, "resources": resources, "outputs": outputs}

    return dump(doc, default_flow_style=False)

def generate():
    parser = argparse.ArgumentParser(description="Generate a HOT template.")
    parser.add_argument("input", help="Input YAML specification", type=str)
    args = parser.parse_args()

    inputdata = yaml.load(open(args.input).read())

    print genyaml(inputdata)
