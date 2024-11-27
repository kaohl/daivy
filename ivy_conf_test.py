#!/bin/env python3

import unittest
import xml.etree.ElementTree as ET
import ivy_cache_resolver as ivy

# ATTENTION
# It is important that each test runs with its own
# cache instance to make tests independent. However,
# they do share the ivy-cache on disk to reduce
# network traffic.

class ConfBuilder:
    def __init__(self, confs_builder):
        self._confs_builder = confs_builder
        self._attrs         = {}

    def attr(self, name, value):
        self._attrs[name] = value
        return self

    def name(self, name):
        self.attr('name', name)
        return self

    def visibility(self, vis):
        self.attr('visibility', vis)
        return self

    def extends(self, extends):
        self.attr('extends', extends)
        return self

    def build(self):
        self._confs_builder.add_conf(self._attrs)
        return self._confs_builder

class ConfsBuilder:
    def __init__(self):
        self._configurations_xml = ET.Element('configurations')

    def add_conf(self, attrs):
        ET.SubElement(self._configurations_xml, 'conf', attrs)
        return self

    def conf(self):
        return ConfBuilder(self)

    def build(self):
        return ivy.MasterConfigs.from_xml(self._configurations_xml)

class ConfTest(unittest.TestCase):

    def assert_config(self, exp, act):
        self.assertEqual(exp.name, act.name)
        self.assertEqual(exp.extends, act.extends)
        self.assertEqual(exp.visibility, act.visibility)
        self.assertEqual(exp.transitive, act.transitive)

    def assert_configs(self, exp, act):
        with self.subTest():
            self.assertEqual(len(exp._configs), len(act._configs))

        with self.subTest():
            self.assertTrue(act.config() == act.config('default'))
            self.assertTrue(exp.config() == exp.config('default'))
            self.assert_config(exp.config(), act.config())

        for name, config in act._configs.items():
            with self.subTest(name = name):
                self.assert_config(exp.config(name), config)

    def assert_module_configs(self, id, expected_configs):
        cache  = ivy.Cache()
        module = cache.resolve_module(id)
        self.assert_configs(expected_configs, module.configs)

    def test_confs_commons_cli_1_4(self):
        confs = ConfsBuilder()
        confs.conf().name('default').extends('runtime,master').build()
        confs.conf().name('master').build()
        confs.conf().name('compile').build()
        confs.conf().name('provided').build()
        confs.conf().name('runtime').extends('compile').build()
        confs.conf().name('test').extends('runtime').build()
        confs.conf().name('system').build()
        confs.conf().name('sources').build()
        confs.conf().name('javadoc').build()
        confs.conf().name('optional').build()

        self.assert_module_configs(ivy.ID('commons-cli', 'commons-cli', '1.4'), confs.build())

if __name__ == '__main__':
    unittest.main()

