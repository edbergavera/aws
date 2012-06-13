# Create your views here.
import os
import time
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
            time.sleep(20)
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
    key = ec2.create_key_pair(key_name)
    key.save('~/.ssh')
    os.chown(os.path.join(os.path.expanduser('~/.ssh'),key_name+'.pem'),1000,1000)
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

    return instance