__author__ = 'kismet'

from fabric.api import run, env

env.hosts = ['ubuntu@ec2-176-32-75-156.ap-northeast-1.compute.amazonaws.com']

def host_type():
    run('uname -s')