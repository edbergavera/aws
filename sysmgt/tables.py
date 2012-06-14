__author__ = 'kismet'
import django_tables2 as tables

class EC2ClientsTable(tables.Table):
    instance_id = tables.URLColumn(verbose_name='Instance ID')
    state = tables.Column()
    ami_id = tables.Column(verbose_name='AMI ID')
    tag = tables.Column()
    platform = tables.Column()
    type = tables.Column()
    key_pair = tables.Column(verbose_name='Key Pair')
    private_ip = tables.Column(verbose_name='Private IP')
    public_dns = tables.Column(verbose_name='Public DNS')


    class Meta:
        attrs = {'class': 'table table-striped'}


