# Copyright (c) 2013, Arista Networks, Inc. 
# All rights reserved. 
# 
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are 
# met: 
# - Redistributions of source code must retain the above copyright notice, 
# this list of conditions and the following disclaimer. 
# - Redistributions in binary form must reproduce the above copyright 
# notice, this list of conditions and the following disclaimer in the 
# documentation and/or other materials provided with the distribution. 
# - Neither the name of Arista Networks nor the names of its 
# contributors may be used to endorse or promote products derived from 
# this software without specific prior written permission. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR 
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS 
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR 
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN 
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. #
#
# collect-eos.py
#
#    Version 1.0 17/12/2013
#    Written by:
#       Sean Flack (sean@aristanetworks.com)
#
#    Revision history:
#       1.0 - initial release

'''
   DESCRIPTION
   This script should be used in conjunction with Collectd for EOS and enables
   the collection of various switch metrics via the Arista Command-API.

   INSTALLATION
   After altering this file, it should be placed in:
   /opt/collect/python/

   CONFIGURATION
   Not Applicable

   COMPATIBILITY
   Tested with EOS v4.13.0F

   LIMITATIONS
   None Known.

'''

import collectd
from jsonrpclib import Server
switch = None
platform = ''

#== Our Own Functions go here: ==#
def configer(ObjConfiguration):
   collectd.debug('Configuring Stuff')

def initer():
    global switch
    switch = Server( "http://admin:@localhost/command-api" )
    response = switch.runCmds( 1, ["show version"] )
    collectd.debug( "The switch's system MAC addess is %s" % response[0]["systemMacAddress"] )
    
def reader(input_data=None):
    metric = collectd.Values();
    intStats(metric)
    intDom(metric)
    response = switch.runCmds( 1, ["show version"] )
    #Check whether this platform supports LANZ
    global platform
    platform = response[0]["modelName"][ 4:8 ]
    if platform in ('7150', '7124', '7148' ):
        lanzTxLatency(metric)
        lanzQueueLength(metric)
        lanzDrops(metric)

def intStats(metric):
    intMetric = metric
    response = switch.runCmds( 1, ["show interfaces counters"] )
    for x in response[0]["interfaces"]:
        UcastPkts = [ 0, 0 ]
        BroadcastPkts = [ 0, 0 ]
        MulticastPkts = [ 0, 0 ]
        Discards = [ 0, 0 ]
        Octets = [ 0, 0 ]
        for y in response[0]["interfaces"][x]:
            if y.startswith('in'):
                if y[2:] == 'UcastPkts':
                    UcastPkts[0] = response[0]["interfaces"][x][y]
                elif y[2:] == 'BroadcastPkts':
                    BroadcastPkts[0] = response[0]["interfaces"][x][y]
                elif y[2:] == 'MulticastPkts':
                    MulticastPkts[0] = response[0]["interfaces"][x][y]
                elif y[2:] == 'Discards':
                    Discards[0] = response[0]["interfaces"][x][y]
                elif y[2:] == 'Octets':
                    Octets[0] = response[0]["interfaces"][x][y]
            if y.startswith('out'):
                if y[3:] == 'UcastPkts':
                    UcastPkts[1] = response[0]["interfaces"][x][y]
                elif y[3:] == 'BroadcastPkts':
                    BroadcastPkts[1] = response[0]["interfaces"][x][y]
                elif y[3:] == 'MulticastPkts':
                    MulticastPkts[1] = response[0]["interfaces"][x][y]
                elif y[3:] == 'Discards':
                    Discards[1] = response[0]["interfaces"][x][y]
                elif y[3:] == 'Octets':
                    Octets[1] = response[0]["interfaces"][x][y]
        #Dispatch the metrics
        intMetric.plugin = 'eos-interface-counters-%s' % x
        intMetric.values = BroadcastPkts
        intMetric.type = 'eos_if_BroadcastPkts'
        intMetric.dispatch()
        intMetric.values = UcastPkts
        intMetric.type = 'eos_if_UcastPkts'
        intMetric.dispatch()
        intMetric.values = MulticastPkts
        intMetric.type = 'eos_if_MulticastPkts'
        intMetric.dispatch()
        intMetric.values = Discards
        intMetric.type = 'eos_if_Discards'
        intMetric.dispatch()
        intMetric.values = Octets
        intMetric.type = 'eos_if_Octets'
        intMetric.dispatch()

def intDom(metric):
    intMetric = metric
    response = switch.runCmds( 1, ["show interfaces transceiver"] )
    for x in response[0]["interfaces"]:
        intMetric.plugin = 'eos-interface-dom-%s' % x
        for y in response[0]["interfaces"][x]:
            if y not in [ 'updateTime', 'vendorSn', 'mediaType' ]:
                intMetric.type = 'eos_dom_%s' % y
                intMetric.values = [ response[0]["interfaces"][x][y] ]
                intMetric.dispatch()

def lanzTxLatency(metric):
    intMetric = metric
    response = switch.runCmds( 1, ["show queue-monitor length limit 10 seconds tx-latency"] )
    #Check whether this platform is a 7150
    if platform == '7150':
		for x in response[0]["entryList"]:
			intMetric.plugin = 'eos-lanz'
			intMetric.plugin_instance = x["interface"]
			intMetric.type = 'eos_lanz_txLatency'
			intMetric.type_instance = 'trafficClass-%s' % x["trafficClass"]
			intMetric.time = x["entryTime"]
			intMetric.values = [ x["txLatency"] ]
			intMetric.dispatch()
        
def lanzQueueLength(metric):
    intMetric = metric
    response = switch.runCmds( 1, ["show queue-monitor length limit 10 seconds"] )
    #Check whether this platform is a 7150
    if platform == '7150':
		for x in response[0]["entryList"]:
			if x["entryType"] == 'U':
				intMetric.plugin = 'eos-lanz'
				intMetric.plugin_instance = x["interface"]
				intMetric.type = 'eos_lanz_queueLength'
				intMetric.type_instance = 'trafficClass-%s' % x["trafficClass"]
				intMetric.time = x["entryTime"]
				intMetric.values = [ x["queueLength"] ]
				intMetric.dispatch()
            
def lanzDrops(metric):
    intMetric = metric
    response = switch.runCmds( 1, ["show queue-monitor length limit 10 seconds drops"] )
    #Check whether this platform is a 7150
    if platform == '7150':
		for x in response[0]["entryList"]:
			intMetric.plugin = 'eos-lanz'
			intMetric.plugin_instance = x["interface"]
			intMetric.type = 'eos_lanz_txDrops'
			intMetric.time = x["entryTime"]
			intMetric.values = [ x["txDrops"] ]
			intMetric.dispatch()

#== Hook Callbacks, Order is important! ==#
collectd.register_config(configer)
collectd.register_init(initer)
collectd.register_read(reader)

