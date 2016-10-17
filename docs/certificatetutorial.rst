Certificate usage tutorial
===========================

Below is the procedure to generate test certificates, and similar example certificates are distributed among the examples. The example server certificate holds the host name, and assumes that the broker is running on 'localhost'. Note that the settings are optimized for being an easy-to-use example, rather than production strength security.

Certificate Authority
--------------------------
Generate a private key for the CA (certificate authority)::
 
    $ openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out ca_private_key.pem
 

Generate the public CA certificate::
 
    $ openssl req -new -x509 -days 3650 -key ca_private_key.pem -subj "/C=SE/O=TEST" -out ca_public_certificate.pem
 

Server certificate
----------------------------
Generate a private key for the server::
 
    $ openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out server_private_key.pem 
 

The server certificate will have the host name as its CN (Common Name), and this must be the address that clients connects to. It can be for example "www.example.com", "11.22.33.44" or "localhost". When deploying the server in different locations you need to adapt this (the certificate must be re-generated if the broker IP-number is changed). A few examples are given below.

Request a server certificate from the CA::
 
    $ openssl req -new -key server_private_key.pem -subj "/C=SE/O=TEST/CN=192.168.0.3" -out server_request.csr
    $ openssl req -new -key server_private_key.pem -subj "/C=SE/O=TEST/CN=localhost"   -out server_request.csr
 

The CA issues a server certificate::
 
    $ openssl x509 -req -in server_request.csr -CA ca_public_certificate.pem -CAkey ca_private_key.pem -days 3650 -CAcreateserial -out server_public_certificate.pem
 
Note that is the first time the CA generates a certificate. We ask it to
create a file for keeping track of serial numbers (using the -CAcreateserial flag).

Now the ``.csr`` file can be removed.


Taxisign resource certificate
---------------------------------------
Generate a private key for the taxi sign::
 
    $ openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out taxisign_private_key.pem
 

Request a (taxi sign) client certificate from the CA. The Common Name (CN) must be unique among the clients to the broker, as we use it as the username::
 
    $ openssl req -new -key taxisign_private_key.pem -subj "/C=SE/O=TEST/CN=taxisign" -out taxisign_request.csr
 

The CA issues a (taxi sign) client certificate::
 
    $ openssl x509 -req -in taxisign_request.csr -CA ca_public_certificate.pem -CAkey ca_private_key.pem -days 3650 -CAserial ca_public_certificate.srl -out taxisign_public_certificate.pem
 

Taxisign app certificate
---------------------------------------
Generate a private key for the taxi app::
 
    $ openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out taxiapp_private_key.pem
 

Request a (taxi app) client certificate from the CA::
 
    $ openssl req -new -key taxiapp_private_key.pem -subj "/C=SE/O=TEST/CN=taxiapp" -out taxiapp_request.csr
 

The CA issues a (taxi app) client certificate::
 
    $ openssl x509 -req -in taxiapp_request.csr -CA ca_public_certificate.pem -CAkey ca_private_key.pem -days 3650 -CAserial ca_public_certificate.srl -out taxiapp_public_certificate.pem
 

Force the Mosquitto broker to use certificates
----------------------------------------------------
Use a modified mosquitto.conf file::
 
    port 8883
    cafile ca_public_certificate.pem
    certfile server_public_certificate.pem
    keyfile server_private_key.pem
    require_certificate true
    use_identity_as_username true

    #acl_file acl.txt

    #listener 1883
    #allow_anonymous true
 
(If you un-comment the two last lines also non-encrypted connections are accepted)

Start Mosquitto from the directory with the configutation and certificate files::
 
    SecureGateway/examples/servercertificates$ mosquitto -c mosquitto.conf
 

Testing the certificates from command line
-------------------------------------------------
For the clients, put the key and certificate files in a subfolder. Rename the files to:

 * public_certificate.pem
 * private_key.pem
 
Also put a copy of the ca_public_certificate.pem in each clients' subfolders.

Test that the broker rejects communication without certificates::
 
    $ mosquitto_sub -v -t +/# 
 

The moquitto_sub command is accepting certificate files. When using it with certificates, the host IP address must be given exactly as in the certificate file. If not given, the mosquitto_sub will assume that the host is 'localhost' and thus the certificate must have been generated for this host name. Otherwise you must give the hostname/IPnumber explicitly to mosquitto_sub.

You can connect two clients to the broker like this, if you have 'localhost' as CN in the server/broker certificate::
 
    SecureGateway/examples/taxisignapp/certificates$     mosquitto_sub -v -t +/# -h localhost -p 8883 --cafile ca_public_certificate.pem --cert public_certificate.pem --key private_key.pem 
    SecureGateway/examples/taxisignservice/certificates$ mosquitto_sub -v -t +/# -h localhost -p 8883 --cafile ca_public_certificate.pem --cert public_certificate.pem --key private_key.pem 
 

With a broker running on a server with IP 192.168.0.3, and the server certificate has been generated for that IPnumber::
 
    SecureGateway/examples/taxisignapp/certificates$     mosquitto_sub -v -t +/# -h 192.168.0.3 -p 8883 --cafile ca_public_certificate.pem --cert public_certificate.pem --key private_key.pem 
    SecureGateway/examples/taxisignservice/certificates$ mosquitto_sub -v -t +/# -h 192.168.0.3 -p 8883 --cafile ca_public_certificate.pem --cert public_certificate.pem --key private_key.pem
 

You can also use one mosquitto_pub and one mosquitto_sub to send command line messages between terminal windows.

If you do not want mosquitto_sub to check the server certificate to the server hostname, give the --insecure flag to mosquitto_sub. For example::
 
    $ mosquitto_sub -v -t +/# -h localhost --insecure -p 8883 --cafile ca_public_certificate.pem --cert public_certificate.pem --key private_key.pem 
 

With the setting "require_certificate false" in the mosquitto.conf file, do not give the --cafile --cert --key options to mosquitto_sub. (Otherwise it will give "Connection Refused: bad user name or password.")

Run the taxisignservice and taxisign app using certificates
-----------------------------------------------------------------
After starting the certificate-enabled broker, run this in two separate terminal windows::
 
    SecureGateway/examples/taxisignapp$     python3 taxisignapp.py     -mode graphical -host localhost -port 8883 -cert certificates/
    SecureGateway/examples/taxisignservice$ python3 taxisignservice.py -mode graphical -host localhost -port 8883 -cert certificates/
 
All distributed example apps and resources can use certificates.
