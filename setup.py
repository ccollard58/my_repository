from setuptools import setup, find_packages

setup(
    name="leo-stacktools",
    version = "0.1",
    packages = ['leo_stacktools', 'leo_heatgen'],
    package_data = {'leo_stacktools': ['appinit.php.tmpl', 'bootstrap.py.tmpl', 'soapwait.php'],
                    'leo_heatgen':    ['cloudconfig.yaml.tmpl'],
                   },
    install_requires = ["ipaddress", "requests", "pyyaml", "python-keystoneclient",
                        "python-heatclient", "python-neutronclient", "python-novaclient",
                        "paramiko"],
    entry_points = {
        'console_scripts': [
            'stackcreate=leo_stacktools.stackcreate:create',
            'stackconfigure=leo_stacktools.stackconfigure:configure',
            'heatgen=leo_heatgen.generator:generate',
        ],
    },
    include_package_data = True,
)
