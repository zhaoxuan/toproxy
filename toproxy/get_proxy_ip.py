#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2016 JohnZ.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""

"""

import sys
import logging

import redis
import tornado.ioloop
import tornado.web


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(filename)s [line:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout)

LOGGER = logging.getLogger()

REDIS_CLIENT = redis.StrictRedis(
    host='127.0.0.1',
    port=6379, db=8,
    password='b5bc60642acc4764be9936b10497b8c1'
)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        num = int(self.get_argument('num', 0, True))

        ip_list = []
        if num > 100 or num <= 0:
            num = 100

        start = 0
        cursor = 0

        while len(ip_list) < num:
            cursor, tmp_list = REDIS_CLIENT.scan(cursor)

            if cursor == 0:
                ip_list += tmp_list
                break
            else:
                ip_list += tmp_list
                continue

        self.write('\n'.join(ip_list))


def make_app():
    return tornado.web.Application([
        (r"/fetch", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(5555)
    tornado.ioloop.IOLoop.current().start()
