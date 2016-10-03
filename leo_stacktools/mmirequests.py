#!/usr/bin/python

# Wrapper module over python requests module to make MMI calls to an AppWorks based product.

import requests
import requests.api
import urlparse
import json

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Globals
username             = 'guiadmin'
password             = 'tekware'
sslVerifyCertificate = True

def checkAvailable(address, **kwargs):
    """ Check to see if the MMI is available at the given address. 
        Returns a standard response object. """

    kwargs.setdefault('verify', sslVerifyCertificate)
    return requests.api.request('get', "https://{0}/mmi/alexa/v1.0/topo/versions".format(address), **kwargs)

def get(url, **kwargs):
    """ Returns the overridden requests module get function. The overridden
        function has the X-Auth-Token header added and the sslVerifyCertificate
        value set to the module sslVerifyCertificate value  in the request """

    headers = {'X-Auth-Token': getAuthToken(url)}
    kwargs.setdefault('headers', headers)
    kwargs.setdefault('verify', sslVerifyCertificate)
    return requests.api.request('get', url, **kwargs)

def post(url, **kwargs):
    """ Returns the overridden requests module post function. The overridden
        function has the X-Auth-Token header added and the sslVerifyCertificate
        value set to the module sslVerifyCertificate value  in the request """

    headers = {'X-Auth-Token': getAuthToken(url)}
    kwargs.setdefault('headers', headers)
    kwargs.setdefault('verify', sslVerifyCertificate)
    return requests.api.request('post', url, **kwargs)

def put(url, **kwargs):
    """ Returns the overridden requests module put function. The overridden
        function has the X-Auth-Token header added and the sslVerifyCertificate
        value set to the module sslVerifyCertificate value  in the request """

    headers = {'X-Auth-Token': getAuthToken(url)}
    kwargs.setdefault('headers', headers)
    kwargs.setdefault('verify', sslVerifyCertificate)
    return requests.api.request('put', url, **kwargs)

def delete(url, **kwargs):
    """ Returns the overridden requests module delete function. The overridden
        function has the X-Auth-Token header added and the sslVerifyCertificate
        value set to the module sslVerifyCertificate value  in the request """

    headers = {'X-Auth-Token': getAuthToken(url)}
    kwargs.setdefault('headers', headers)
    kwargs.setdefault('verify', sslVerifyCertificate)
    kwargs.setdefault('data', json.dumps(payload))
    return requests.api.request('delete', url, **kwargs)

def getAuthToken(url):
    """ Returns the authentication token """

    authUri = "%s/auth/tokens" % getBaseUrl(url)

    payload = {
        'username' : username,
        'password' : password
    }

    response = requests.post(authUri, data=payload, verify = sslVerifyCertificate)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    return response.json().get('data').get('token')

def getBaseUrl(url):
    """Get base URI extracted from given URI"""

    url    = urlparse.urlparse(url)
    path   = url.path.strip('/').split('/')
    appl   = path[1]
    ver    = path[2]
    netloc = url.netloc
    scheme = url.scheme

    return "{scheme}://{netloc}/mmi/{appl}/{ver}".format(
        scheme = scheme,
        netloc = netloc,
        appl   = appl,
        ver    = ver
    )
