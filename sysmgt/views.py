# Create your views here.
import os
import time
import boto
import boto.manage.cmdshell
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import simplejson
import salt.client
from fabfile import host_type
from fabric.tasks import execute

DIR = os.path.abspath(os.path.dirname(__file__))

script = open(os.path.join(DIR, 'scripts/salt_bootstrap.sh'))

def hello(request):
    client = salt.client.LocalClient()
    ret = client.cmd('ip*', 'pkg.list_upgrades')
    #    out = ret['ip-10-152-251-59.ap-northeast-1.compute.internal']
    #    ret = client.cmd('*', 'test.ping', '--raw-out')
    return render_to_response('launch_instance.html', {'ret': ret})

def view_run():
    out = execute(host_type)
    return HttpResponse(out)
# The following function courtesy of Mitch Garnaat

def launch_instance(ami='ami-60c77761',
                    instance_type='t1.micro',
                    key_name='svr02key',
                    key_extension='.pem',
                    key_dir='~/.pemkeys',
                    group_name='quick-start-1',
                    ssh_port=22,
                    cidr='0.0.0.0/0',
                    tag='minion',
                    user_data=script,
                    cmd_shell=True,
                    login_user='ubuntu',
                    ssh_passwd=None,
                    access_key=None,
                    secret_key=None):
    """
    Launch an instance and wait for it to start running.
    Returns a tuple consisting of the Instance object and the CmdShell
    object, if request, or None.

    ami             The ID of the Amazon Machine Image that this instance will
                    be based on. Default is a 64-bit Amazon Linux EBS image.

    instance_type   The type of the instance.

    key_name        The name of the SSH Key used for logging into the instance.
                    It will be created if it does not exist.

    key_extension   The file extension for SSH private key files.

    key_dir         The path to the directory containing SSH private keys.
                    This is usually ~/.ssh.

    group_name      The name of the security group used to control access
                    to the instance. It will be created if it does not exist.
                    ssh_port The port number you want to use for SSH access (default 22).
                    cidr The CIDR block used to limit access to your instance.

    tag             A name that will be used to tag the instance so we can
                    easily find it later.
    user_data       Data that will be passed to the newly started
                    instance at launch and will be accessible via
                    the metadata service running at http://169.254.169.254.

    cmd_shell       If true, a boto CmdShell object will be created and returned.
                    This allows programmatic SSH access to the new instance.

    login_user      The user name used when SSH'ing into new instance. The default is 'ec2-user'

    ssh_passwd      The password for your SSH key if it is encrypted with a
                    passphrase.

    """
    cmd = None
    # Create a connection to EC2 service.
    # You can pass credentials in to the connect_ec2 method explicitly
    # or you can use the default credentials in your ~/.boto config file
    # as we are doing here.
    ec2 = boto.connect_ec2(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    # Check to see if specified keypair already exists.
    # If we get an InvalidKeyPair.NotFound error back from EC2,
    # it means that it doesn't exist and we need to create it.
    try:
        key = ec2.get_all_key_pairs(keynames=[key_name])[0]
    except ec2.ResponseError, e:
        if e.code == 'InvalidKeyPair.NotFound':
            print 'Creating keypair: %s' % key_name
            # Create an SSH key to use when logging into instances.
            key = ec2.create_key_pair(key_name)
            # AWS will store the public key but the private key is
            # generated and returned and needs to be stored locally.
            # The save method will also chmod the file to protect
            # your private key.
            key.save(key_dir)
        else:
            raise
            # Check to see if specified security group already exists.
        # If we get an InvalidGroup.NotFound error back from EC2,
    # it means that it doesn't exist and we need to create it.
    try:
        group = ec2.get_all_security_groups(groupnames=[group_name])[0]
    except ec2.ResponseError, e:
        if e.code == 'InvalidGroup.NotFound':
            print 'Creating Security Group: %s' % group_name
            # Create a security group to control access to instance via SSH.
            group = ec2.create_security_group(group_name,
                'A group that allows SSH access')
        else:
            raise
            # Add a rule to the security group to authorize SSH traffic
        # on the specified port.
    try:
        group.authorize('tcp', ssh_port, ssh_port, cidr)
    except ec2.ResponseError, e:
        if e.code == 'InvalidPermission.Duplicate':
            print 'Security Group: %s already authorized' % group_name
        else:
            raise

    # Now start up the instance. The run_instances method
    # has many, many parameters but these are all we need
    # for now.
    reservation = ec2.run_instances(ami,
        key_name=key_name,
        security_groups=[group_name],
        instance_type=instance_type,
        user_data=user_data)
    # Find the actual Instance object inside the Reservation object
    # returned by EC2.
    instance = reservation.instances[0]

    pub_dns = reservation.instances[0].public_dns_name
    print pub_dns
    # The instance has been launched but it's not yet up and
    # running. Let's wait for its state to change to 'running'.
    print 'waiting for instance'
    while instance.state != 'running':
        print '.'
        time.sleep(5)
        instance.update()
    print 'done'
    # Let's tag the instance with the specified label so we can
    # identify it later.
    instance.add_tag(tag)
    # The instance is now running, let's try to programmatically
    # SSH to the instance using Paramiko via boto CmdShell.
    if cmd_shell:
        key_path = os.path.join(os.path.expanduser(key_dir),
            key_name+key_extension)
        cmd = boto.manage.cmdshell.sshclient_from_instance(instance,
            key_path,
            user_name=login_user)

    return (instance, cmd)