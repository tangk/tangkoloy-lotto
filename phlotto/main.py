#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# The webapp2 framework
import logging
from google.appengine.api import memcache
import webapp2
import simplejson as json
from models import LottoResults, DrawDate, DigitsResults_high, DigitsResults_low
from tasks.daily import CurrentDate, cronJob

class MainPage(webapp2.RequestHandler):
    # Respond to a HTTP GET request
    def get(self):
        date=CurrentDate().getnow()
        self.response.out.write('<html><body>')
        self.response.out.write(date)
        self.response.out.write('</body></html>')
    def post(self):
        UPDATE_RQST = 1
        RETRIEVE_FROM_DATE = 2
        RETRIEVE_FROM_DATES = 3
        draw_types_lotto = {'55':0, '49':0, '45':0, '42':0}
        draw_types_digits = {'6d':0, '4d':0}
        draw_types_daily_3d = {'11am':0, '4pm':0, '9pm':0}
        draw_types_daily_2d = {'11am':0, '4pm':0, '9pm':0}
        date=CurrentDate()
        inp = self.request.body
        try:
            d=json.loads(inp)
            logging.debug(d)
            if not d: return
        except ValueError:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.set_status( 500,"Internal server error")
            self.response.write(' Invalid JSON object in request: '+inp)
            logging.error( 'Invalid JSON object: '+inp)
            return
        responseList=[]
        self.request_id = d['rid']
        self.request_data = d['rdata']
        self.request_extra = d['extra']
        #self.month = e['v1']
        #self.year = e['v3']
        res = {}
        if self.request_id == UPDATE_RQST:
            for draw in draw_types_lotto:
                found = memcache.get(draw)
                if found:
                    logging.debug(found)
                    res[draw] = found

            for draw in draw_types_digits:
                found = memcache.get(draw)
                if found:
                    res[draw] = found

            for time in draw_types_daily_2d:
                found = memcache.get('2d_'+time)
                if found:
                    res['2d_'+time] = found

            for time in draw_types_daily_3d:
                found = memcache.get('3d_'+time)
                if found:
                    res['3d_'+time] = found
            logging.debug(res)
        elif self.request_id == RETRIEVE_FROM_DATE:
            draw_date = DrawDate.get_by_key_name(self.request_data)
            if draw_date is None:
                cronJob().get()
                draw_date = DrawDate.get_by_key_name(self.request_data)
        self.response.set_status(200,"OK")
        resultElement={'id':1, 'rid':self.request_id, 'result':res}
        logging.debug(resultElement)
        responseList.append(resultElement)
        self.response.out.write(json.dumps(responseList))

# Create our application instance that maps the root to our
# MainPage handler
app = webapp2.WSGIApplication([('/', MainPage)], debug=True)


#def main():
#    # Set the logging level in the main function
#    # See the section on Requests and App Caching for information on how
#    # App Engine reuses your request handlers when you specify a main function
#    logging.getLogger().setLevel(logging.DEBUG)
#    webapp.util.run_wsgi_app(app)
#
#if __name__ == '__main__':
#    main()