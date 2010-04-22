function initialize() {
    var latlng = new google.maps.LatLng( -27.4396, 152.987612 );
    var myOptions = {
    zoom: 14,
    center: latlng,
    mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    var map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);

	function createMarker(point,name, infowindow, html) {
	    var marker = new google.maps.Marker({
		              position: point,
		              title:name
		            });
	    google.maps.event.addListener(marker, "click", function() {
            
            
            infowindow.setContent(html);
            infowindow.open(map,marker);
	    });
	    return marker;
	}

    $.getJSON('parks.json', 
    	function(data) {
			if (data.status && data.status == 'success') {
			var infowindow = new google.maps.InfoWindow({});
		        for (var i = 0; i < data.results.length; i++) {
        			var loc = data.results[i];
        			var infoWindowHTML = 
        				"<b>Name:</b> <a href='/p/" + loc.key_id +"/'>" + loc.name + "</a><br/><b>latlng:</b>"+loc.lat+","+loc.lon+"<br>";
        			
				    var point = new google.maps.LatLng(loc.lat, loc.lon);
				    var marker = createMarker(point,loc.name,infowindow, infoWindowHTML)
			      	marker.setMap(map);
		        }
			}
		}
	);
    
}



function createResultMarker(result) {
	var icon = new google.maps.Icon(G_DEFAULT_ICON);
	icon.image = result.icon;
	icon.iconSize = new google.maps.Size(21, 34);
	
	var resultLatLng = new google.maps.LatLng(result.lat, result.lng);
	  
	var marker = new google.maps.Marker(resultLatLng, {
	icon: icon,
	title: result.name
	});
  
  	google.maps.Event.addListener(marker, 'click', (function(result) {
  		return function() {
	    	if (g_listView && result.listItem) {
				$.scrollTo(result.listItem, {duration: 1000});
			} else {
		        var infoHtml = tmpl('tpl_result_info_window', { result: result });

				map.openInfoWindowHtml(marker.getLatLng(), infoHtml, {
  					pixelOffset: new GSize(icon.infoWindowAnchor.x - icon.iconAnchor.x,
                         icon.infoWindowAnchor.y - icon.iconAnchor.y)});
	      	}
    	};
		})(result));
  
		return marker;
}
