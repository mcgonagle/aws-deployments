#!/usr/bin/env python 

DOCUMENTATION = '''
---
module: bigip_cluster
short_description: "Manages F5 BIG-IP Device Services Clusters"
description:
    - "Manages F5 BIG-IP Device Services Clusters"
version_added: "X.X"
author: Alex Applebaum
notes:
    - "Requires BIG-IP software version >= 11"
    - "Best run as a local_action in your playbook"
requirements:
    - bigsuds 
options:
    hostname:
        description:
            - BIG-IP host sending API requests to
        required: true
        default: null
        choices: []
        aliases: []
    user:
        description:
            - BIG-IP username
        required: true
        default: null
        choices: []
        aliases: []
    password:
        description:
            - BIG-IP password
        required: true
        default: null
        choices: []
        aliases: []
    state:
        description:
            - cluster state
        required: false
        default: present
        choices: ['present', 'absent']
        aliases: []
    action:
        description:
            - configure device object, cluster devices or create a traffic group
              "device" should be run on each device. 
              "cluster" should be run on a seed device.
              "traffic_group" should be run on a seed device
        required: false
        default: cluster
        choices: ['device', 'cluster', 'traffic_group' ]
        aliases: []
    devices:
        description:
            - device object names of devices you want to cluster together. Should match dns hostname.
        required: false
        default: null
        choices: []
        aliases: []
    devices_mgmt_ips:
        description:
            - mgmt ips of devices you want to cluster together
        required: false
        default: null
        choices: []
        aliases: []
    device_name:
        description:
            - device object name of device you want to configure
        required: false
        default: null
        choices: []
        aliases: []
    failover_addr:
	description:
	    - IP address used for Failover (required) 
	required: false
	default: none
	choices: []
	aliases:
    configsync_addr:
	description:
	    - IP address used for Config Sync
	required: false
	default: none
	choices: []
	aliases:
    primary_mirror_addr:
	description:
	    - Primary Mirror Address
	required: false
	default: none
	choices: []
	aliases:
    secondary_mirror_addr:
	description:
	    - Secondary Mirror Address
	required: false
	default: none
	choices: []
	aliases:
    traffic_group_name:
	description:
	    - traffic group name 
	required: false
	default: None
	choices: []
	aliases: []
    traffic_group_count:
	description:
	    - FUTURE: traffic group count.  
	required: false
	default: None
	choices: []
	aliases: []


'''

EXAMPLES = '''

## playbook task examples:

---
# file cluster.yml
# ...
- hosts: localhost
  tasks:

  - name: Configure LB1 Device Object
    bigip_cluster:
	hostname: lb1.mydomain.com
	username: admin
	password: mysecret
	state: present
	action: device
	device_name: lb1.mydomain.com
	failover_addr:  10.0.2.201
	configsync_addr:  10.0.2.201
	primary_mirror_addr: 10.0.2.201
	secondary_mirror_addr: 10.0.3.201

  - name: Configure LB2 Device Object
    bigip_cluster:
	hostname: lb1.mydomain.com
	username: admin
	password: mysecret
	state: present
	action: device
	device_name: lb2.mydomain.com
	failover_addr:  10.0.2.202
	configsync_addr:  10.0.2.202
	primary_mirror_addr: 10.0.2.202
	secondary_mirror_addr: 10.0.3.202


  - name: Simple create cluster
    bigip_cluster:
	hostname: lb1.mydomain.com
	username: admin
	password: mysecret
	state: present
	action: cluster
	devices: [ lb1.mydomain.com, lb2.mydomain.com ]
	devices_mgmt_ips: [ 10.0.0.201, 10.0.0.202 ]

  # NOT IMPLEMENTED YET
  - name: Simple delete cluster
    bigip_cluster:
	hostname: lb1.mydomain.com
	username: admin
	password: mysecret
	state: absent
	action: cluster
	devices: [ lb1.mydomain.com, lb2.mydomain.com ]
	devices_mgmt_ips: [ 10.0.0.201, 10.0.0.202 ]

  - name: Create a second traffic group
    bigip_cluster:
	hostname: lb1.mydomain.com
	username: admin
	password: mysecret
	state: present
	action: traffic_group
	traffic_group_name: traffic-group-2

  # NOT IMPLEMENTED YET
  - name: Delete a traffic group
    bigip_cluster:
	hostname: lb1.mydomain.com
	username: admin
	password: mysecret
	state: absent
	action: traffic_group
	traffic_group_name: traffic-group-2

  # NOT IMPLEMENTED YET
  - name: Create lots of traffic groups (current max = 127 ): NOT IMPLEMENTED YET
    bigip_cluster:
	hostname: lb1.mydomain.com
	username: admin
	password: mysecret
	state: present
	action: traffic_group
	traffic_group_count: 127

'''

import os
import sys
import json

# Need to add absolute path to library so python can find it
# https://github.com/ansible/ansible/issues/4083
# ex. can't use pwd as ansible actually runs module in a tmp directory
# /home/vagrant/.ansible/tmp/ansible-tmp-1438633710.7-121872048074041/bigip_cluster
# hopefully this directory is unique
# aws_deployments_path = os.path.abspath("/aws-deployments/library")
# sys.path.append(aws_deployments_path)

import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import bigsuds


def main():

    changed = False

    # grab connection args from bigip.py util
    argument_spec = bigip_argument_spec()
    
    # add cluster specific args
    argument_spec.update(
        dict(
            state=dict(type='str', choices=['present', 'absent'], required=True),
            action=dict(type='str', choices=['device','cluster', 'traffic_group'],  required=True),
            devices=dict(type='list', aliases=['members']),
            devices_mgmt_ips=dict(type='list'),
            device_group_name=dict(type='str', default=None),
            device_name=dict(type='str', default=None),
            failover_addr=dict(type='str', default=None),
            configsync_addr=dict(type='str', default=None),
            primary_mirror_addr=dict(type='str', default=None),
            secondary_mirror_addr=dict(type='str', default=None),
            traffic_group_name=dict(type='str', default=None),
            traffic_group_count=dict(type='str', default=None),
            )
    )


    module = AnsibleModule(
        argument_spec = argument_spec,
    )

    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']
    timeout = module.params['timeout']
    address_isolation = module.params['address_isolation']
    strict_route_isolation = module.params['strict_route_isolation']

    state = module.params['state']
    action = module.params['action']
    devices = module.params['devices']
    devices_mgmt_ips = module.params['devices_mgmt_ips']
    device_group_name = module.params['device_group_name']
    device_name = module.params['device_name']
    failover_addr = module.params['failover_addr']
    configsync_addr = module.params['configsync_addr']
    primary_mirror_addr = module.params['primary_mirror_addr']
    secondary_mirror_addr = module.params['secondary_mirror_addr']
    traffic_group_name = module.params['traffic_group_name']
    traffic_group_count = module.params['traffic_group_count']

    result = {'changed' : False }

    if state is 'device': 
	if device_name is None:
	    module.fail_json(msg='device_name is required when creating device object. Best practices is for it to be the hostname')
	if failover_addr is None:
	    module.fail_json(msg='failover address is required when creating device object')
	if configsync_addr is None:
	    module.fail_json(msg='config_sync address is required when creating device object')

    if state is 'cluster': 
	if devices is None:
	    module.fail_json(msg='device object names are required when creating a cluster. device object names are usually the hostname')


    try:
        # Initalize the bigsuds connection object to SEED node
        bigip_obj = bigsuds.BIGIP(
                    hostname = hostname,
                    username = username,
                    password = password,
                    )
    except Exception, e:
           print e

    try: 
	if action == 'device':
	
           existing_device_name = bigip_obj.Management.Device.get_local_device()
	   # print json.dumps({"existing_device_name": existing_device_name,
           #                 "device_name": device_name})
	   if existing_device_name != ("/Common/" + device_name):
                # have to reset device trust to set the proper device-name
                bigip_obj.Management.Trust.reset_all(
                                        device_object_name = device_name,
                                        keep_current_authority = 'true',
                                        authority_cert = '',
                                        authority_key = '',
                                      )

	        result = { "changed": True, "Resetting Device Trust" : True }
		time.sleep(15)

	   # Begin Setting HA Channel Properities
          
           # Set ConfigSync Address 
           bigip_obj.Management.Device.set_configsync_address( devices = [device_name], addresses = [configsync_addr] )

           # Set Failover Address
	   fo_ints = [ failover_addr ]
	   unicast_objs = []
	   for i in range(len(fo_ints)):
		unicast_obj = {
				'source'    : { 'address' : fo_ints[i], 'port' : 1026 },
				'effective' : { 'address' : fo_ints[i], 'port' : 1026 }
			      }
		unicast_objs.append(unicast_obj)

	   bigip_obj.Management.Device.set_unicast_addresses(
							devices =   [device_name],
                                                        addresses = [unicast_objs]
                                                    )
 	  
           # Set Mirror Addresses
           if primary_mirror_addr:
                bigip_obj.Management.Device.set_primary_mirror_address(
                                                            devices = [device_name],
                                                            addresses = [primary_mirror_addr]
                                                        )
           if secondary_mirror_addr:
                bigip_obj.Management.Device.set_secondary_mirror_address(
                                                            devices = [device_name],
                                                            addresses = [secondary_mirror_addr]
                                                        )


	   # Should do some extra validation here with some gets before returning true
	   result = { "changed": True, "Device Object Configured" : True }

	if action == 'cluster':
	    if state == 'present' and len(devices):
                peer_exists = False
                device_group_exists = False

		# Check to see if Device Trust Group exists / already contains a peer device
                existing_peers = bigip_obj.Management.Device.get_list()
                for device in existing_peers:
                    if device == devices[1]:
                         peer_exists = True
                         break

		if device_group_name == None:
		    device_group_name = "my-sync-failover-group"

		# Check to see if there's a sync failover group
		existing_device_groups = bigip_obj.Management.DeviceGroup.get_list()
                for group in existing_device_groups:
		    if group == ("/Common/" + device_group_name):
		         device_group_exists = True
                         break


		if not peer_exists:

		    ### GO TO SEED DEVICE AND CREATE CLUSTER
		    # Can potentially make which device is the seed an option.
		    # For now will be first in the list
		    for i in range(len(devices)-1):

			    bigip_obj.Management.Trust.add_authority_device(
							    address = devices_mgmt_ips[i + 1],
							    username = username,
							    password = password,
							    device_object_name = devices[i + 1],
							    browser_cert_serial_number = '',
							    browser_cert_signature = '',
							    browser_cert_sha1_fingerprint = '',
							    browser_cert_md5_fingerprint = '',
							  )


		if not device_group_exists:

		    # Create Sync-Failover Group. 
		    device_group_created = bigip_obj.Management.DeviceGroup.create(  
                                                                device_groups = [device_group_name],
                                                                types = ["DGT_FAILOVER"]
                                                                )

		    # Due to, Bug alias 479071 TG initial-placement influenced by sync-failover DG w/auto-sync enabled 
                    # either need to disaable auto-sync when first creating sync-failover-group
                    # or first offline peers before adding them 
                    bigip_obj.Management.DeviceGroup.set_autosync_enabled_state (
                                                                device_groups = [device_group_name],
                                                                states = ["STATE_DISABLED"]
                                                                )
		    
		    # Add device Sync-Failover Group. 
                    add_deivces = bigip_obj.Management.DeviceGroup.add_device(  
								  device_groups = [device_group_name],
                                                                  devices = [ devices ]
                                                                  )

		    # Initiate a Sync Request
                    sync_request = bigip_obj.System.ConfigSync.synchronize_to_group_v2(
                                                    group = device_group_name,
                                                    device = devices[0],
                                                    force = True
                                                    )

	            # Can now re-enable auto-sync  
		    bigip_obj.Management.DeviceGroup.set_autosync_enabled_state (
                                                                device_groups = [device_group_name],
                                                                states = ["STATE_ENABLED"]
                                                                )
		    
		    result = { "changed": True, "cluster_created" : True }
		else:
		    result = { "changed": False, "msg" : "Cluster already exists" }

	if action == 'traffic_group':
	
	    # exists = bigip_obj.cluster.traffic_group_exists( traffic_group_name )
	    existing_traffic_groups = bigip_obj.Management.TrafficGroup.get_list()
            for group in existing_traffic_groups:
                    if group == traffic_group_name:
                         traffic_group_exists = True
                         break	
	    
	    if not traffic_group_exists:
		# bigip_obj.cluster.create_traffic_group ( traffic_group_name ) 
                bigip_obj.Management.TrafficGroup.create( traffic_groups = [traffic_group_name] )

    except Exception, e:
	module.fail_json(msg="received exception: %s" % e)
 
    # module.exit_json(changed=changed, content=result)
    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
# import some globals/ connection vars
from bigip_utils import *

if __name__ == '__main__':
    main()