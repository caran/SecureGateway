Security usage
=============================

Certificates (signed public keys) are used in the Secure Gateway to provide authentication. The certificates are signed by a Certificate Authority (CA). Typically that is a trusted third party, but here we will create a self-signed CA.

When a client connects to the broker, the client needs three files:

 * Client certificate. This is the public key that will be sent to the broker, so that the broker can encrypt messages when sending to the client.
 * Client private key. This is used by the client to unlock encrypted messages that it receives.
 * CA (Certificate Authority) certificate. This is used by the client to verify that the broker is the one it is claiming to be. 

The broker will use a corresponding set of files.

See the separate tutorial in the examples section.


