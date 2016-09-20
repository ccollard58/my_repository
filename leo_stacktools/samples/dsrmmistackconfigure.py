#!/usr/bin/env python

# Example showing how to replace the configureTopology function of the
# stackconfigure module with your own specific things.

# This sample create a 1-NO, 1-SO setup to be used by the DSR MMI developers.

# to invoke this script. Update the PYTHONPATH to include the directory containing stackconfigure.py
# export PYTHONPATH=$PYTHONPATH:/root/stacktools/leo_stacktools

import stackconfigure
import mmirequests
import json

# mmirequests Globals
mmirequests.username             = 'guiadmin'
mmirequests.password             = 'tekware'
mmirequests.sslVerifyCertificate = False

# Globals
NTPIP =  '192.168.56.180'

def printJson(output):
    print getPrettyJson(output)

def getPrettyJson(output):
    return '%s' % (json.dumps(output, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=False))

def configureNetworkElements(noafloatingip, topologyInfo):
    """ Add Network Elements """

    url = 'https://%s/mmi/dsr/v1.0/topo/networkelements' % (noafloatingip)
    for networkElement in topologyInfo['networkelements']:
        print "Configuring Network Element %s ..." % (networkElement['name'])
        payload = { 'name' : networkElement['name']}
        response = mmirequests.post(url, data=json.dumps(payload))
        printJson(response.json())

def configureServerGroups(noafloatingip, topologyInfo):
    """ Add Server Groups """

    url = 'https://%s/mmi/dsr/v1.0/topo/servergroups' % (noafloatingip)
    for serverGroup in topologyInfo['servergroups']:
        print "Configuring Server Group %s ..." % (serverGroup['name'])
        payload = {
            'functionName' : 'DSR (active/standby pair)',
            'level'        : serverGroup['level'],
            'name'         : serverGroup['name'],
            'numWanRepConn': 1,
            'parentSgName' : serverGroup['parentSgName']
        }
        response = mmirequests.post(url, data=json.dumps(payload))
        printJson(response.json())

def configureServers(noafloatingip, topologyInfo):
    """ Add Servers """

    url = 'https://%s/mmi/dsr/v1.0/topo/servers' % (noafloatingip)
    for server in topologyInfo['servers']:
        print "Configuring Server %s..." % (server['hostname'])
        payload = {
            'haRolePref'        : 'DEFAULT',
            'hostname'          : server['hostname'],
            'location'          : 'OpenStack',
            'networkElementName': server['networkElementName'],
            'ntpServers'        : [{
                'ipAddress': server['ntpServerIp'],
                'prefer'   : True
            }],
            'profileName'       : 'DSR TVOE Guest',
            'role'              : server['role'],
            'serverGroupName'   : server['serverGroupName'],
            'systemId'          : 'OpenStack'
        }
        response = mmirequests.post(url, data=json.dumps(payload))
        printJson(response.json())


def configureNetworks(noafloatingip, topologyInfo):
    """ Configure Networks """

    url = 'https://%s/mmi/dsr/v1.0/topo/networks' % (noafloatingip)

    for network in topologyInfo['networks']:
        print "Configuring Network %s..." % (network['name'])
        payload = {
            'ipAddress' : network['ipAddress'],
            'name'      : network['name'],
            'subnetMask': network['subnetMask'],
            'vlanId'    : network['vlanId'],
        }

        if network['name'] in ['XMI', 'IMI']:
            payload['type'] = 'OAM'
        else:
            payload['type'] = 'APPLICATION'

        if network['gateway'] is None:
            payload['isDefault']  = False
            payload['isRoutable'] = False
        else:
            payload['isDefault']  = True
            payload['isRoutable'] = True
            payload['gatewayAddress'] = network['gateway']

        if network['neName'] != 'GLOBAL':
            payload['neName'] = network['neName']
            payload['locked'] = True
        else:
            payload['locked'] = False

        response = mmirequests.post(url, data=json.dumps(payload))
        printJson(response.json())

def configureNetworkDevices(noafloatingip, topologyInfo):
    """ Configure Network Devices """

    url = "https://%s/mmi/dsr/v1.0/topo/networkdevices" % (noafloatingip)

    for networkDevice in topologyInfo['networkDevices']:
        print "Configuring IP Address %s..." % (networkDevice['ipAddress'])
        payload = {
            "hostname": networkDevice['hostname'],
            "interfaces": [
                {
                    "ipAddress": networkDevice['ipAddress'],
                    "networkName": networkDevice['networkName'],
                }
            ],
            "options": {
                "bootProto": "none",
                "onboot": True
            },
            "port": networkDevice['port'],
            "type": networkDevice['type'],
        }
        response = mmirequests.post(url, data=json.dumps(payload))
        printJson(response.json())

def configureTopology(noafloatingip, topologyInfo):
    configureNetworkElements(noafloatingip, topologyInfo)
    configureServerGroups(noafloatingip, topologyInfo)
    configureServers(noafloatingip, topologyInfo)
    configureNetworks(noafloatingip, topologyInfo)
    configureNetworkDevices(noafloatingip, topologyInfo)

if __name__ == '__main__':
    # call the stackconfigure configure function after replacing the
    # configureTopology function
    stackconfigure.configureTopology = configureTopology
    stackconfigure.configure()
