Other info
=============


Network discovery
-------------------

TODO!
For the client to find the IP number of the broker, the Avahi system can be used. The broker publishes its connection information, and the clients search for this information.

Description 

installation

Command line usage

Taxi sign app with startup script for node discovery.


Making apps for Android
-----------------------
Making a simple Android application to control a hardware taxi sign using MQTT protocol


Create a new Android project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Create a simple Android application from the editor of your choice. A simple app with a MainActivity is fine.

Setup necessary Android permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Navigate to the Android Manifest file of your project and add the following permissions:

.. code-block:: xml

    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.BROADCAST_STICKY"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>

MainActivity
~~~~~~~~~~~~

A number of steps is required to the source code of the MainActivity file.

1. Extend the Activity to implement MQTTCallBack

.. code-block:: java

    public class MainActivity extends Activity implements MqttCallback {

The editor will automatically add 3 unimplemented methods

.. code-block:: java

   @Override
    public void connectionLost(Throwable throwable) {

    }

   @Override
    public void messageArrived(final String topic, MqttMessage message) {

   }
   @Override
    public void deliveryComplete(IMqttDeliveryToken iMqttDeliveryToken) {

   }

2. Declare all the necessary variables

.. code-block:: java

    /* MQTT  required variables */
    String clientId = "MobileApp";
    MemoryPersistence persistence = new MemoryPersistence();
    MqttClient mqttClient;

    /* MQTT subscribe and publish topics */
    String taxi_subscribe_mqtt_topic_presence = "resourceavailable/taxisignservice/presence";
    String taxi_subscribe_mqtt_topic = "data/taxisignservice/state";
    String publish_mqtt_topic = "command/taxisignservice/state";

    /* Android UI Elements */
    ToggleButton toggleTaxiSighSwitch;
    ImageView imageViewTaxiSign;
    TextView tvSecureGateAway;
    ImageView imView_semcon_icon_bottom;

3. Create the Client

.. code-block:: java

   public void create_MQTT_Client() {
      ApplicationLayer app = (ApplicationLayer) getApplicationContext();
      String brokers_ip = app.getBrokers_ip();
      String secure_gateway_broker = "tcp://"+ brokers_ip + ":1883";

            try {
                mqttClient = new MqttClient(secure_gateway_broker, clientId, persistence);
                MqttConnectOptions mqttConnOpt = new MqttConnectOptions();
                mqttConnOpt.setCleanSession(true);
                mqttClient.setCallback(this);
                mqttClient.connect();
                mqttClient.subscribe(taxi_subscribe_mqtt_topic);
                mqttClient.subscribe(taxi_subscribe_mqtt_topic_presence);
            }
            catch (MqttException e) {
                e.printStackTrace();
            }
    }

Note: The client should be called inside the Activity function so it will be bound with the same UI Thread.

4. Create the methods to send MQTT messages

.. code-block:: java

     public void send_MQQT_Message(String topic, String payLoad) {
            try {
                MqttMessage message = new MqttMessage(payLoad.getBytes());
                mqttClient.publish(topic, message);
            } catch (MqttException me) {
                me.printStackTrace();
            }
        }

5. Create a switch statement to handle the different received messages. The topics that the client is subscribed to are the ones declared on step 2. The statement must be inside the messageArrived function we added at step 1.

.. code-block:: java

    @Override
    public void messageArrived(final String topic, MqttMessage message) {
        final String received_message = message.toString();
        MainActivity.this.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (topic.equals(taxi_subscribe_mqtt_topic_presence)) {
                    if(received_message.equals("True")){
                    imageViewTaxiSign.setBackgroundResource(R.drawable.taxi_sign_off);
                    toggleTaxiSighSwitch.setEnabled(true);
                    toggleTaxiSighSwitch.setText("\n" + "Taxi Sign");
                    }
                    else if(received_message.equals("False")){
                    imageViewTaxiSign.setBackgroundResource(R.drawable.taxi_sign_offline);
                    toggleTaxiSighSwitch.setEnabled(false);
                    toggleTaxiSighSwitch.setText("\n" + "Taxi Sign");
                    }
                 }
                else if(topic.equals(taxi_subscribe_mqtt_topic)){
                    if(received_message.equals("False")) {
                        imageViewTaxiSign.setBackgroundResource(R.drawable.taxi_sign_off);
                        toggleTaxiSighSwitch.setChecked(false);
                        toggleTaxiSighSwitch.setText("\n" + "Taxi Sign");
                    }
                    else if(received_message.equals("True")) {
                        imageViewTaxiSign.setBackgroundResource(R.drawable.taxi_sign_on);
                        toggleTaxiSighSwitch.setChecked(true);
                        toggleTaxiSighSwitch.setText("\n" + "Taxi Sign");
                    }
                }
            }

        });
    }

6. Final step in the MainActivity is to add the on-click Listeners on the buttons in order to control the sign.

.. code-block:: java

     toggleTaxiSighSwitch = (ToggleButton) findViewById(R.id.switch1);
            toggleTaxiSighSwitch.setText("\n" + "Taxi Sign");
            toggleTaxiSighSwitch.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
                public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                    if (isChecked) {
                        toggleTaxiSighSwitch.setOnClickListener(new View.OnClickListener() {
                            @Override
                            public void onClick(View v) {
                                send_MQQT_Message(publish_mqtt_topic, "True");
                                imageViewTaxiSign.setBackgroundResource(R.drawable.taxi_sign_on);
                            }
                        });
                    } else {
                        toggleTaxiSighSwitch.setOnClickListener(new View.OnClickListener() {
                            @Override
                            public void onClick(View v) {
                                send_MQQT_Message(publish_mqtt_topic, "False");
                                imageViewTaxiSign.setBackgroundResource(R.drawable.taxi_sign_off);
                            }
                        });
                    }
                }
            });

            imageViewTaxiSign = (ImageView) findViewById(R.id.imTop);
            imageViewTaxiSign.setBackgroundResource(R.drawable.taxi_sign_offline);

            tvSecureGateAway = (TextView) findViewById(R.id.tvsecureGateway);
            tvSecureGateAway.setText(getResources().getString(R.string.txView));

            imView_semcon_icon_bottom = (ImageView) findViewById(R.id.imageView2);
            imView_semcon_icon_bottom.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    Intent intent = new Intent(getApplicationContext(), SettingsActivity.class);
                    startActivity(intent);
                }
            });

7. Finally create the simple layout that contains all the buttons.

.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>
    <RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:background="@color/white"
        android:orientation="vertical"
        android:weightSum="1">

        <ImageView
            android:id="@+id/imTop"
            android:layout_gravity="center"
            android:layout_width="540dp"
            android:layout_height="180dp"
            android:layout_alignParentTop="true"
            android:layout_centerHorizontal="true"
            android:layout_marginTop="130dp" />

        <ToggleButton
            android:layout_width="180dp"
            android:layout_height="320dp"
            android:id="@+id/switch1"
            android:enabled="false"
            android:textSize="25dp"
            android:textColor="@color/gray"
            android:gravity="center|bottom"
            android:background="@drawable/toggle_button_selector"
            android:layout_centerVertical="true"
            android:layout_centerHorizontal="true"
            />

        <ImageView
            android:layout_width="250dp"
            android:layout_height="120dp"
            android:src="@drawable/sg_transparent"
            android:id="@+id/imageView"
            android:layout_below="@+id/switch1"
            android:layout_alignParentLeft="true"
            android:layout_alignParentStart="true"
            android:layout_marginTop="45dp" />

        <TextView
            android:layout_width="500dp"
            android:layout_height="wrap_content"
            android:gravity="left"
            android:textSize="20dp"
            android:layout_marginLeft="200dp"
            android:id="@+id/tvsecureGateway"
            android:layout_alignTop="@+id/imageView"
            android:layout_alignParentLeft="true"
            android:layout_alignParentStart="true" />

        <ImageView
            android:layout_width="wrap_content"
            android:layout_height="20dp"
            android:src="@drawable/semocon_logo_buttom"
            android:layout_alignParentBottom="true"
            android:layout_alignParentLeft="true"
            android:layout_alignParentStart="true"
            android:layout_marginBottom="40dp"
            android:id="@+id/imageView2" />

    </RelativeLayout>


Introduction to access control lists
-------------------------------------

The certificates discussed above handle the authentication, which identifies each client (and the server/broker).

Authorization is about defining which client should be allowed to what
and is handled by access control lists (ACL) in the Mosquitto broker.

To test the ACL functionality add this line in the mosquitto.conf file::
 
    acl_file acl.txt
 

With this ACL file, the only valid topic is ``a/b/c``::
 
    topic readwrite a/b/c
 
The permission can be ``read``, ``write`` or ``readwrite``.

If a username is given, the ``topic`` rows below it are valid for that user only. For example::
 
    user foo
    topic readwrite a/b/c

    user bar    
    topic read a/b/c
 

Start mosquitto without certificates, but with the ACL functionality enabled that was defined
above. Run this in two separate windows::
 
    $ mosquitto_sub -t +/# -v -u bar
    $ mosquitto_pub -t a/b/c -m 123 -u foo
 
Then try to run the same again, but with two usernames swapped.

It can be useful to run the mosquitto broker with the ``-v`` flag,
to see the details of the communication.


Dynamically change access to applications
---------------------------------------------
TODO!

 Dynamically change access to application
