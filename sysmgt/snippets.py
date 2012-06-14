import datetime
import subprocess
import json

__author__ = 'kismet'


def instance_uptime(launch_time):
    """
    Computes the uptime in hours the instance is running.
    """
    #ts = datetime.datetime.strptime(launch_time[:19], "%Y-%m-%dT%H:%M:%S")
    import boto.utils
    lt = boto.utils.parse_ts(launch_time)
    today = datetime.datetime.today()
    time_delta = today.now() - ts
    hours = time_delta.total_seconds() / 3600 - 8
    return int(hours)

def list_minions():
    """
    Lists all accepted minions
    """
    accepted = subprocess.Popen(["sudo", "salt-key", "--list=accepted"], stdout=subprocess.PIPE).communicate()[0]
    # out is a list
    out = json.loads(accepted)
    return out


# Command to get package (pkg) description
#
# cmd = 'dpkg-query -Wf \'${{Description}}\n\' {0}'.format(pkg)


# List of accepted minions

# hosts = subprocess.Popen(["sudo", "salt-key", "--list=accepted"], stdout=subprocess.PIPE).communicate()[0].split()
# hosts_list = [host.strip('\x1b[0;32m') for host in hosts]
