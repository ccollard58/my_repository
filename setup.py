from setuptools import setup, find_packages

setup(
    name="commscloud-stacktools",
    version = "0.1",
    packages = ['commscloud_stacktools'],
    package_data = {'commscloud_stacktools':['appinit.php.tmpl', 'bootstrap.py.tmpl', 'soapwait.php']},
    install_requires = ["ipaddress", "requests", "python-keystoneclient", "python-heatclient",
                        "python-neutronclient", "python-novaclient", "paramiko"],
    entry_points = {
        'console_scripts': [
            'stackcreate=commscloud_stacktools.stackcreate:create',
            'stackconfigure=commscloud_stacktools.stackconfigure:configure',
        ],
    },
    include_package_data = True,
)
