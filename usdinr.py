import datetime
import jinja2
import json
import os
import re
import time
import webapp2

from bs4 import BeautifulSoup, SoupStrainer
from google.appengine.api import urlfetch
from google.appengine.ext import ndb


def date_to_millis(d):
    """Converts a datetime object to the number of milliseconds since the unix epoch."""
    return int(time.mktime(d.timetuple())) * 1000

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    variable_start_string= '{[{',
    variable_end_string= '}]}',
    autoescape=True)

JINJA_ENVIRONMENT.filters['date_to_millis'] = date_to_millis

class RateHistory(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    ex = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class MonthMax(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    max_rate = ndb.FloatProperty(indexed=False)
    date = ndb.DateTimeProperty()
    max_date = ndb.DateTimeProperty(auto_now_add=True)

class MainPage(webapp2.RequestHandler):

    def getYUSDINR(self, url):
        result = urlfetch.fetch(url)
        soup = BeautifulSoup(result.content, 'html.parser')
        low = soup.find("b", {"data-sq": "USDINR=X:low"}).getText()
        high = soup.find("b", {"data-sq": "USDINR=X:high"}).getText()
        today = soup.find("span", {"id": "yfs_l84_USDINR=X"}).getText()
        return {'low': low, 'high': high, 'today': today}
    
    def get(self):
        
        value = self.getYUSDINR("http://finance.yahoo.com/echarts?s=USDINR=X")

        history = RateHistory()
        history.ex = value['today']
        history.put()


        month_date = datetime.datetime.strptime("%s-%s-2"%(datetime.date.today().year, datetime.date.today().month), '%Y-%m-%d')
        results = MonthMax.query(MonthMax.date == month_date).fetch()
        high_float_value = float(value['high'])
        if results:
            if results[0].max_rate < high_float_value:
                results[0].max_rate = high_float_value
                results[0].put()
        else:
            maxi = MonthMax()
            maxi.max_rate = high_float_value
            maxi.date = month_date
            maxi.put()

        results = MonthMax.query().fetch()

        rates_query = RateHistory.query().order(-RateHistory.date)
        rates = rates_query.fetch(100)

        yahoo = "(%s - %s) %s" %(value['low'], value['high'], value['today'])

        template_values = {
            'money' : {'yahoo': yahoo},
            'rates': rates,
            'results': results
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


class Real(webapp2.RequestHandler):

    def getCRUSDINR(self, url):
        value = "N/A"
        try:
            result = urlfetch.fetch(url)
            p = re.search('Rate <img src="images/icon_rupees.jpg" style="vertical-align:text-top;">.*', result.content)
            t =  p.group()
            p = re.search('[0-9]+\.[0-9]+', t)
            value = p.group()
        except:
            pass
        return value

    def getCRTopUSDINR(self):
        rate = urlfetch.fetch('http://www.compareremit.com/calculation/today_exchange_rate/1').content
        provider = urlfetch.fetch('http://www.compareremit.com/calculation/today_exchange_rate/4').content
        return {'label': provider, 'value': rate, 'ref': ''}

    def get(self):
        ria = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/ria-money-transfer/')
        western_union = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/western-union/')
        transwise = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/transferwise/')
        xoom = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/xoom/')
        resp = [
                {'label': 'WU', 'value': western_union,'ref': 'https://refer.westernunion.com/mt-mgm-us/recipient'},
                {'label': 'Ria', 'value': ria, 'ref': 'http://refer.riamoneytransfer.com/v2/share/6189557156121780477/6c616b73686d6973616e746869707269796140676d61696c2e636f6d'},
                {'label': 'TransferWise', 'value': transwise, 'ref': 'https://transferwise.com/u/66beb6'},
                {'label': 'Xoom', 'value': xoom, 'ref': 'http://refer.xoom.com/v2/share/6182101262079424292'},
        ];
        self.response.out.write(json.dumps(resp))
        

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/real', Real),
], debug=True)
