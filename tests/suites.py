import argparse
import unittest

try:
    import test_canadapter
    import test_climateapp
    import test_framework_app
    import test_framework_resource
    import test_minimal_taxiapp
    import test_minimal_taxisign
    import test_servicemanager
    import test_taxisignapp
    import test_taxisignservice
    import test_vehiclesimulator
except:
    from . import test_canadapter
    from . import test_climateapp
    from . import test_framework_app
    from . import test_framework_resource
    from . import test_minimal_taxiapp
    from . import test_minimal_taxisign
    from . import test_servicemanager
    from . import test_taxisignapp
    from . import test_taxisignservice
    from . import test_vehiclesimulator


def embedded():
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_canadapter))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_framework_app))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_framework_resource))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_minimal_taxiapp))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_minimal_taxisign))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_servicemanager))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_vehiclesimulator))
    return suite


def graphical():
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_climateapp))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_taxisignapp))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_taxisignservice))
    return suite


def alltests():
    suite = unittest.TestSuite()
    suite.addTests(embedded())
    suite.addTests(graphical())
    return suite


def main():
    EMBEDDED = 'embedded'
    GRAPHICAL = 'graphical'
    ALL = 'alltests'
    VERBOSITY = 2

    parser = argparse.ArgumentParser(description='Run some or all tests')
    parser.add_argument('-s',
                        dest='suitename',
                        choices=[EMBEDDED, GRAPHICAL, ALL],
                        default=GRAPHICAL,
                        help='The suite of tests that should be used. Defaults to: %(default)s')
    args = parser.parse_args()

    scope = globals().copy()
    suitefunction = scope.get(args.suitename)
    suite = suitefunction()

    unittest.TextTestRunner(verbosity=VERBOSITY).run(suite)


if __name__ == '__main__':
    main()
