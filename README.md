threaded-instance-cluster
=========================

This script will create a configurable group of instances into an AWS VPC.

Wait till they're running, test that they are both healthy and alive and finally execute some code in a threaded manner for each instance created. Finally when all threads are complete it will terminate all instances.
