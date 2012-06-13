from django import forms

AMI_ID=(
    ('ami-60c77761', 'Ubuntu 12.04 LTS 64-bit'),
    ('ami-44328345', 'Ubuntu 11.10 64-bit'),
)

TYPE=(
    ('t1.micro', 'Micro Instance'),
    ('m1.small', 'Small Instance')
)
class LaunchEC2Form(forms.Form):
    ami_id = forms.ChoiceField(choices=AMI_ID)
    instance_type = forms.ChoiceField(choices=TYPE)
    keypair = forms.CharField(max_length=10)
    tag = forms.CharField(max_length=20)