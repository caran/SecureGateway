import time

import sgframework


def on_taxisign_state_data(app, messagetype, servicename, signalname, payload):
    if payload.strip() == 'True':
        print("The taxi sign is now on.", flush=True)
    else:
        print("The taxi sign is now off.", flush=True)


app = sgframework.App('taxiapp', 'localhost')
app.register_incoming_data('taxisignservice', 'state', on_taxisign_state_data)
app.start()  # Not using threaded networking

starttime = time.time()
command_sent = False
while True:
    app.loop()

    if time.time() - starttime > 4 and not command_sent:
        print("Turning on the taxi sign from script...", flush=True)
        app.send_command('taxisignservice', 'state', 'True')
        command_sent = True
