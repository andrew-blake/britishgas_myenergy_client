from __future__ import print_function
import requests
import calendar
from datetime import datetime
import re

import json
import codecs
import logging

logging.basicConfig()
requests_log = logging.getLogger("requests.packages.urllib3")

try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client

# for debugging
from pprint import pprint
from ipdb import set_trace


class MyEnergyClientInvalidPostData(Exception):
    pass


class MyEnergyBase(object):
    def __init__(self, debug=False):
        self.reader = codecs.getdecoder("utf-8")

        if debug:
            http_client.HTTPConnection.debuglevel = 1
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        else:
            http_client.HTTPConnection.debuglevel = 0
            logging.getLogger().setLevel(logging.INFO)
            requests_log.setLevel(logging.INFO)
            requests_log.propagate = False

    def _convert(self, object):
        return json.loads(object)


class MyEnergyClient(MyEnergyBase):
    def __init__(self, username, password, proxies=None, debug=False, ssl_verify=True):
        super(MyEnergyClient, self).__init__(debug)

        self.username = username
        self.password = password
        self.proxies = proxies
        self.ssl_verify = ssl_verify

        self.cookies = None
        self.bg_cookie_id = None
        self.jsessionid = None
        self.token = None
        self.account_number = None
        self.ucrn = None
        self.is_initialised = False

        self._login()

    def _unixtime_in_ms(self):
        d = datetime.utcnow()
        return calendar.timegm(d.timetuple()) * 1000

    def _get_cookies(self):

        cookies = {
            'ecos.dt': '%s' % self._unixtime_in_ms(),
            'homepage_beta': 'false',
            'SessionPersistence': 'CLICKSTREAMCLOUD:=visitorId=anonymous|PROFILEDATA:=avatar=/etc/designs/default/images/collab/avatar.png,isLoggedIn=true,isLoggedIn_xss=true,authorizableId=anonymous,authorizableId_xss=anonymous,formattedName=,formattedName_xss=|TAGCLOUD:=|SURFERINFO:=IP=127.0.0.1,keywords=,browser=WebKit,OS=Mac OS X,resolution=320x568|',
        }

        if self.bg_cookie_id is not None:
            cookies['BG_COOKIE_ID'] = self.bg_cookie_id

        if self.jsessionid is not None:
            cookies['JSESSIONID'] = self.jsessionid

        return cookies

    def _get_headers(self, is_post):

        headers = {
            'Host': 'www.britishgas.co.uk',
            'Proxy-Connection': 'keep-alive',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-GB;q=1, en;q=0.9, ja;q=0.8, el;q=0.7',
            'Connection': 'keep-alive',
            'User-Agent': 'British Gas/2.1.70 (iPod touch; iOS 8.1.2; Scale/2.00)',
        }

        if is_post:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if self.token is not None:
            headers['X-CSRF-Token'] = self.token

        return headers

    def _login(self):

        #
        # get the cookies
        #
        url = 'https://www.britishgas.co.uk/mobile/iphone/OAMAuthenticate'

        data = {
            'channel': 'itouch',
            'clientVersion': '6.1.7',
            'deviceName': 'iPod Touch',
            'deviceVersion': 'iPod5.1',
            'iOSVersion': '8.1.2',
            'password': self.password,
            'responseType': 'JSON',
            'username': self.username,
        }
        req1 = requests.post(url, data=data, headers=self._get_headers(is_post=True), cookies=self._get_cookies(),
                             proxies=self.proxies, verify=self.ssl_verify)

        self.response = json.loads(req1.content)
        self.is_authenticated = self.response['OAMAuthenticate']['isAuthenticated'] == u'TRUE'
        self.account_number = self.response['OAMAuthenticate']['Accounts'][0]['AccountNumber']
        self.ucrn = self.response['OAMAuthenticate']['Accounts'][0]['CustomerDetails']['Ucrn']

        self.cookies = req1.cookies
        self.bg_cookie_id = self.cookies['BG_COOKIE_ID']
        self.jsessionid = self.cookies['JSESSIONID']

        # print("BG_COOKIE_ID=%s; JSESSIONID=%s" % (self.bg_cookie_id, self.jsessionid))

        print("Account: %s" % self.account_number)
        print("Ucrn:    %s" % self.ucrn)

        self._save_response(req1, url)

        #
        # get the CSRF token
        #
        url = 'https://www.britishgas.co.uk/mobile/iphone/ser?'
        data = {
            'clientVersion': '6.1.7',
            'channel': 'itouch',
            'deviceVersion': 'iPod5,1',
            'accountNumber': '%s' % self.account_number,
            'accountType': 'Combined'
        }

        req2 = requests.post(url, data=data, cookies=self._get_cookies(), headers=self._get_headers(is_post=True),
                             proxies=self.proxies, verify=self.ssl_verify)
        html = req2.content
        token = None

        for line in html.split('\r\n'):
            m = re.match('.*id="uniqueId" value="(?P<token>.*)".*', line)
            if m is not None:
                token = m.groupdict()['token']
                break

        self.token = token

        # print("X-CSRF-Token: %s" % self.token)

        self.is_initialised = True and self.token

    def _save_url(self, url):
        # print("Processing: %s" % url)
        req = requests.get(url, cookies=self._get_cookies(), headers=self._get_headers(is_post=False),
                           proxies=self.proxies, verify=self.ssl_verify)
        self._save_response(req, url)

    def _save_response(self, req, url):
        filename = 'api-response-%s.json' % url
        filename = filename.replace('https://www.britishgas.co.uk/myenergy_prod/', '')
        filename = filename.replace('https://www.britishgas.co.uk/', '')
        filename = filename.replace('/', '-')

        content_dict = json.loads(req.content)
        content = json.dumps(content_dict, indent=4)
        fp = open(filename, 'w')
        fp.write(content)
        fp.close()
        print("Wrote: %s" % filename)

    def get_usage_by_month_daily(self):

        urls = [
            # 'https://www.britishgas.co.uk/myenergy_prod/api/usage/year/2015-01-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-12-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-11-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-10-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-09-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-08-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-07-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-06-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-05-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-04-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-03-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-02-01',
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/month/2015-01-01',
            # 'https://www.britishgas.co.uk/myenergy_prod/api/usage/day/2015-12-30',
            # 'https://www.britishgas.co.uk/myenergy_prod/api/usage/week/2015-12-20',
            # 'https://www.britishgas.co.uk/myenergy_prod/api/usage/week/2015-12-27',
        ]

        for url in urls:
            self._save_url(url)

    def get_usage_by_year_monthly(self):

        urls = [
            'https://www.britishgas.co.uk/myenergy_prod/api/usage/year/2015-01-01',
        ]

        for url in urls:
            self._save_url(url)

    def get_nectar_details(self):
        url = 'https://www.britishgas.co.uk/mobile/Nectar/Summary'
        data = {
            'channel': 'itouch',
            'clientVersion': '6.1.7',
            'deviceVersion': 'iPod5.1',
            'iOSVersion': '8.1.2',
            'responseType': 'JSON',
            'step': '1',
            'ucrn': self.ucrn,
        }
        req = requests.post(url, data=data, cookies=self._get_cookies(), headers=self._get_headers(is_post=True),
                            proxies=self.proxies, verify=self.ssl_verify)
        self._save_response(req, url)
