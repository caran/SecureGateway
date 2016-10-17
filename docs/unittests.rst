Unittests and integration tests
===============================

In order to run the tests, you need to install sgframework, for example in
development mode (symbolic links to source)::

    $ sudo make develop

All dependencies, also for the examples must be installed.

Enable the virtual can bus::

    $ sudo make vcan

Make sure that Mosquitto MQTT broker is running.

Run the core tests (also on an embedded Linux board, for example a Beaglebone)::

    $ make test

In order to also test the graphical example apps, use::

    $ make test-all


To run individual test files, execute them from the project root directory (for example)::

    $ python3 tests/test_framework_resource.py

If you would like to run a single test case in a test file, adjust the ``if __name__ == '__main__':`` section of the file.


Test documentation for core framework
-------------------------------------

.. automodule:: tests.test_framework_app
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:

.. automodule:: tests.test_framework_resource
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:


Test documentation for scripts
--------------------------------

.. automodule:: tests.test_canadapter
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:

.. automodule:: tests.test_servicemanager
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:


Test documentation for minimal examples
----------------------------------------

.. automodule:: tests.test_minimal_taxisign
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:

.. automodule:: tests.test_minimal_taxiapp
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:


Test documentation for elaborate examples
------------------------------------------

.. automodule:: tests.test_vehiclesimulator
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:

.. automodule:: tests.test_climateapp
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:

.. automodule:: tests.test_taxisignservice
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:

.. automodule:: tests.test_taxisignapp
    :members:
    :no-private-members:
    :noindex:
    :undoc-members:
