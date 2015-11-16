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

        rates_query = RateHistory.query().order(-RateHistory.date)
        rates = rates_query.fetch(100)

        yahoo = "(%s - %s) %s" %(value['low'], value['high'], value['today'])

        template_values = {
            'money' : {'yahoo': yahoo},
            'rates': rates
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


class Real(webapp2.RequestHandler):

    def getCRUSDINR(self, url):
        result = urlfetch.fetch(url)
        p = re.search('Rate <img src="images/icon_rupees.jpg" style="vertical-align:text-top;">.*', result.content)
        t =  p.group()
        p = re.search('[0-9]+\.[0-9]+', t)
        return p.group()

    def getCRTopUSDINR(self):
        rate = urlfetch.fetch('http://www.compareremit.com/calculation/today_exchange_rate/1').content
        provider = urlfetch.fetch('http://www.compareremit.com/calculation/today_exchange_rate/4').content
        return {'rate': rate, 'provider': provider}

    def get(self):
        ria = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/ria-money-transfer/')
        western_union = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/western-union/')
        transwise = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/transferwise/')
        xoom = self.getCRUSDINR('http://www.compareremit.com/money-transfer-companies/xoom/')
        top = self.getCRTopUSDINR()
        resp = {
            'top': top,
            'rates': [
                {'label': 'WU', 'value': western_union},
                {'label': 'Ria', 'value': ria},
                {'label': 'TransferWise', 'value': transwise},
                {'label': 'Xoom', 'value': xoom}
            ]
        };
        self.response.out.write(json.dumps(resp))
        

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/real', Real),
], debug=True)
