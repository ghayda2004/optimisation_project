import os

def generate_map_html(route_data, output_dir="outputs"):
    """
    Génère un fichier HTML autonome avec Leaflet.js et OSRM pour visualiser la route.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    driver_id = route_data['driver_id']
    filename = f"map_driver_{driver_id}.html"
    filepath = os.path.join(output_dir, filename)

    # Préparation des données pour le JS
    depot = route_data['depot']
    stops = route_data['stops']
    
    # Construction de la liste des coordonnées pour OSRM (Format: lon,lat;lon,lat)
    osrm_coords = f"{depot['lng']},{depot['lat']};"
    osrm_coords += ";".join([f"{s['lng']},{s['lat']}" for s in stops])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Route Chauffeur {route_data['driver_name']}</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; font-family: sans-serif; }}
            #header {{ 
                background: #2d6a4f; color: white; padding: 15px; 
                display: flex; justify-content: space-between; align-items: center;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2); position: relative; z-index: 1000;
            }}
            #map {{ height: calc(100vh - 70px); width: 100vw; }}
            .stats {{ font-weight: bold; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div id="header">
            <div><b>Chauffeur:</b> {route_data['driver_name']}</div>
            <div class="stats">
                📦 {route_data['nb_colis']} colis | 
                📍 {route_data['total_distance_km']} km | 
                💰 Gain: {route_data['gain_net']} DT
            </div>
        </div>
        <div id="map"></div>

        <script>
            var map = L.map('map');

            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);

            var stops = [
                {{ "lat": {depot['lat']}, "lng": {depot['lng']}, "info": "DÉPÔT (Départ)", "color": "blue" }},
                {", ".join([f'{{ "lat": {s["lat"]}, "lng": {s["lng"]}, "info": "Arrêt {s["sequence"]}: {s["client"]}<br>{s["adresse"]}", "color": "green" }}' for s in stops])}
            ];

            var bounds = [];

            // Ajouter les marqueurs
            stops.forEach(function(s, index) {{(
                var marker = L.marker([s.lat, s.lng]).addTo(map);
                marker.bindPopup(s.info);
                bounds.push([s.lat, s.lng]);
            )}});

            // Tracer la route via OSRM
            var osrmUrl = "https://router.project-osrm.org/route/v1/driving/{osrm_coords}?overview=full&geometries=geojson";
            
            fetch(osrmUrl)
                .then(response => response.json())
                .then(data => {{
                    var route = data.routes[0].geometry;
                    L.geoJSON(route, {{
                        style: {{ color: '#2d6a4f', weight: 6, opacity: 0.7 }}
                    }}).addTo(map);
                    
                    map.fitBounds(bounds, {{ padding: [50, 50] }});
                }});
        </script>
    </body>
    </html>
    """

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return filepath