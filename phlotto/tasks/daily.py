from datetime import tzinfo, timedelta, datetime
from models import LottoResults, DrawDate, DigitsResults_high, DigitsResults_low
from lxml import html
from google.appengine.api import urlfetch
from lxml.html.clean import Cleaner
from google.appengine.api import memcache

import logging
import webapp2


class GMT8(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=8) + self.dst(dt)
    def dst(self, dt):
        d = datetime(dt.year, 4, 1)
        self.dston = d - timedelta(days=d.weekday() + 1)
        d = datetime(dt.year, 11, 1)
        self.dstoff = d - timedelta(days=d.weekday() + 1)
        if self.dston <= dt.replace(tzinfo=None) < self.dstoff:
            #return timedelta(hours=1)
            return timedelta(0)
        else:
            return timedelta(0)
    def tzname(self):
        return "GMT +8"

class CurrentDate():
    gmt8 = GMT8()
    datenow = datetime.now(gmt8)
    if datenow.hour < 8:
        datenow = datenow - timedelta(days=1)
    def getnow(self):
        return self.datenow
    def gethour(self):
        return self.datenow.hour
    def getday(self):
        return str(self.datenow.day)
    def getmonth(self):
        return str(self.datenow.month)
    def getyear(self):
        return str(self.datenow.year)
    def getwkday(self):
        return self.datenow.weekday()

class cronJob(webapp2.RequestHandler):
    def get(self):
        logging.debug('starting job..')
        draw_types_lotto = {'55':0, '49':0, '45':0, '42':0}
        draw_types_digits = {'6d':0, '4d':0}
        draw_types_daily_3d = {'11am':0, '4pm':0, '9pm':0}
        draw_types_daily_2d = {'11am':0, '4pm':0, '9pm':0}
        date_obj = CurrentDate()
        if date_obj.getwkday() == 0: #monday
            del draw_types_lotto['49']
            del draw_types_lotto['42']
            del draw_types_digits['6d']
        elif date_obj.getwkday() == 1: #tuesday
            del draw_types_lotto['55']
            del draw_types_lotto['45']
            del draw_types_digits['4d']
        elif date_obj.getwkday() == 2:
            del draw_types_lotto['49']
            del draw_types_lotto['42']
            del draw_types_digits['6d']
        elif date_obj.getwkday() == 3:
            del draw_types_lotto['55']
            del draw_types_lotto['45']
            del draw_types_digits['4d']
        elif date_obj.getwkday() == 4: #friday
            del draw_types_lotto['55']
            del draw_types_lotto['49']
            del draw_types_lotto['42']
            del draw_types_digits['6d']
        elif date_obj.getwkday() == 5: #saturday
            del draw_types_lotto['49']
            del draw_types_lotto['45']
            del draw_types_digits['4d']
        elif date_obj.getwkday() == 6: #sunday
            del draw_types_lotto['55']
            del draw_types_lotto['45']
            del draw_types_lotto['42']
            del draw_types_digits['6d']
            del draw_types_digits['4d']

        for draw in draw_types_lotto:
            found = memcache.get(draw)
            if found:
                draw_types_lotto[draw] = found

        for draw in draw_types_digits:
            found = memcache.get(draw)
            if found:
                draw_types_digits[draw] = found

        for time in draw_types_daily_2d:
            found = memcache.get('2d_'+time)
            if found:
                draw_types_daily_2d[time] = found

        for time in draw_types_daily_3d:
            found = memcache.get('3d_'+time)
            if found:
                draw_types_daily_3d[time] = found


        #keys_lotto = memcache.get('keys_lotto')
        #keys_digit = memcache.get('keys_digit')
        #keys_daily_2d = memcache.get('keys_daily_2d')
        #keys_daily_3d = memcache.get('keys_daily_3d')
        #draw_types_lotto_tmp = None
        #draw_types_digits_tmp = None
        #draw_types_daily_2d_tmp = None
        #draw_types_daily_3d_tmp = None
        #if keys_lotto is not None:
        #    draw_types_lotto_tmp = memcache.get_multi(keys_lotto, key_prefix='lotto_draws')
        #if draw_types_lotto_tmp is not None:
        #    draw_types_lotto.update(draw_types_lotto_tmp)
#
#        if keys_digit is not None:
#            draw_types_digits_tmp = memcache.get_multi(keys_digit, key_prefix='digit_draws')
#        if draw_types_digits_tmp is not None:
#            draw_types_digits.update(draw_types_digits_tmp)
#
#        if keys_daily_2d is not None:
#            draw_types_daily_2d_tmp = memcache.get_multi(keys_daily_2d, key_prefix='daily_2d')
#        if draw_types_daily_2d_tmp is not None:
#            draw_types_daily_2d.update(draw_types_daily_2d_tmp)
#
#        if keys_daily_3d is not None:
#            draw_types_daily_3d_tmp = memcache.get_multi(keys_daily_3d, key_prefix='daily_3d')
#        if draw_types_daily_3d_tmp is not None:
#            draw_types_daily_3d.update(draw_types_daily_3d_tmp)

        draw_date = DrawDate.get_or_insert(date_obj.getyear()+ date_obj.getmonth()+ date_obj.getday(),
            day=date_obj.getday(),
            month=date_obj.getmonth(),
            year=date_obj.getyear())

        for draw,done in draw_types_lotto.iteritems():
            if not done:
                new = Scraper(date_obj.getyear(), date_obj.getmonth(), date_obj.getday(), draw).scrape()
                if new:
                    lotto_results = LottoResults.get_or_insert(new[0], parent=draw_date, result=new[1], jackpot=new[2])
                    if len(new) == 4:
                        lotto_results.winners = new[3]
                        lotto_results.put()
                    draw_types_lotto[draw] = new[1]
                    memcache.add(key=draw, value=new[1], time=43200) #12hrs expire

        #memcache.add(key='keys_lotto', value=draw_types_lotto.keys(), time=86400)
        #memcache.add_multi(draw_types_lotto, key_prefix='lotto_draws', time=86400)

        for draw,done in draw_types_digits.iteritems():
            if not done:
                new = Scraper(date_obj.getyear(), date_obj.getmonth(), date_obj.getday(), draw).scrape()
                if new:
                    digits_results = DigitsResults_high.get_or_insert(new[0], parent=draw_date, result=new[1])
                    draw_types_digits[draw] = new[1]
                    memcache.add(key=draw, value=new[1], time=43200) #12hrs expire

        #memcache.add(key='keys_digit', value=draw_types_digits.keys(), time=86400)
        #memcache.add_multi(draw_types_digits, key_prefix='digit_draws', time=86400)

        for time,done in draw_types_daily_2d.iteritems():
            if not done:
                new = Scraper(date_obj.getyear(), date_obj.getmonth(), date_obj.getday(), '2d').scrape()
                if new:
                    daily_results = DigitsResults_low.get_or_insert(new[0], parent=draw_date)
                    if 'n.a' not in new[1]:
                        if draw_types_daily_2d['11am'] != new[1]:
                            daily_results.eleven_am_result = new[1]
                            draw_types_daily_2d['11am'] = new[1]
                            memcache.add(key='2d_11am', value=new[1])

                    if 'n.a' not in new[2]:
                        if draw_types_daily_2d['4pm'] != new[2]:
                            daily_results.four_pm_result = new[2]
                            draw_types_daily_2d['4pm'] = new[2]
                            memcache.add(key='2d_4pm', value=new[2])

                    if 'n.a' not in new[3]:
                        if draw_types_daily_2d['9pm'] != new[3]:
                            daily_results.nine_pm_result = new[3]
                            draw_types_daily_2d['9pm'] = new[3]
                            memcache.add(key='2d_9pm', value=new[3])

                    daily_results.put()

        #memcache.add(key='keys_daily_2d', value=draw_types_daily_2d.keys(), time=14400)
        #memcache.add_multi(draw_types_daily_2d, key_prefix='daily_2d', time=14400)

        for time,done in draw_types_daily_3d.iteritems():
            if not done:
                new = Scraper(date_obj.getyear(), date_obj.getmonth(), date_obj.getday(), '3d').scrape()
                if new:
                    daily_results = DigitsResults_low.get_or_insert(new[0], parent=draw_date)
                    if 'n.a' not in new[1]:
                        if draw_types_daily_3d['11am'] != new[1]:
                            daily_results.eleven_am_result = new[1]
                            draw_types_daily_3d['11am'] = new[1]
                            memcache.add(key='3d_11am', value=new[1])

                    if 'n.a' not in new[2]:
                        if draw_types_daily_3d['4pm'] != new[2]:
                            daily_results.four_pm_result = new[2]
                            draw_types_daily_3d['4pm'] = new[2]
                            memcache.add(key='3d_4pm', value=new[2])

                    if 'n.a' not in new[3]:
                        if draw_types_daily_3d['9pm'] != new[3]:
                            daily_results.nine_pm_result = new[3]
                            draw_types_daily_3d['9pm'] = new[3]
                            memcache.add(key='3d_9pm', value=new[3])

                    daily_results.put()


        #memcache.add(key='keys_daily_3d', value=draw_types_daily_3d.keys(), time=14400)
        #memcache.add_multi(draw_types_daily_3d, key_prefix='daily_3d', time=14400)

class Scraper:
    def __init__(self, year, month, day, draw):
        self.year = year
        self.month = month
        self.day = day
        self.draw = draw
        self.parse_done = False
    def parse_links(self):
        if not self.parse_done:
            url = "http://lynxjuan.com/"+str(self.year)+"/"+str(self.month)+"/"+str(self.day)
            website = urlfetch.fetch(url)
            page = str(website.content)
            tree = html.fromstring(page)
            links = tree.findall(".//a[@rel='bookmark']")
            link_dict = {}
            for link in links:
                draw_url = link.get('href')
                if '55' in draw_url:
                    link_dict['55'] = draw_url
                elif '49' in draw_url:
                    link_dict['49'] = draw_url
                elif '45' in draw_url:
                    link_dict['45'] = draw_url
                elif '42' in draw_url:
                    link_dict['42'] = draw_url
                elif ('6d' in draw_url) or ('six' in draw_url):
                    link_dict['6d'] = draw_url
                elif '4d' in draw_url:
                    link_dict['4d'] = draw_url
                elif ('swertres' in draw_url) or ('3d' in draw_url) or ('suertres' in draw_url):
                    link_dict['3d'] = draw_url
                elif ('ez2' in draw_url) or ('2d' in draw_url):
                    link_dict['2d'] = draw_url
            self.parse_done = True
            memcache.add(key='keys', value=link_dict.keys(), time=3600)
            memcache.add_multi(link_dict, key_prefix='link_dict', time=3600)
            return link_dict
    def get_all_links(self):
        return self.parse_links()
    def scrape(self):
        link_dict = None
        partial_result = list()
        scrape_result = list()
        keys = memcache.get('keys')
        if keys is not None:
            link_dict = memcache.get_multi(keys, key_prefix='link_dict')
        if link_dict is None:
            link_dict = self.get_all_links()
        draw = self.draw
        #logging.debug(link_dict)
        if draw in link_dict:
            get_url = link_dict[draw]
        else:
            return 0
        #logging.debug(get_url)
        website = urlfetch.fetch(get_url)
        page = str(website.content)
        tree2 = html.fromstring(page)
        #tree2 = html.parse(get_url).getroot()
        div = tree2.find_class('PostContent')
        p = div[0].find('p')
        cleaner = Cleaner(remove_tags=(['strong']))
        htm = cleaner.clean_html(p)
        for el in htm.xpath('//text()'):
            if len(partial_result) < 4:
                txt=el.strip().encode('utf-8')
                if not len(partial_result):
                    if '55' in txt:
                        txt = '55'
                    if '49' in txt:
                        txt = '49'
                    if '45' in txt:
                        txt = '45'
                    if '42' in txt:
                        txt = '42'
                    if '6d' in txt or 'Six' in txt:
                        txt = '6d'
                    if ('4d' in txt) or ('4D' in txt):
                        txt = '4d'
                    if ('swertres' in txt) or ('Swertres' in txt):
                        txt = '3d'
                    if 'EZ2' in txt:
                        txt = '2d'
                if len(partial_result) == 1:
                    if '4d' in partial_result[0]:
                        txt = txt[-7:]
                    if '6d' in partial_result[0]:
                        txt = txt[-11:]
                    if '3d' in partial_result[0]:
                        txt = txt[-5:]
                    if '2d' in partial_result[0]:
                        txt = txt[-5:]
                if len(partial_result) == 2:
                    if txt.find('Php') != -1:
                        txt = txt[txt.find('Php'):]
                    if '3d' in partial_result[0]:
                        txt = txt[-5:]
                    if '2d' in partial_result[0]:
                        txt = txt[-5:]
                if len(partial_result) == 3:
                    if 'one' in txt:
                        txt = '1'
                    if 'two' in txt:
                        txt = '2'
                    if ('no' in txt) or ('No' in txt):
                        txt = '0'
                    if '3d' in partial_result[0]:
                        txt = txt[-5:]
                    if '2d' in partial_result[0]:
                        txt = txt[-5:]
                partial_result.append(txt)
        temp = []
        if ('6d' in partial_result[0]) or ('4d' in partial_result[0]):
            partial_result = partial_result[:2]
        elif ('42' in partial_result[0]) or \
             ('55' in partial_result[0]) or \
             ('45' in partial_result[0]) or \
             ('49' in partial_result[0]):
            if len(partial_result[3]) > 5: partial_result = partial_result[:3]
            else: partial_result = partial_result[:4]
        elif ('3d' in partial_result[0]) or ('2d' in partial_result[0]):
            for item in partial_result:
                if ':' in item: item = 'n.a'
                temp.append(item)
            partial_result = temp
        scrape_result = partial_result
        logging.debug(scrape_result)
        return scrape_result



app = webapp2.WSGIApplication([('/tasks', cronJob)], debug=True)