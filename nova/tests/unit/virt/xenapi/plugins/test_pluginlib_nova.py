# Copyright (c) 2016 OpenStack Foundation
# All Rights Reserved.
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

from nova.tests.unit.virt.xenapi.plugins import plugin_test


class FakeUnplugException(Exception):
    def __init__(self, details):
        self.details = details


class PluginlibNova(plugin_test.PluginTestBase):
    def setUp(self):
        super(PluginlibNova, self).setUp()
        self.pluginlib_nova = self.load_plugin("pluginlib_nova.py")

    def test_configure_logging(self):
        name = 'fake_name'
        mock_Logger_setLevel = self.mock_patch_object(
            self.pluginlib_nova.logging.Logger, 'setLevel')
        mock_sysh_setLevel = self.mock_patch_object(
            self.pluginlib_nova.logging.handlers.SysLogHandler, 'setLevel')
        mock_Formatter = self.mock_patch_object(
            self.pluginlib_nova.logging, 'Formatter')
        mock_sysh_setFormatter = self.mock_patch_object(
            self.pluginlib_nova.logging.handlers.SysLogHandler, 'setFormatter')
        mock_Logger_addHandler = self.mock_patch_object(
            self.pluginlib_nova.logging.Logger, 'addHandler')

        self.pluginlib_nova.configure_logging(name)

        self.assertTrue(mock_Logger_setLevel.called)
        self.assertTrue(mock_sysh_setLevel.called)
        self.assertTrue(mock_Formatter.called)
        self.assertTrue(mock_sysh_setFormatter.called)
        self.assertTrue(mock_Logger_addHandler.called)

    def test_exists(self):
        fake_args = {'k1': 'v1', 'k2': 'v2'}

        def _test_exists_ok():
            self.assertEqual('v1', self.pluginlib_nova.exists(fake_args, 'k1'))

        def _test_exists_exception():
            self.assertRaises(self.pluginlib_nova.ArgumentError,
                              self.pluginlib_nova.exists,
                              fake_args,
                              'no_key')

        _test_exists_ok()
        _test_exists_exception()

    def test_optional(self):
        fake_args = {'k1': 'v1'}

        def _test_optional_exist():
            self.assertEqual('v1',
                             self.pluginlib_nova.optional(fake_args, 'k1'))

        def _test_optional_none():
            self.assertIsNone(self.pluginlib_nova.optional(fake_args,
                                                           'no_key'))

        _test_optional_exist()
        _test_optional_none()

    def test_get_domain_0(self):
        mock_get_this_host = self.mock_patch_object(
            self.session.xenapi.session,
            'get_this_host',
            return_val='fake_fost_ref')
        mock_get_vm_records = self.mock_patch_object(
            self.session.xenapi.VM,
            'get_all_records_where',
            return_val={"fake_vm_ref": "fake_value"})

        ret_value = self.pluginlib_nova._get_domain_0(self.session)

        self.assertTrue(mock_get_this_host.called)
        self.assertTrue(mock_get_vm_records.called)
        self.assertEqual('fake_vm_ref', ret_value)

    def test_with_vdi_in_dom0(self):
        mock_get_domain_0 = self.mock_patch_object(
            self.pluginlib_nova,
            '_get_domain_0',
            return_val='fake_dom0_ref')
        mock_vbd_create = self.mock_patch_object(
            self.session.xenapi.VBD,
            'create',
            return_val='fake_vbd_ref')
        mock_vbd_plug = self.mock_patch_object(
            self.session.xenapi.VBD,
            'plug')
        mock_vbd_get_device = self.mock_patch_object(
            self.session.xenapi.VBD,
            'get_device',
            return_val='fake_vbd_ref')
        mock_vbd_unplug_with_retry = self.mock_patch_object(
            self.pluginlib_nova,
            '_vbd_unplug_with_retry')
        mock_vbd_destroy = self.mock_patch_object(
            self.session.xenapi.VBD,
            'destroy')

        def handle_function(vbd):
            # the fake vbd handle function
            return vbd

        fake_vdi = 'fake_vdi'
        return_value = self.pluginlib_nova.with_vdi_in_dom0(
            self.session, fake_vdi, 'RO', handle_function)

        self.assertEqual('fake_vbd_ref', return_value)
        self.assertTrue(mock_get_domain_0.called)
        self.assertTrue(mock_vbd_create.called)
        self.assertTrue(mock_vbd_plug.called)
        self.assertTrue(mock_vbd_get_device.called)
        self.assertTrue(mock_vbd_unplug_with_retry.called)
        self.assertTrue(mock_vbd_destroy.called)

    def test_vbd_unplug_with_retry_success_at_first_time(self):
        def fake_vbd_unplug(*args, **kwargs):
            return

        self.session.xenapi.VBD.unplug.side_effect = fake_vbd_unplug

        self.pluginlib_nova._vbd_unplug_with_retry(self.session,
                                                   'fake_vbd_ref')
        self.assertEqual(1, self.session.xenapi.VBD.unplug.call_count)

    def test_vbd_unplug_with_retry_detached_already(self):
        def fake_vbd_unplug(*args, **kwargs):
            raise FakeUnplugException(['DEVICE_ALREADY_DETACHED'])

        self.session.xenapi.VBD.unplug.side_effect = fake_vbd_unplug
        self.pluginlib_nova.XenAPI.Failure = FakeUnplugException
        self.pluginlib_nova._vbd_unplug_with_retry(self.session,
                                                   'fake_vbd_ref')
        self.assertEqual(1, self.session.xenapi.VBD.unplug.call_count)

    def test_vbd_unplug_with_retry_seccuss_at_second_time(self):
        def fake_vbd_unplug(*args, **kwargs):
            if fake_vbd_unplug.called:
                return
            else:
                fake_vbd_unplug.called = True
                raise FakeUnplugException(['DEVICE_DETACH_REJECTED'])

        fake_vbd_unplug.called = False
        self.session.xenapi.VBD.unplug.side_effect = fake_vbd_unplug
        self.pluginlib_nova.XenAPI.Failure = FakeUnplugException
        self.pluginlib_nova._vbd_unplug_with_retry(self.session,
                                                   'fake_vbd_ref')
        self.assertEqual(2, self.session.xenapi.VBD.unplug.call_count)
