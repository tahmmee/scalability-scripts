
# Python script to generate the cloudformation template json file
# This is not strictly needed, but it takes the pain out of writing a
# cloudformation template by hand.  It also allows for DRY approaches
# to maintaining cloudformation templates.

from troposphere import Ref, Template, Parameter, Output, Join, GetAtt, Tags
import troposphere.ec2 as ec2

t = Template()

t.add_description(
    'An Ec2-classic stack with Couchbase Server n a VPC'
)

NUM_COUCHBASE_SERVERS=1

COUCHBASE_INSTANCE_TYPE="r3.4xlarge"
SYNC_GW_INSTANCE_TYPE="m3.medium"
GATELOAD_INSTANCE_TYPE="m3.medium"

def createCouchbaseVPC(t):
    couchbaseVPC = t.add_resource(ec2.VPC(
        'VPC', CidrBlock='10.0.0.0/16',
        EnableDnsSupport='true',
        EnableDnsHostnames='true',
        Tags=Tags(Name=Join('', ['vpc-scalabilty-', Ref('AWS::Region')]))
    ))
    return couchbaseVPC

def createCouchbaseInternetGateway(t):
    couchbaseInternetGateway = t.add_resource(ec2.InternetGateway(
        'GATEWAY',
         Tags=Tags(Name=Join('', ['gateway-scalability-', Ref('AWS::Region')]))
    ))
    return couchbaseInternetGateway

def createCouchbaseVPCGatewayAttachment(t, gateway, vpc):
    couchbaseVPCGatewayAttachment =  t.add_resource(ec2.VPCGatewayAttachment(
        'VPCGATEWAYATTACHMENT',
        InternetGatewayId=Ref(gateway),
        VpcId=Ref(vpc)
    ))
    return couchbaseVPCGatewayAttachment

def createCouchbaseRouteTable(t, vpc):
    couchbaseRouteTable = t.add_resource(ec2.RouteTable(
        'ROUTETABLE',
        VpcId=Ref(vpc),
        Tags=Tags(Name=Join('', ['routetable-scalabilty-', Ref('AWS::Region')]))
    ))
    return couchbaseRouteTable

def createCouchbaseRoute(t, gateway, routetable):
    couchbaseRoute = t.add_resource(ec2.Route(
        'ROUTE',
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=Ref(gateway),
        RouteTableId=Ref(routetable)
    ))
    return couchbaseRoute

def createCouchbaseSubnet(t, vpc):
    couchbaseSubnet = t.add_resource(ec2.Subnet(
       'SUBNET',
        CidrBlock='10.0.0.0/16',
        MapPublicIpOnLaunch='true',
        Tags=Tags(Name=Join('', ['subnet-scalability-', Ref('AWS::Region')])),
        VpcId=Ref(vpc)
    ))
    return couchbaseSubnet

def createCouchbaseSubnetRouteTableAssociation(t, subnet, routetable):
    couchbaseSubnetRouteTableAssociation = t.add_resource(ec2.SubnetRouteTableAssociation(
        'SUBNETROUTETABLEASSOCATION',
        RouteTableId=Ref(routetable),
        SubnetId=Ref(subnet)
    ))
    return couchbaseSubnetRouteTableAssociation

def createCouchbaseSecurityGroups(t, vpc):

    # Couchbase security group
    secGrpCouchbase = ec2.SecurityGroup('CouchbaseSecurityGroup')
    secGrpCouchbase.GroupDescription = "Allow access to Couchbase Server"
    secGrpCouchbase.VpcId = Ref(vpc)
    secGrpCouchbase.SecurityGroupIngress = [
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp="0.0.0.0/0",
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="8091",
            ToPort="8091",
            CidrIp="0.0.0.0/0",
        ),
        ec2.SecurityGroupRule(   # sync gw user port
            IpProtocol="tcp",
            FromPort="4984",
            ToPort="4984",
            CidrIp="0.0.0.0/0",
        ),
        ec2.SecurityGroupRule(   # sync gw admin port
            IpProtocol="tcp",
            FromPort="4985",
            ToPort="4985",
            CidrIp="0.0.0.0/0",
        ),
        ec2.SecurityGroupRule(   # expvars
            IpProtocol="tcp",
            FromPort="9876",
            ToPort="9876",
            CidrIp="0.0.0.0/0",
        )
    ]

    # Add security group to template
    t.add_resource(secGrpCouchbase)

    cbIngressPorts = [
        {"FromPort": "4369", "ToPort": "4369" },    # couchbase server
        {"FromPort": "5984", "ToPort": "5984" },    # couchbase server
        {"FromPort": "8092", "ToPort": "8092" },    # couchbase server
        {"FromPort": "11209", "ToPort": "11209" },  # couchbase server 
        {"FromPort": "11210", "ToPort": "11210" },  # couchbase server
        {"FromPort": "11211", "ToPort": "11211" },  # couchbase server
        {"FromPort": "21100", "ToPort": "21299" },  # couchbase server
    ]

    for cbIngressPort in cbIngressPorts:
        from_port = cbIngressPort["FromPort"]
        to_port = cbIngressPort["ToPort"]
        name = 'CouchbaseSecurityGroupIngress{}'.format(from_port)
        secGrpCbIngress = ec2.SecurityGroupIngress(name)
        secGrpCbIngress.GroupId = GetAtt(secGrpCouchbase, 'GroupId')
        secGrpCbIngress.IpProtocol = "tcp"
        secGrpCbIngress.FromPort = from_port
        secGrpCbIngress.ToPort = to_port
        secGrpCbIngress.SourceSecurityGroupId = GetAtt(secGrpCouchbase, 'GroupId')
        t.add_resource(secGrpCbIngress)

    return secGrpCouchbase


#
# Parameters
#
keyname_param = t.add_parameter(Parameter(
    'KeyName', Type='String',
    Description='Name of an existing EC2 KeyPair to enable SSH access'
))

couchbaseVPC = createCouchbaseVPC(t)
couchbaseInternetGateway = createCouchbaseInternetGateway(t)
couchbaseVPCGatewayAttachment = createCouchbaseVPCGatewayAttachment(t, couchbaseInternetGateway, couchbaseVPC)
couchbaseRouteTable = createCouchbaseRouteTable(t, couchbaseVPC)
couchbaseRoute = createCouchbaseRoute(t, couchbaseInternetGateway, couchbaseRouteTable)
couchbaseSubnet = createCouchbaseSubnet(t, couchbaseVPC)
couchbaseSubnetRouteTableAssociation = createCouchbaseSubnetRouteTableAssociation(t, couchbaseSubnet, couchbaseRouteTable)
secGrpCouchbase = createCouchbaseSecurityGroups(t, couchbaseVPC)

# Couchbase Server Instances
for i in xrange(NUM_COUCHBASE_SERVERS):
    name = "couchbaseserver{}".format(i)
    instance = ec2.Instance(name)
    instance.ImageId = "ami-????"  # TODO: Add AMI
    instance.InstanceType = COUCHBASE_INSTANCE_TYPE
    instance.SecurityGroupIds = [GetAtt(secGrpCouchbase, 'GroupId')]
    instance.SubnetId = Ref(couchbaseSubnet)
    instance.KeyName = Ref(keyname_param)
    instance.Tags=Tags(Name=name, Type="couchbaseserver")

#    instance.BlockDeviceMappings = [
#        ec2.BlockDeviceMapping(
#            DeviceName = "/dev/sda1",
#            Ebs = ec2.EBSBlockDevice(
#                DeleteOnTermination = True,
#                VolumeSize = 60,
#                VolumeType = "gp2"
#            )
#        )
#    ]
    t.add_resource(instance)

print(t.to_json())
