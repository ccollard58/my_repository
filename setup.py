from setuptools import setup, find_packages

setup(
    name="commscloud-stacktools",
    version = "0.1",
    packages = ['commscloud_stacktools', 'commscloud_heatgen'],
    package_data = {'commscloud_stacktools': ['appinit.php.tmpl', 'bootstrap.py.tmpl', 'soapwait.php'],
                    'commscloud_heatgen':    ['cloudconfig.yaml.tmpl'],
                   },
    install_requires = ["ipaddress", "requests", "pyyaml", "python-keystoneclient",
                        "python-heatclient", "python-neutronclient", "python-novaclient",
                        "paramiko"],
    entry_points = {
        'console_scripts': [
            'stackcreate=commscloud_stacktools.stackcreate:create',
            'stackconfigure=commscloud_stacktools.stackconfigure:configure',
            'heatgen=commscloud_heatgen.generator:generate',
        ],
    },
    include_package_data = True,
)
