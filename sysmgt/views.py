# Create your views here.
import os
import time
import datetime
import boto
import boto.manage.cmdshell
from django.core.mail import send_mail
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
import salt.client
import subprocess
from sysmgt.forms import LaunchEC2Form
from django.views.decorators.csrf import csrf_exempt

DIR = os.path.abspath(os.path.dirname(__file__))

script = open(os.path.join(DIR, 'scripts/salt_bootstrap.sh')).read()

@csrf_exempt
def launch(request):
    if request.method == 'POST':
        form = LaunchEC2Form(request.POST)
        if form.is_valid():
            ami_id = form.cleaned_data['ami_id']
            instanceType = form.cleaned_data['instance_type']
            keypair = form.cleaned_data['keypair']
            tag_name = form.cleaned_data['tag']
            instance_id = launch_instance(ami=ami_id,instance_type=instanceType,key_name=keypair,tag=tag_name)
            html = "<html><body>Instance ID: %s</body></html>"% instance_id
            return HttpResponse(html)
    else:
        form = LaunchEC2Form()
    return render_to_response('launch_form.html', {'form': form})


def index(request):
    return render_to_response('index.html',)


def disk_usage(request):
    client = salt.client.LocalClient()
    ret = client.cmd('T2*', 'cmd.run', ['df -hT'])
    return render_to_response('index.html', {'ret' : ret})

def manage():
    pass

# create an Ubuntu instance

def launch_instance(ami, instance_type, key_name, tag):
    """
    Launch an instance and wait for it to start running.
    Returns a tuple consisting of the Instance object and the CmdShell
    object, if request, or None.

    ami             The ID of the Amazon Machine Image that this instance will
                    be based on. Default is a 64-bit Amazon Linux EBS image.

    instance_type   The type of the instance.

    key_name        The name of the SSH Key used for logging into the instance.
                    It will be created if it does not exist.

    tag             A name that will be used to tag the instance so we can
                    easily find it later.

    """
    # Create a connection to EC2 service.
    # You can pass credentials in to the connect_ec2 method explicitly
    # or you can use the default credentials in your ~/.boto config file
    # as we are doing here.

    ec2 = boto.connect_ec2()
#    key = ec2.create_key_pair(key_name)
#    key.save('~/.ssh')
    try:
        key = ec2.get_all_key_pairs(keynames=[key_name])[0]
    except ec2.ResponseError, e:
        if e.code == 'InvalidKeyPair.NotFound':
#            print 'Creating keypair: %s' % key_name
            # Create an SSH key to use when logging into instances.
            key = ec2.create_key_pair(key_name)

            # AWS will store the public key but the private key is
            # generated and returned and needs to be stored locally.
            # The save method will also chmod the file to protect
            # your private key.
            key.save('~/.ssh')
        else:
            raise
#    os.chown(os.path.join(os.path.expanduser('~/.ssh'),key_name+'.pem'),1000,1000)
    # Now start up the instance. The run_instances method
    # has many, many parameters but these are all we need
    # for now.
    reservation = ec2.run_instances(ami,
        key_name=key_name,
        security_groups=['quick-start-1'],
        instance_type=instance_type,
        user_data=script)

    # Find the actual Instance object inside the Reservation object
    # returned by EC2.
    instance = reservation.instances[0]
    instance.add_tag(tag)
    # enable detailed monitoring
    instance.monitor()
    # check if instance is running
    while instance.state != 'running':
        time.sleep(5)
        instance.update()
    # store instance info to simpledb
    store_to_simpledb(instance.id)

    return instance


def store_to_simpledb(instance_id):
    __platform__={'ami-60c77761' : 'Ubuntu 12.04 LTS 64-bit',
                  'ami-44328345' : 'Ubuntu 11.10 64-bit',
                  'ami-942f9995' : 'Ubuntu 10.04 LTS 64-bit'}
    sdb = boto.connect_sdb()
    dom = sdb.get_domain('ec2_clients')
    # establish connection to ec2
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances([instance_id])
    instance = reservations[0].instances[0]
    # record id is item_name
    item_name = instance.id
    item_attrs = {'hostname' : instance.private_dns_name,
                  'state' : instance.state,
                  'ami_id' : instance.image_id,
                  'platform':  __platform__[instance.image_id],
                  'type' : instance.instance_type,
                  'key_pair' : instance.key_name,
                  'public_dns' : instance.public_dns_name,
                  'private_ip' : instance.private_ip_address,
                  'launch_time' : launch_time(instance.launch_time),
                  'root_device' : instance.root_device_name,
                  'region' : instance.region.name,
                  'tag' : instance.tags.keys()}

    dom.put_attributes(item_name, item_attrs)

def refresh_db(instance_id):

    conn = boto.connect_ec2()
    reservations = conn.get_all_instances([instance_id])
    instance = reservations[0].instances[0]
    # update instance
    instance.update()
    # store new values to simpledb
    store_to_simpledb(instance.id)

def retrieve_simpledb(instance_id):

    sdb = boto.connect_sdb()
    dom = sdb.get_domain('ec2_clients')
    return dom.get_attributes(instance_id)


def instance_uptime(launch_time):
    """
    Computes the uptime in hours the instance is running.
    """
    #ts = datetime.datetime.strptime(launch_time[:19], "%Y-%m-%dT%H:%M:%S")
    import boto.utils
    lt = boto.utils.parse_ts(launch_time)
    today = datetime.datetime.utcnow()
    time_delta = today.now() - lt
    hours = time_delta.total_seconds() / 3600 - 8
    return int(hours)

def launch_time(launch_time):
    """
    Returns the date format
    """
    ts = datetime.datetime.strptime(launch_time[:19], "%Y-%m-%dT%H:%M:%S")

    return ts.strftime("%Y-%m-%d %H:%M:%S")

def reboot(instance_id):
    conn = boto.connect_ec2()
    conn.reboot_instances([instance_id])

def stop(instance_id):
    conn = boto.connect_ec2()
    conn.stop_instances([instance_id])

def start(instance_id):
    conn = boto.connect_ec2()
    conn.start_instances([instance_id])

def terminate(instance_id):
    conn = boto.connect_ec2()
    conn.terminate_instances(instance_id)
    #update database after an instance is terminated
    delete_item(instance_id)

def console_output(instance_id):
    """
    Returns console output as string
    """
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances([instance_id])
    instance = reservations[0].instances[0]
    return instance.get_console_output().output

def delete_item(instance_id):
    """
    Deletes an item from simpledb when an instance is terminated
    """
    sdb = boto.connect_sdb()
    dom = sdb.get_domain('ec2_clients')
    for item in dom:
        if instance_id == item.name:
            dom.delete_item(item)



