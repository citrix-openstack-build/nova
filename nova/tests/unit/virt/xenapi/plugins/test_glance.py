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

import mock

import sys

try:
    import httplib
    import urllib2
    from urllib2 import HTTPError
    from urllib2 import URLError
except ImportError:
    # make py3.x happy: it's needed for script parsing, although this test
    # is excluded from py3.x testing
    import http.client as httplib
    from urllib.error import HTTPError
    from urllib.error import URLError
    import urllib.request as urllib2

from nova.tests.unit.virt.xenapi.plugins import plugin_test


class GlanceTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(GlanceTestCase, self).setUp()
        # md5 is deprecated in py2.7 and forward;
        sys.modules['md5'] = mock.Mock()
        self.glance = self.load_plugin("glance")

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_and_verify_ok(self, mock_urlopen):
        mock_extract_tarball = self.mock_patch_object(
            self.glance.utils, 'extract_tarball')
        mock_info = mock.MagicMock()
        mock_info.getheader.return_value = 'expect_cksum'
        mock_urlopen.return_value.info.return_value = mock_info
        fake_request = urllib2.Request('http://fakeurl.com')
        self.glance.md5.new.return_value.hexdigest.return_value = \
            'expect_cksum'

        result = self.glance._download_tarball_and_verify(
            fake_request, 'fake_staging_path')

        self.assertTrue(mock_urlopen.called)
        self.assertTrue(mock_extract_tarball.called)
        self.assertTrue(result)

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_ok_verify_failed(self, mock_urlopen):
        mock_extract_tarball = self.mock_patch_object(
            self.glance.utils, 'extract_tarball')
        mock_info = mock.MagicMock()
        mock_info.getheader.return_value = 'expect_cksum'
        mock_urlopen.return_value.info.return_value = mock_info
        fake_request = urllib2.Request('http://fakeurl.com')
        self.glance.md5.new.return_value.hexdigest.return_value = \
            'unexpect_cksum'

        is_RetryableError_raised = False
        try:
            self.glance._download_tarball_and_verify(
                fake_request, 'fake_staging_path')
        except self.glance.RetryableError:
            is_RetryableError_raised = True

        self.assertTrue(mock_urlopen.called)
        self.assertTrue(mock_extract_tarball.called)
        self.assertTrue(is_RetryableError_raised)

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_failed_HTTPError(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            None, None, None, None, None)
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(
            self.glance.RetryableError,
            self.glance._download_tarball_and_verify,
            fake_request, 'fake_staging_path')

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_failed_URLError(self, mock_urlopen):
        mock_urlopen.side_effect = URLError(None)
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(
            self.glance.RetryableError,
            self.glance._download_tarball_and_verify,
            fake_request, 'fake_staging_path')

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_failed_HTTPException(self, mock_urlopen):
        mock_urlopen.side_effect = httplib.HTTPException()
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(
            self.glance.RetryableError,
            self.glance._download_tarball_and_verify,
            fake_request, 'fake_staging_path')

    @mock.patch.object(urllib2, 'Request')
    def test_download_tarball_by_url(self, mock_request):
        mock_download_tarball_and_verify = self.mock_patch_object(
            self.glance, '_download_tarball_and_verify')

        self.glance._download_tarball_by_url(
            'fake_sr_path', 'fake_staging_path', 'fake_image_id',
            'fake_glance_endpoint', 'fake_extra_headers')

        self.assertTrue(mock_request.called)
        self.assertTrue(mock_download_tarball_and_verify.called)

    @mock.patch.object(httplib, 'HTTPConnection')
    def test_upload_tarball_by_url_http(self, mock_HTTPConn):
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_response = mock.MagicMock()
        mock_response.status = httplib.OK
        mock_HTTPConn.return_value.getresponse.return_value = \
            mock_response

        fake_endpoint = 'http://fake_netloc/fake_path'

        self.glance._upload_tarball_by_url(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            extra_headers=mock.MagicMock(),
            properties=mock.MagicMock())

        self.assertTrue(mock_HTTPConn.called)
        self.assertTrue(mock_validate_image.called)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPConn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    @mock.patch.object(httplib, 'HTTPSConnection')
    def test_upload_tarball_by_url_https(self, mock_HTTPSConn):
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_response = mock.MagicMock()
        mock_response.status = httplib.OK
        mock_HTTPSConn.return_value.getresponse.return_value = \
            mock_response

        fake_endpoint = 'https://fake_netloc/fake_path'

        self.glance._upload_tarball_by_url(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            extra_headers=mock.MagicMock(),
            properties=mock.MagicMock())

        self.assertTrue(mock_HTTPSConn.called)
        self.assertTrue(mock_validate_image.called)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    @mock.patch.object(httplib, 'HTTPSConnection')
    def test_upload_tarball_by_url_https_failed_retry(self, mock_HTTPSConn):
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_response = mock.MagicMock()

        mock_response.status = httplib.REQUEST_TIMEOUT
        mock_HTTPSConn.return_value.getresponse.return_value = \
            mock_response
        fake_endpoint = 'https://fake_netloc/fake_path'

        self.glance._upload_tarball_by_url(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            extra_headers=mock.MagicMock(),
            properties=mock.MagicMock())

        self.assertTrue(mock_HTTPSConn.called)
        self.assertTrue(mock_validate_image.called)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
        self.assertTrue(mock_check_resp_status.called)

    def test_check_resp_status_and_retry(self):
        mock_resp_badrequest = mock.MagicMock()
        mock_resp_badrequest.status = httplib.BAD_REQUEST
        mock_resp_badgateway = mock.MagicMock()
        mock_resp_badgateway.status = httplib.BAD_GATEWAY

        self.assertRaises(
            self.glance.PluginError,
            self.glance.check_resp_status_and_retry,
            mock_resp_badrequest,
            'fake_image_id',
            'fake_url')

        self.assertRaises(
            self.glance.RetryableError,
            self.glance.check_resp_status_and_retry,
            mock_resp_badgateway,
            'fake_image_id',
            'fake_url')

    def test_validate_image_status_before_upload_ok(self):
        mock_conn = mock.MagicMock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_check_resp_status_and_retry = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_head_resp = mock.MagicMock()
        mock_head_resp.read.return_value = 'fakeData'
        mock_head_resp.status = httplib.OK

        mock_head_resp.getheader.return_value = 'queued'
        mock_conn.getresponse.return_value = mock_head_resp

        self.glance.validate_image_status_before_upload(
            mock_conn, fake_url, extra_headers=mock.MagicMock())

        self.assertTrue(mock_conn.getresponse.called)
        self.assertEqual(
            mock_conn.getresponse.return_value.read.call_count, 2)
        self.assertFalse(mock_check_resp_status_and_retry.called)

    def test_validate_image_status_before_upload_failed(self):
        mock_conn = mock.MagicMock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_head_resp = mock.MagicMock()
        mock_head_resp.read.return_value = 'fakeData'
        mock_head_resp.status = httplib.OK

        mock_head_resp.getheader.return_value = 'not-queued'
        mock_conn.getresponse.return_value = mock_head_resp

        self.assertRaises(self.glance.PluginError,
            self.glance.validate_image_status_before_upload,
            mock_conn, fake_url, extra_headers=mock.MagicMock())

    def test_download_vhd2(self):
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area')
        mock_download_tarball_by_url = self.mock_patch_object(
            self.glance, '_download_tarball_by_url')
        mock_import_vhds = self.mock_patch_object(
            self.glance.utils, 'import_vhds')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.download_vhd2(
            'fake_session', 'fake_image_id', 'fake_endpoint',
            'fake_uuid_stack', 'fake_sr_path', 'fake_extra_headers')

        self.assertTrue(mock_make_staging_area.called)
        self.assertTrue(mock_download_tarball_by_url.called)
        self.assertTrue(mock_import_vhds.called)
        self.assertTrue(mock_cleanup_staging_area.called)

    def test_download_vhd(self):
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area')
        mock_download_tarball = self.mock_patch_object(
            self.glance, '_download_tarball')
        mock_import_vhds = self.mock_patch_object(
            self.glance.utils, 'import_vhds')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.download_vhd(
            'fake_session', 'fake_image_id', 'fake_glance_host',
            'fake_glance_port', 'fake_glance_use_ssl',
            'fake_uuid_stack', 'fake_sr_path', 'fake_extra_headers')

        self.assertTrue(mock_make_staging_area.called)
        self.assertTrue(mock_download_tarball.called)
        self.assertTrue(mock_import_vhds.called)
        self.assertTrue(mock_cleanup_staging_area.called)

    def test_upload_vhd2(self):
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area')
        mock_prepare_staging_area = self.mock_patch_object(
            self.glance.utils, 'prepare_staging_area')
        mock_upload_tarball_by_url = self.mock_patch_object(
            self.glance, '_upload_tarball_by_url')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.upload_vhd2(
            'fake_session', 'fake_vid_uuids', 'fake_image_id',
            'fake_endpoint', 'fake_sr_path',
            'fake_extra_headers', 'fake_properties')

        self.assertTrue(mock_make_staging_area.called)
        self.assertTrue(mock_prepare_staging_area.called)
        self.assertTrue(mock_upload_tarball_by_url.called)
        self.assertTrue(mock_cleanup_staging_area.called)

    def test_upload_vhd(self):
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area')
        mock_prepare_staging_area = self.mock_patch_object(
            self.glance.utils, 'prepare_staging_area')
        mock_upload_tarball = self.mock_patch_object(
            self.glance, '_upload_tarball')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.upload_vhd(
            'fake_session', 'fake_vid_uuids', 'fake_image_id',
            'fake_glance_host', 'fake_glance_port',
            'fake_glance_use_ssl', 'fake_sr_path',
            'fake_extra_headers', 'fake_properties')

        self.assertTrue(mock_make_staging_area.called)
        self.assertTrue(mock_prepare_staging_area.called)
        self.assertTrue(mock_upload_tarball.called)
        self.assertTrue(mock_cleanup_staging_area.called)
