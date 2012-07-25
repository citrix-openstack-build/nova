# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright (C) 2012 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nova import exception
from nova import test

from nova.compute import vm_mode


class ComputeVMModeTest(test.TestCase):

    class testinstance(object):
        def __init__(self, mode):
            self.vm_mode = mode

    def test_case(self):
        inst = ComputeVMModeTest.testinstance("HVM")
        mode = vm_mode.get_from_instance(inst)
        self.assertEqual(mode, "hvm")

    def test_legacy_pv(self):
        inst = ComputeVMModeTest.testinstance("pv")
        mode = vm_mode.get_from_instance(inst)
        self.assertEqual(mode, "xen")

    def test_legacy_hv(self):
        inst = ComputeVMModeTest.testinstance("hv")
        mode = vm_mode.get_from_instance(inst)
        self.assertEqual(mode, "hvm")

    def test_bogus(self):
        inst = ComputeVMModeTest.testinstance("wibble")

        self.assertRaises(exception.Invalid,
                          vm_mode.get_from_instance,
                          inst)

    def test_good(self):
        inst = ComputeVMModeTest.testinstance("hvm")
        mode = vm_mode.get_from_instance(inst)
        self.assertEqual(mode, "hvm")
