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

class Image(db.Model):
    content=db.BlobProperty()
class Region(db.Model):
    name=db.StringProperty()
    fullPath=db.StringProperty()
    
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
    
    def getUrl(self, hostPrefix):
        return "%s/p/%d" %(hostPrefix, self.key().id())
    
    @staticmethod
    def public_attributes():
      """Returns a set of simple attributes on location entities."""
      return [
        'name', 'address', 'country', 
        'administrative_area_level_1',
        'administrative_area_level_2',
        'administrative_area_level_3',
        'locality', 'postal_code', 
        'street_number', 'route',
      ]
class WebRequest(webapp.RequestHandler):
    def post(self):
        self.get()

    def get(self):
        try:
            self.process()
        except:
            self.response.out.write('An error occured:<br/>')
            traceback.print_exc(file=self.response.out)
    def get_domain(self):
        domain_url = self.request.url
        pos = domain_url.find('/', 9) # find the first / after the http:// part
        domain= domain_url[:pos]
        return domain
            
class Save(WebRequest):

    def process(self):
        location=Location()
        locationId=self.request.get('locationId','')
        try:
            location=Location.get_by_id(int(locationId))
        except:
            pass
        location.name=self.request.get("name")
        lat = float(self.request.get('lat'))
        lon = float(self.request.get('lon'))
        location.location=db.GeoPt(lat,lon)
        # Add the geocells to the location object
        location.update_location()

        self.setAddress(location, lat, lon)
        # create image entry


        location.put()
        
        redirectTo=self.request.get('redirectTo','/new')

        self.redirect(redirectTo)

    def setAddress(self, location, lat, lon):
        # Lookup the address
        args = {
            'latlng':"%f,%f" %(lat,lon),
            'sensor': 'false',
        }
        GEOCODE_BASE_URL = "http://maps.google.com/maps/api/geocode/json"
        url = GEOCODE_BASE_URL + '?' +urllib.urlencode(args)
        try:

            strResult = urllib2.urlopen(url)
            result = simplejson.load(strResult)
        except:
            logging.warn("Unable to download address details")
            return
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
        locations = location_query.fetch(100)


        template_values={
            "locations" : locations,
            'domain': self.get_domain()
        }
        self.writeTemplate(template_values, templateName)
class KmlPage(ListingPage):
    def process(self):
        self.showListing('parks.kml', 'application/vnd.google-earth.kml+xml')

class Sitemap(ListingPage):
    def process(self):
        self.showListing('sitemap.xml', 'text/xml')

class MainPage(ListingPage):
    def process(self):
        self.showListing('index.html', 'text/html')

class NewPage(ListingPage):
    def process(self):
        self.showListing('New.html', 'text/html')


def _merge_dicts(*args):
  """Merges dictionaries right to left. Has side effects for each argument."""
  return reduce(lambda d, s: d.update(s) or d, args)

class JsonList(WebRequest):
    def process(self):
        location_query = Location.all()
        locations = location_query.fetch(100)
        public_attrs = Location.public_attributes()
        resultsObj = [
          _merge_dicts({
            'lat': loc.location.lat,
            'lon': loc.location.lon,
            'key_id' : loc.key().id(),
            },
            dict([(attr, getattr(loc, attr))
                  for attr in public_attrs]))
          for loc in locations]

        self.response.out.write(simplejson.dumps(
            {
            'status': 'success',
            'results': resultsObj
            }))
        
class RegionPage(TemplatePage):
    def process(self):
        url = self.request.path
        #id = int(re.split('/', url)[2])
        #location = Location.get_by_id(id)
        m=re.match(r'/r/(.*?)/?region.html', url)
        region = m.group(1)
        name=region
        if region =='':
            name="Top"
        
        region_query = Region.all()
        region_query.filter("name =", name)

        region = region_query.get()


        template_values={
            "region" : region,
            'domain': self.get_domain()
        }
        self.writeTemplate(template_values, "Regions.html")


class LocationPage(TemplatePage):
    templateName = "Location.html"
    idIndex=2
    def process(self):
        url = self.request.path
        id = int(re.split('/', url)[self.idIndex])
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
            'url': location.getUrl(self.get_domain()),
            'nearby':nearby,
        }
        self.writeTemplate(values, self.templateName)

class EditLocationPage(LocationPage):
    templateName = "EditLocation.html"
    idIndex=4

#### Pasted code for review only
class DownloadHandler(LocationPage):
    def get(self):
        url = self.request.path
        match = re.match("/download/(.*)/", url)
        key=match.groups()[0]
        logging.debug ("key: %s" % key)
        payment = db.get(key)
        product = db.get(payment.product_key)
        if product.file_content:
            mimetypes.init()
            self.response.headers['Content-Type'] = mimetypes.guess_type(product.file_name)[0]
            self.response.out.write(product.file_content)
        else:
            self.error(404)
    def xpost(self):
        file_url=self.request.get("file_url")
        file_name=self.request.get("file_name")
        content=self.request.get("content")
        logging.info("upload:" + file_name)

        lower_file_name = file_name.lower()
        if (lower_file_name.endswith(".mht") or lower_file_name.endswith(".mhtml") ):
            self.process_mht_file(content, file_url)
        else:
            page = self.get_page_for_write(file_url)
            page.url = file_url
            page.html = content
            page.title = "test"
            page.include_n_sitemap = False
            page.put()
########## End pasted code.
            

application = webapp.WSGIApplication(
                [
                    ('/', MainPage),
                    ('/parks.kml', KmlPage),
                    ('/sitemap.xml', Sitemap),
                    ('/parks.json', JsonList),
#                    ('/p/[0-9]+/', LocationPage),
                    ('/p/.*/', LocationPage),
                    ('/r/.*', RegionPage),
                    ('/new', NewPage),
                    ('/actions/save/p', Save),
                    ('/actions/edit/p/.*/',EditLocationPage)
                ], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()