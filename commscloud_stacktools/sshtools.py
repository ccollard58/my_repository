import os
import sys

import paramiko

def runCommand(host, command, user="admusr", key = None, printoutput = False):
    if not key:
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(host, port=22,
            username=user, key_filename=key, allow_agent=False)

    stdin,stdout,stderr = client.exec_command(command)
    ret = ""

    for line in stdout:
        if printoutput:
            print line.strip()
        ret += line

    for line in stderr:
        print line.strip()

    return ret

def progress(cur,total):
    sys.stdout.write("Copying... {0:.2%}\r".format(float(cur)/total))

def putFile(host, localpath, remotepath, user="admusr", key = None):
    if not key:
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=22,
            username=user, key_filename=key, allow_agent=False)

    sftp = client.open_sftp()

    sftp.put(localpath, remotepath, progress)
    print "\nDone!"
