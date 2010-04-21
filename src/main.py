import os
import re
import traceback
import urllib
import urllib2
import simplejson
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

from geo.geomodel import GeoModel
from geo import geotypes

class Location(GeoModel):
    name = db.StringProperty()
    address=db.StringProperty()
    addressStatus=db.StringProperty()

    country=db.StringProperty()
    administrative_area_level_1=db.StringProperty()
    administrative_area_level_2=db.StringProperty()
    administrative_area_level_3=db.StringProperty()
    locality=db.StringProperty()
    postal_code=db.StringProperty()
    street_number=db.StringProperty()
    route=db.StringProperty()
    
    creationDate = db.DateTimeProperty(auto_now_add=True)
    modificationDate = db.DateTimeProperty(auto_now=True)

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

        self.setAddress(location, lat, lon)

        location.put()
        self.redirect('/')
    def setAddress(self, location, lat, lon):
        # Lookup the address
        args = {
            'latlng':"%f,%f" %(lat,lon),
            'sensor': 'false',
        }
        GEOCODE_BASE_URL = "http://maps.google.com/maps/api/geocode/json"
        url = GEOCODE_BASE_URL + '?' +urllib.urlencode(args)

        strResult = urllib2.urlopen(url)
        result = simplejson.load(strResult)
        logging.info("JSON Result =" + simplejson.dumps(result))
        status = result['status']
        location.addressStatus = status
        if (status == 'OK'):
            #location.address = result['results'][0]['formatted_address']
            for entry in result['results']:
                #logging.info(entry)
                #if (entry['types'][0] == 'street_address'):
                if ('street_address' in entry['types']):
                    location.address = entry['formatted_address']
                    for component in entry['address_components']:
                        if ('country' in component['types']):
                            location.country = component['long_name']
                        if ('administrative_area_level_1' in component['types']):
                            location.administrative_area_level_1 = component['long_name']
                        if ('administrative_area_level_2' in component['types']):
                            location.administrative_area_level_2 = component['long_name']
                        if ('administrative_area_level_3' in component['types']):
                            location.administrative_area_level_3 = component['long_name']
                        if ('locality' in component['types']):
                            location.locality = component['long_name']
                        if ('route' in component['types']):
                            location.route = component['long_name']
                        if ('street_number' in component['types']):
                            location.street_number = component['long_name']                        
                        if ('postal_code' in component['types']):
                            pc = component['long_name']
                            if (pc in location.address):
                                location.postal_code = component['long_name']
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
            'domain': self.get_domain()
        }
        self.writeTemplate(template_values, templateName)
    def get_domain(self):
        domain_url = self.request.url
        pos = domain_url.find('/', 9) # find the first / after the http:// part
        domain= domain_url[:pos]
        return domain
class KmlPage(ListingPage):
    def process(self):
        self.showListing('parks.kml', 'application/vnd.google-earth.kml+xml')

class Sitemap(ListingPage):
    def process(self):
        self.showListing('sitemap.xml', 'text/xml')

class MainPage(ListingPage):
    def process(self):
        self.showListing('index.html', 'text/html')

class RegionPage(TemplatePage):
    def process(self):
        url = self.request.path
        id = int(re.split('/', url)[2])
        location = Location.get_by_id(id)
    
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
                    ('/sitemap.xml', Sitemap),
#                    ('/p/[0-9]+/', LocationPage),
                    ('/p/.*/', LocationPage),
                    ('/r/.*', RegionPage),
                    ('/new', Save),
                ], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()