import time

import sgframework


def on_taxisign_state_command(resource, messagetype, servicename,
                              commandname, commandpayload):
    if commandpayload.strip() == 'True':
        print("Turning on my taxi sign.", flush=True)
        return 'True'
    else:
        print("Turning off my taxi sign.", flush=True)
        return 'False'


resource = sgframework.Resource('taxisignservice', 'localhost')
resource.register_incoming_command('state',
                                   on_taxisign_state_command,
                                   defaultvalue='False',
                                   send_echo_as_retained=True)
resource.start(use_threaded_networking=True)
while True:
    time.sleep(1)
