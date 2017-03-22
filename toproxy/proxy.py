#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8


import os
import re
import argparse
import logging
from urlparse import urlparse

import tornado.httpserver
import tornado.ioloop
import tornado.iostream
import tornado.web
import tornado.httpclient


logger = logging.getLogger()


class ProxyHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET', 'POST']

    @tornado.web.asynchronous
    def get(self):
        logger.debug('Handle %s request to %s', self.request.method, self.request.uri)

        def handle_response(response):
            if (response.error and not
                    isinstance(response.error, tornado.httpclient.HTTPError)):
                self.set_status(500)
                self.write('Internal server error:\n' + str(response.error))
            else:
                self.set_status(response.code)
                for header in ('Date', 'Cache-Control', 'Server', 'Content-Type', 'Location'):
                    v = response.headers.get(header)
                    if v:
                        self.set_header(header, v)
                v = response.headers.get_list('Set-Cookie')
                if v:
                    for i in v:
                        self.add_header('Set-Cookie', i)
                if response.body:
                    self.write(response.body)
            self.finish()

        if base_auth_user:
            auth_header = self.request.headers.get('Authorization', '')
            if not base_auth_valid(auth_header):
                self.set_status(403)
                self.write('Auth Faild')
                self.finish()
                return

        user_agent = self.request.headers.get('User-Agent', '')
        if shield_attack(user_agent):
            self.set_status(500)
            self.write('nima')
            self.finish()
            return

        client_ip = self.request.remote_ip
        if not match_white_iplist(client_ip):
            logger.debug('deny %s', client_ip)
            self.set_status(403)
            self.write('')
            self.finish()
            return
        body = self.request.body
        if not body:
            body = None
        try:
            fetch_request(
                self.request.uri, handle_response,
                method=self.request.method, body=body,
                headers=self.request.headers, follow_redirects=False,
                allow_nonstandard_methods=True)
        except tornado.httpclient.HTTPError as e:
            if hasattr(e, 'response') and e.response:
                handle_response(e.response)
            else:
                self.set_status(500)
                self.write('Internal server error:\n' + str(e))
                self.finish()

    @tornado.web.asynchronous
    def post(self):
        return self.get()


def get_proxy(url):
    url_parsed = urlparse(url, scheme='http')
    proxy_key = '%s_proxy' % url_parsed.scheme
    return os.environ.get(proxy_key)


def base_auth_valid(auth_header):
    # Basic Zm9vOmJhcg==
    auth_mode, auth_base64 = auth_header.split(' ', 1)
    assert auth_mode == 'Basic'
    # 'Zm9vOmJhcg==' == base64("foo:bar")
    auth_username, auth_password = auth_base64.decode('base64').split(':', 1)
    if auth_username == base_auth_user and auth_password == base_auth_passwd:
        return True
    else:
        return False


def parse_proxy(proxy):
    proxy_parsed = urlparse(proxy, scheme='http')
    return proxy_parsed.hostname, proxy_parsed.port


def match_white_iplist(clientip):
    if clientip in white_iplist:
        return True
    if not white_iplist:
        return True
    return False


def shield_attack(header):
    if re.search(header, 'ApacheBench'):
        return True
    return False


def fetch_request(url, callback, **kwargs):
    logger.debug('Forward request via upstream proxy')
    tornado.httpclient.AsyncHTTPClient.configure(
        'tornado.curl_httpclient.CurlAsyncHTTPClient')

    if proxy_host is not None:
        kwargs['proxy_host'] = proxy_host
        kwargs['proxy_port'] = proxy_port

    req = tornado.httpclient.HTTPRequest(url, **kwargs)
    client = tornado.httpclient.AsyncHTTPClient()
    client.fetch(req, callback, follow_redirects=True, max_redirects=3)


def run_proxy(port, start_ioloop=True):
    app = tornado.web.Application([
        (r'.*', ProxyHandler),
    ])

    app.listen(port)
    ioloop = tornado.ioloop.IOLoop.instance()

    if start_ioloop:
        ioloop.start()


if __name__ == '__main__':
    white_iplist = []
    proxy_host = None
    proxy_port = None

    parser = argparse.ArgumentParser(description='''python -m toproxy/proxy  -p 8888 -w 127.0.0.1,8.8.8.8 -u xiaorui:fengyun''')

    parser.add_argument('-p', '--port', help='tonado proxy listen port', action='store', default=8888)
    parser.add_argument('-w', '--white', help='white ip list ---> 127.0.0.1,215.8.1.3', action='store', default=[])
    parser.add_argument('-u', '--user', help='Base Auth , xiaoming:123123', action='store', default=None)
    parser.add_argument('-H', '--proxy_host', help='Proxy host', action='store', default=None)
    parser.add_argument('-P', '--proxy_port', help='Proxy port', action='store', default=0)
    args = parser.parse_args()

    if not args.port:
        parser.print_help()

    port = int(args.port)
    white_iplist = args.white
    proxy_host = args.proxy_host
    proxy_port = int(args.proxy_port)

    if args.user:
        base_auth_user, base_auth_passwd = args.user.split(':')
    else:
        base_auth_user, base_auth_passwd = None, None

    print ("Starting HTTP proxy on port %d" % port)
    run_proxy(port)
