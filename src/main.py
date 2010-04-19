import os
import re
import traceback
import urllib
import urllib2
import simplejson

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

from geo.geomodel import GeoModel
from geo import geotypes

class Location(GeoModel):
    name = db.StringProperty()
    address=db.StringProperty()

class WebRequest(webapp.RequestHandler):
    def post(self):
        self.get()

    def get(self):
        try:
            self.process()
        except:
            self.response.out.write('An error occured:<br/>')
            traceback.print_exc(file=self.response.out)
            
class Save(webapp.RequestHandler):
    def get(self):
        location = Location()
        location.name=self.request.get("name")
        lat = float(self.request.get('lat'))
        lon = float(self.request.get('lon'))
        location.location=db.GeoPt(lat,lon)
        # Add the geocells to the location object
        location.update_location()

        # Lookup the address
        args = {
            'latlng':"%f,%f" %(lat,lon),
            'sensor': 'false',
        }
        GEOCODE_BASE_URL = "http://maps.google.com/maps/api/geocode/json"
        url = GEOCODE_BASE_URL + '?' +urllib.urlencode(args)

        strResult = urllib2.urlopen(url)
        result = simplejson.load(strResult)
        status = result['status']
        if (status == 'OK'):
            location.address = result['results'][0]['formatted_address']


        location.put()
        self.redirect('/')

class TemplatePage(WebRequest):
    def writeTemplate(self, values, templateName):

        path = os.path.join(os.path.dirname(__file__), 'templates',  templateName)
        self.response.out.write(template.render(path, values))

class ListingPage(TemplatePage):
    def showListing(self, templateName, contenttype):
        self.response.headers['Content-Type'] = contenttype

        location_query = Location.all()
        locations = location_query.fetch(10)


        template_values={
            "locations" : locations,
        }
        self.writeTemplate(template_values, templateName)

class KmlPage(ListingPage):
    def process(self):
        self.showListing('parks.kml', 'application/vnd.google-earth.kml+xml')

class MainPage(ListingPage):
    def process(self):
        self.showListing('index.html', 'text/html')

class LocationPage(TemplatePage):
    def process(self):
        url = self.request.path
        id = int(re.split('/', url)[2])
        location = Location.get_by_id(id)


        base_query = Location.all()
#        center = location.location

        center = geotypes.Point(float(location.location.lat),
                                float(location.location.lon))

        max_results=10
        max_distance=8000000

        nearby = Location.proximity_fetch(base_query, center,
                                          max_results=max_results,
                                          max_distance=max_distance)


        values={
            'loc':location,
            'nearby':nearby,
        }
        self.writeTemplate(values, "Location.html")

application = webapp.WSGIApplication(
                [
                    ('/', MainPage),
                    ('/parks.kml', KmlPage),
#                    ('/p/[0-9]+/', LocationPage),
                    ('/p/.*/', LocationPage),
                    ('/new', Save),
                ], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()