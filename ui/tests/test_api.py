import json

import httplib
from mock import patch, Mock
from unittest2 import TestCase

from .responses import response, make_identity, FakeResponse
from .utils import ResourceTestCase



class CachedHttpTest(TestCase):
    def make_request(self, **kwargs):
        from tcmui.core.api import CachedHttp

        res = Mock()
        res.status = kwargs.pop("response_status", httplib.OK)
        content = kwargs.pop("response_content", "content")
        with patch(
            "tcmui.core.api.httplib2.Http.request",
            Mock(return_value=(res, content))):
            return CachedHttp().request(**kwargs)


    def test_caches_get(self):
        with patch("tcmui.core.api.cache") as cache:
            cache.get = Mock(return_value=None)

            ret = self.make_request(method="GET", uri="/uri/")

            cache.set.assert_called_with("/uri/", ret, 600)


    def _test_doesnt_cache(self, method):
        with patch("tcmui.core.api.cache") as cache:
            self.make_request(method=method, uri="/uri/")

            self.assertFalse(cache.get.called)
            self.assertFalse(cache.set.called)


    def test_put_doesnt_cache(self):
        self._test_doesnt_cache("PUT")


    def test_post_doesnt_cache(self):
        self._test_doesnt_cache("POST")


    def test_delete_doesnt_cache(self):
        self._test_doesnt_cache("DELETE")


    def test_doesnt_cache_non_OK(self):
        with patch("tcmui.core.api.cache") as cache:
            cache.get = Mock(return_value=None)

            self.make_request(method="GET", uri="/uri/", response_status=401)

            self.assertTrue(cache.get.called)
            self.assertFalse(cache.set.called)


    def test_returns_cached_for_get(self):
        with patch("tcmui.core.api.cache") as cache:
            cache.get = Mock(return_value="cached")

            ret = self.make_request(method="GET", uri="/uri/")

            cache.get.assert_called_with("/uri/")
            self.assertEqual(ret, "cached")



class CredentialsTest(TestCase):
    def get_creds(self, *args, **kwargs):
        from tcmui.core.auth import Credentials
        return Credentials(*args, **kwargs)


    def test_with_password(self):
        c = self.get_creds("user@example.com", password="blah")

        self.assertEqual(
            c.headers(),
            {
                "authorization": "Basic dXNlckBleGFtcGxlLmNvbTpibGFo"
                }
            )


    def test_with_cookie(self):
        c = self.get_creds("user@example.com", cookie="USERTOKEN: value")

        self.assertEqual(
            c.headers(),
            {
                "cookie": "USERTOKEN: value"
                }
            )


    def test_with_both(self):
        c = self.get_creds(
            "user@example.com", password="blah", cookie="USERTOKEN: value")

        self.assertEqual(
            c.headers(),
            {
                "authorization": "Basic dXNlckBleGFtcGxlLmNvbTpibGFo"
                }
            )


    def test_with_neither(self):
        c = self.get_creds("user@example.com")

        self.assertEqual(c.headers(), {})


    def test_repr(self):
        c = self.get_creds("user@example.com")

        self.assertEqual(repr(c), "<Credentials: user@example.com>")



class TestResourceTestCase(ResourceTestCase):
    RESOURCE_DEFAULTS = {
        "name": "Default name",
        }

    RESOURCE_TYPE = "testresource"

    RESOURCE_TYPE_PLURAL = "testresources"


    def get_resource_class(self):
        from tcmui.core.api import RemoteObject, fields

        class TestResource(RemoteObject):
            name = fields.Field()

        return TestResource


    def get_resource_list_class(self):
        from tcmui.core.api import ListObject, fields

        class TestResourceList(ListObject):
            entryclass = self.resource_class
            api_name = self.RESOURCE_TYPE_PLURAL
            default_url = self.RESOURCE_TYPE_PLURAL

            entries = fields.List(fields.Object(self.resource_class))

        return TestResourceList



@patch("remoteobjects.http.userAgent")
class ResourceObjectTest(TestResourceTestCase):
    def test_get_data(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/3")

        self.assertEqual(c.name, "Test TestResource")


    def test_unicode_conversion(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/3")

        self.assertEqual(type(c.name), unicode)


    def test_no_id(self, http):
        c = self.resource_class(name="No id yet")
        self.assertEqual(c.id, None)

    def test_get_url(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/3")
        c.deliver()

        self.assertEqual(
            http.request.call_args[1]["uri"],
            "http://fake.base/rest/testresources/3?_type=json")


    def test_get_id(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(
                name="Test TestResource",
                resourceIdentity=make_identity(id="3")))

        c = self.resource_class.get("testresources/3")

        self.assertEqual(c.id, "3")


    def test_get_location(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(
                name="Test TestResource",
                resourceIdentity=make_identity(url="testresources/3/")))

        c = self.resource_class.get("testresources/3")
        c.deliver()

        self.assertEqual(c._location, "http://fake.base/rest/testresources/3/")


    def test_create(self, http):
        c = self.resource_class(name="Some TestResource")

        self.assertEqual(c.name, "Some TestResource")


    def test_no_auth_no_auth_headers(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/3")
        c.deliver()

        headers = http.request.call_args[1]["headers"]
        self.assertFalse("cookie" in headers)
        self.assertFalse("authorization" in headers)


    def test_auth_headers_password(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        c = self.resource_class.get(
            "testresources/3",
            auth=self.creds("user@example.com", password="blah"))
        c.deliver()

        headers = http.request.call_args[1]["headers"]
        self.assertTrue("authorization" in headers)
        self.assertFalse("cookie" in headers)


    def test_auth_headers_cookie(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        c = self.resource_class.get(
            "testresources/3",
            auth=self.creds("user@example.com", cookie="USERTOKEN: blah"))
        c.deliver()

        headers = http.request.call_args[1]["headers"]
        self.assertFalse("authorization" in headers)
        self.assertTrue("cookie" in headers)


    def test_get_persists_auth(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        creds = self.creds("user@example.com", cookie="USERTOKEN: blah")

        c = self.resource_class.get("testresources/3", auth=creds)
        c.deliver()

        self.assertEqual(c.auth, creds)


    def test_get_full_url(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_one(name="Test TestResource"))

        c = self.resource_class.get("http://some.other.url/testresources/3")
        c.deliver()

        self.assertEqual(
            http.request.call_args[1]["uri"],
            "http://some.other.url/testresources/3?_type=json")


    def test_unauthorized(self, http):
        http.request.return_value = response(
            httplib.UNAUTHORIZED, "some error", {"content-type": "text/plain"})

        c = self.resource_class.get("testresources/3")
        with self.assertRaises(self.resource_class.Unauthorized) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "401  requesting TestResource "
            'http://fake.base/rest/testresources/3?_type=json: some error')


    def test_no_content(self, http):
        http.request.return_value = response(
            httplib.NO_CONTENT, "")

        c = self.resource_class.get("testresources/3")
        c.delete()

        self.assertEqual(c.name, None)


    def test_json_error(self, http):
        http.request.return_value = response(
            httplib.CONFLICT, {"errors":[{"error":"email.in.use"}]})

        c = self.resource_class.get("testresources/3")
        with self.assertRaises(self.resource_class.Conflict) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "409  requesting TestResource "
            "http://fake.base/rest/testresources/3?_type=json: email.in.use")


    def test_bad_response(self, http):
        http.request.return_value = response(
            777, "Something is very wrong.")

        c = self.resource_class.get("testresources/3")
        with self.assertRaises(self.resource_class.BadResponse) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "Unexpected response requesting TestResource "
            "http://fake.base/rest/testresources/3?_type=json: 777 ")


    def test_missing_location_header(self, http):
        http.request.return_value = response(
            302, "")

        c = self.resource_class.get("testresources/3")
        with self.assertRaises(self.resource_class.BadResponse) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "'Location' header missing from 302  response requesting TestResource "
            "http://fake.base/rest/testresources/3?_type=json")


    def test_bad_content_type(self, http):
        http.request.return_value = response(
            httplib.OK, "blah", {"content-type": "text/plain"})

        c = self.resource_class.get("testresources/3")
        with self.assertRaises(self.resource_class.BadResponse) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "Bad response fetching TestResource "
            "http://fake.base/rest/testresources/3?_type=json: "
            "content-type text/plain is not an expected type")


    def test_unicode_response(self, http):
        http.request.return_value = (
            FakeResponse(
                httplib.OK,
                headers={"content-type": "application/json"}),
            unicode(json.dumps(self.make_one(name="Test TestResource")))
            )

        c = self.resource_class.get("testresources/3")

        self.assertEqual(type(c.name), unicode)


    def test_cache_attribute(self, http):
        with patch.object(self.resource_class, "cache", True):
            with patch("remoteobjects.RemoteObject.get") as mock:
                self.resource_class.get("testresources/3")

        from tcmui.core.api import cachedUserAgent

        mock.assert_called_with('testresources/3', http=cachedUserAgent)



@patch("remoteobjects.http.userAgent")
class ListObjectTest(TestResourceTestCase):
    def test_get_data_one(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get()

        self.assertEqual(c[0].name, "Test TestResource")


    def test_get_data_multiple(self, http):
        http.request.return_value = response(
            httplib.OK, self.make_searchresult(
                {"name": "Test TestResource"},
                {"name": "Second Test"}))

        c = self.resource_list_class.get()

        self.assertEqual(c[1].name, "Second Test")
