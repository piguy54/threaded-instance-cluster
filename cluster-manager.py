#!/usr/bin/python

from boto import ec2
import copy
import base64
import paramiko
import time
import socket
import thread
import threading

now = time.strftime("%c")

#regiom instances should launch in
region = 'eu-west-1'

conn = ec2.connect_to_region(region)

#instance type to launch
instance = 'm1.xlarge'
#ami to launch
ami = 'ami-xxxxxxxxx'
#subnet to launch instance into
subnet = 'subnet-xxxxxxx'
#security group to attach to instance, should allow ssh access from the system this runs from.
sgs = ['sg-xxxxxxx']
#your key name
ssh_key = 'key-pair'
#your private key .pem
ssh_key_file = '.pem'
#minimum number of instances to launch, script will error out if your limits do not allow this.
min_num_bots = 3
#when unsure about capacity set this to a different value, atleast min instances will launch, as many as max instances will launch.
max_num_bots = min_num_bots
#script can be used to customise the instance on startup.
script = '#!/bin/bash\napt-get install htop -y\nsudo sh -c "echo \'ubuntu  soft   nofile  1000000\' >> /etc/security/limits.conf"\n'
ssh_username = "ubuntu"
#the command to run on the instance once it is up and running. This will exit when an exit code is provided, if you intend to run multiple commands, use a script on the instances and call that from here.
ssh_command = "/home/ubuntu/script.sh"

print "starting instances"
reserve_id = conn.run_instances(ami,min_count=min_num_bots,max_count=max_num_bots,key_name=ssh_key,instance_type=instance,security_group_ids=sgs,subnet_id=subnet,user_data=script)

pending_instances = copy.deepcopy(reserve_id.instances)
while len(pending_instances) > 0:
	print 'still pending ', len(pending_instances)
	for instance in pending_instances:
		print(now + ' Instance ' + instance.id + ' still pending') 
		status = instance.update()
		if status == 'running':
			pending_instances.remove(instance)
			print(now + ' New instance ' + instance.id + ' accessible at ' + instance.private_ip_address)
	print 'sleeping'
	time.sleep(10)
			
count = len(reserve_id.instances)
time.sleep(60)

print now + "all instances are live, starting instances tests"

for instance in reserve_id.instances:
	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(instance.private_ip_address,username=ssh_username,key_filename=ssh_key_file,timeout=5)
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('uptime')
		output = ssh_stdout.readlines()
		ssh.close
	except:
		print "Connection error"
		print("instance : " + instance.id + " is still not healthy, removing from cluster")
		instance.terminate()
		reserve_id.instances.remove(instance)

#run_thread is where you define what actions you would like this instance to do. In this case we ssh to the instances and execute a shell script. We then read from stderr and stdout until we get an exit code.
		
def run_thread(ip_add):
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())	
		ssh.connect(ip_add,username=ssh_username,key_filename=ssh_key_file)
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(ssh_command)
		print "stdout"
		print ssh_stdout.read()
		print "stderr"
		print ssh_stderr.read()		
		print 'exit_code: %d' % ssh_stdout.channel.recv_exit_status()
		ssh.close

threads = []
for instance in reserve_id.instances:
	time.sleep(1)
	t = threading.Thread(target=run_thread, args=(instance.private_ip_address,))	
	threads.append(t)
	t.start()
	
for t in threads:
	t.join()

for instance in reserve_id.instances:
       instance.terminate()
