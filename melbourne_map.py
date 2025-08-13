#!/usr/bin/env python3
"""
Melbourne CBD Map Plotter - Fast Version
Shows a map of Melbourne CBD with 10 addresses plotted using hardcoded coordinates.
"""

import folium

def create_melbourne_cbd_map():
    """
    Create and display a map of Melbourne CBD with 10 addresses plotted.
    """
    # Melbourne CBD addresses with hardcoded coordinates
    addresses = [
        {
            'address': '340 Lygon Street, Melbourne VIC 3053',
            'latitude': -37.799086,
            'longitude': 144.967491
        },
        {
            'address': '123 Collins Street, Melbourne VIC 3000',
            'latitude': -37.815156,
            'longitude': 144.969836
        },
        {
            'address': '456 Bourke Street, Melbourne VIC 3000',
            'latitude': -37.816761,
            'longitude': 144.954126
        },
        {
            'address': '789 Swanston Street, Melbourne VIC 3000',
            'latitude': -37.808782,
            'longitude': 144.963391
        },
        {
            'address': '234 Flinders Street, Melbourne VIC 3000',
            'latitude': -37.818617,
            'longitude': 144.963741
        },
        {
            'address': 'Federation Square, Melbourne VIC 3000',
            'latitude': -37.8180,
            'longitude': 144.9691
        },
        {
            'address': '890 La Trobe Street, Melbourne VIC 3000',
            'latitude': -37.808047,
            'longitude': 144.969335
        },
        {
            'address': 'Melbourne Central, Melbourne VIC 3000',
            'latitude': -37.8100,
            'longitude': 144.9540
        },
        {
            'address': '654 Exhibition Street, Melbourne VIC 3000',
            'latitude': -37.807636,
            'longitude': 144.968466
        },
        {
            'address': 'Flinders Street Station, Melbourne VIC 3000',
            'latitude': -37.8183,
            'longitude': 144.9671
        }
    ]
    
    print(f"Using {len(addresses)} Melbourne CBD addresses with hardcoded coordinates")
    
    # Create the map centered on Melbourne CBD
    melbourne_cbd_coords = [-37.8136, 144.9631]  # Melbourne CBD coordinates
    m = folium.Map(location=melbourne_cbd_coords, zoom_start=14, tiles='OpenStreetMap')
    
    # Add a title to the map
    title_html = '''
        <h3 align="center" style="font-size:16px"><b>Melbourne CBD Addresses</b></h3>
        '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add markers for each address
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']
    
    for i, location in enumerate(addresses, 1):
        # Create popup text
        popup_text = f"<b>Location {i}</b><br>{location['address']}<br>Coordinates: {location['latitude']:.6f}, {location['longitude']:.6f}"
        
        # Add marker with different colors for variety
        color = colors[(i-1) % len(colors)]
        
        folium.Marker(
            location=[location['latitude'], location['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"Location {i}: {location['address']}",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)
    
    # Add a legend
    legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 90px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>Melbourne CBD Map</b></p>
        <p>- Red markers: Addresses 1-2</p>
        <p>- Blue markers: Addresses 3-4</p>
        <p>- Green markers: Addresses 5-6</p>
        <p>- Purple markers: Addresses 7-8</p>
        <p>- Orange markers: Addresses 9-10</p>
        </div>
        '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save the map to an HTML file
    m.save('melbourne_cbd_map_fast.html')
    print("Map saved as 'melbourne_cbd_map_fast.html'")
    print("You can open this file in your web browser to view the interactive map")
    
    # Display summary of addresses
    print("\n=== Summary of Melbourne CBD Addresses ===")
    for i, location in enumerate(addresses, 1):
        print(f"{i:2d}. {location['address']}")
        print(f"    Coordinates: {location['latitude']:.6f}, {location['longitude']:.6f}")
        print()
    
    return m

if __name__ == "__main__":
    # Create and display the map
    map_obj = create_melbourne_cbd_map()
    print("Map creation completed!")
    print("Open 'melbourne_cbd_map_fast.html' in your web browser to view the interactive map.") 