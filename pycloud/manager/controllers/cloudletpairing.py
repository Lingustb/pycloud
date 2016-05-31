# KVM-based Discoverable Cloudlet (KD-Cloudlet)
# Copyright (c) 2015 Carnegie Mellon University.
# All Rights Reserved.
#
# THIS SOFTWARE IS PROVIDED "AS IS," WITH NO WARRANTIES WHATSOEVER. CARNEGIE MELLON UNIVERSITY EXPRESSLY DISCLAIMS TO THE FULLEST EXTENT PERMITTEDBY LAW ALL EXPRESS, IMPLIED, AND STATUTORY WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT OF PROPRIETARY RIGHTS.
#
# Released under a modified BSD license, please see license.txt for full terms.
# DM-0002138
#
# KD-Cloudlet includes and/or makes use of the following Third-Party Software subject to their own licenses:
# MiniMongo
# Copyright (c) 2010-2014, Steve Lacy
# All rights reserved. Released under BSD license.
# https://github.com/MiniMongo/minimongo/blob/master/LICENSE
#
# Bootstrap
# Copyright (c) 2011-2015 Twitter, Inc.
# Released under the MIT License
# https://github.com/twbs/bootstrap/blob/master/LICENSE
#
# jQuery JavaScript Library v1.11.0
# http://jquery.com/
# Includes Sizzle.js
# http://sizzlejs.com/
# Copyright 2005, 2014 jQuery Foundation, Inc. and other contributors
# Released under the MIT license
# http://jquery.org/license
__author__ = 'Keegan'

import logging
import time
import random
import os


from pylons import request, response, session, tmpl_context as c
from pylons import app_globals

from pycloud.pycloud.pylons.lib.base import BaseController
from pycloud.manager.lib.pages import CloudletPairingPage
from pycloud.manager.lib.pages import CloudletDiscoveryPage
from pycloud.pycloud.ska.wifi_ska_device import WiFiSKADevice
from pycloud.pycloud.pylons.lib import helpers as h

from pycloud.pycloud.model.deployment import Deployment

from pycloud.pycloud.utils import ajaxutils
from pycloud.pycloud.pylons.lib.util import asjson

import subprocess

log = logging.getLogger(__name__)

################################################################################################################
# Controller for the Pairing page.
################################################################################################################
class CloudletPairingController(BaseController):

    ############################################################################################################
    # Entry point.
    ############################################################################################################
    def GET_index(self):
        return self.GET_pair()

    ############################################################################################################
    # Displays the connection to cloudlet page
    ############################################################################################################
    def GET_pair(self):
        page = CloudletPairingPage()

        # TODO: Generate secret to display
        temp = ''.join(random.sample(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"], 6))
        page.secret = temp #secret should be alphanumeric and 6 symbols long

        return page.render()

    ############################################################################################################
    # Does the work after data is entered
    ############################################################################################################
    def POST_pair(self):
        device_type = 'cloudlet'
        curr_device = None
        try:
            # Create a device depending on the type.
            #port = request.params.get('port', None)
            #name = request.params.get('name', None)
            id = "10.10.10.10"
            port = "1723"
            name = "WiFi1"
            curr_device = WiFiSKADevice({'host': id, 'port': int(port), 'name': name})
            curr_device.listen()

            # Now the pairing process will be followed, generating all required credentials.
            # The first step is to connect to the device.
            successful_connection = curr_device.connect()
            if not successful_connection:
                raise Exception("Could not connect to cloudlet with id {}.".format(id))

            # Get the device id.
            id_data = curr_device.get_data({'device_id': 'none'})
            device_internal_id = id_data['device_id']
            print 'Device id: ' + device_internal_id

            # Pair the device, send the credentials, and clear their local files.
            deployment = Deployment.get_instance()
            device_keys = deployment.pair_device(device_internal_id, curr_device.get_name(), device_type)
            deployment.send_paired_credentials(curr_device, device_keys)
            deployment.clear_device_keys(device_keys)
        except Exception, e:
            print str(e)
            raise e
        finally:
            if curr_device is not None:
                try:
                    print 'Closing connection.'
                    curr_device.disconnect()
                except Exception, e:
                    error = "Error closing connection with device: " + str(e)
                    print error
                    raise Exception(error)

        return h.redirect_to(controller='devices', action='list')

    ############################################################################################################
    # Displays the discover page for cloudlet pairing.
    ############################################################################################################
    def GET_discover(self):
        page = CloudletDiscoveryPage()

        # TODO: Generate ssid and random psk here
        temp = ''.join(random.sample(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"], 6))
        host = os.uname()[1]
        page.ssid = host + "-" + temp #ssid should be "<cloudlet machine name>-<alphanumeric and 6 symbols long>"
        psk = ''.join(random.sample(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"], 6))
        page.psk = psk #psk should be alphanumeric and 6 symbols long
        command = "sed -ie \"s/xxxxxx/" + page.ssid + "/g\" hostapd/hostapd-nic.conf"
        cmd = subprocess.Popen(command, shell=True, stdout=None)
        command = "sed -ie \"s/yyyyyy/" + page.psk + "/g\" hostapd/hostapd-nic.conf"
        cmd = subprocess.Popen(command, shell=True, stdout=None)

        return page.render()

    ############################################################################################################
    # Does the wrk after data is entered
    ############################################################################################################
    def POST_discover(self):
        # Generate secret to display
        secret = request.params.get('secret', None)
        ssid = request.params.get('ssid', None)
        psk = request.params.get('psk', None)

        command = "wpa_passphrase " + ssid + " " + psk + ">hostapd/wpa.conf"
        cmd = subprocess.Popen(command, shell=True, stdout=None)
        command = "wpa_supplicant -Dwext -iwlan0 -chostapd/wpa.conf"
        cmd = subprocess.Popen(command, shell=True, stdout=None)

        return h.redirect_to(controller='devices', action='list')