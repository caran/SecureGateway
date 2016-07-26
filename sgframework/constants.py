# -*- coding: utf-8 -*-
#
# Author: Jonas Berg
# Copyright (c) 2016, Semcon Sweden AB
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the
#    following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,  this list of conditions and
#    the following disclaimer in the documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Semcon Sweden AB nor the names of its contributors may be used to endorse or
#    promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


## MQTT topic definitions ##
PREFIX_COMMANDAVAILABLE = "commandavailable"
PREFIX_DATAAVAILABLE = "dataavailable"
PREFIX_RESOURCEAVAILABLE = "resourceavailable"
PREFIX_DATA = "data"
PREFIX_COMMAND = "command"
SUFFIX_PRESENCE = "presence"
SUFFIX_WILDCARD_MULTILEVEL = "#"
PAYLOAD_FALSE = "False"
PAYLOAD_TRUE = "True"
ECHO_MESSAGETYPES = {PREFIX_COMMAND: PREFIX_DATA}
MQTT_TOPIC_DEPTH = 3
MQTT_TOPIC_SEPARATOR = "/"
MQTT_TOPIC_TEMPLATE = "{}/{}/{}"

CLIENT_ID_TEMPLATE = "{}-{}"

## Certificate filename definitions ##
CA_CERTS = 'ca_public_certificate.pem'
KEYFILE = 'private_key.pem'
CERTFILE = 'public_certificate.pem'

## Communication settings ##
DEFAULT_QOS = 1
DEFAULT_TIMEOUT = 1.0  # seconds
DEFAULT_KEEPALIVE_TIME = 10  # seconds  (Is converted to int)

SLEEP_START = 1.0  # seconds, for setting up subscriptions etc
SLEEP_STOP = 1.0  # seconds, for finalizing communication
SLEEP_PUBLISH = 0.00001  # seconds, for allowing the other thread to work properly
