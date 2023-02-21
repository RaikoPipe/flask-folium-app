import html
import os
import sys
import traceback
import webbrowser

import branca.element
import folium
import numpy as np
import pandas
from folium.plugins import FastMarkerCluster
from folium.plugins import Fullscreen, HeatMap
from branca.element import Template, MacroElement
from folium.plugins import MarkerCluster

import geopandas
import logging

from geopandas import GeoSeries, GeoDataFrame
from shapely.geometry import Point

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

districts = ["Mansfeld-Südharz"]
roads = {"motorway": "red", "trunk": "orange", "primary": "yellow", "secondary": "green", "tertiary": "blue"}
railways = {"rail": "magenta", "light_rail": "brown", "tram": "light_blue"}

landuse_exceptions = ("forest", "meadow", "military", "quarry", "orchard", "vineyard", "scrub", "grass", "heath",
                      "farmland", "farmyard", "national_park", "nature_reserve", "allotments")

transport_station_exceptions = ("taxi", "taxi_rank", "helipad", "apron", "ferry_terminal", "airport", "airfield",
                                "aerialway_station")

poi_categories = {
    # health
    **dict.fromkeys(["clinic", "hospital", "doctors", "pharmacy", ], "health"),
    # education
    **dict.fromkeys(["university", "school", "college", "library"], "education"),
    # tourism
    **dict.fromkeys(["arts_centre", "tourist_info", "tourist_guidepost", "attraction",
                     "museum", "monument", "zoo", "theme_park", "hotel", "bed_and_breakfast", "guesthouse",
                     ""], "tourism"),
    # leisure
    **dict.fromkeys(["cinema", "theatre", "night_club", "community_centre", "restaurant", "fast_food", "pub", "bar", ],
                    "leisure"),
    # shopping
    **dict.fromkeys(["supermarket", "bakery", "kiosk", "mall", "department_store", "general", "convenience", "clothes",
                     "florist", "chemist", "bookshop", "butcher", "shoe_shop", "beverages", "optician", "jeweller",
                     "gift_shop",
                     "sports_shop", "stationery", "outdoor_shop", "mobile_phone_shop", "toy_shop", "newsagent",
                     "sports_shop", "stationery", "outdoor_shop", "mobile_phone_shop", "toy_shop", "newsagent",
                     "greengrocer", "beauty_shop", "video_shop", "car_dealership", "bicycle_shop", "doityourself",
                     "furniture_shop", "computer_shop", "garden_centre", "hairdresser", "car_repair", "car_sharing",
                     "bicycle_rental", "travel_agent", "laundry"], "shopping"),
    # mobility services
    **dict.fromkeys(["car_sharing", "bicycle_rental"], "mobility"),
}

poi_category_color = {"health": "green", "tourism": "blue", "shopping": "yellow", "leisure": "red",
                      "education": "black", "mobility": "lightblue"}

parking = {"parking": 0, "parking_site": 0, "parking_multistorey": 0, "parking_underground": 0, "parking_bicycle": 0}

transport_station_hierarchy = {
    **dict.fromkeys(["railway_station", "railway_halt"], 0),
    **dict.fromkeys(["bus_station"], 1),
    **dict.fromkeys(["bus_stop", "tram_stop"], 2)}

hierarchy_distance = {0: 100, 1: 100, 2: 50}


def remove_exceptions_from_data(geo_data_frame, exceptions):
    drop = []
    for idx, geometry, fclass, name in geo_data_frame.get(["geometry", "fclass", "name"]).itertuples(
            index=True):

        if isinstance(exceptions, dict):
            if fclass not in exceptions.keys():
                drop.append(idx)
        elif isinstance(exceptions, list) or isinstance(exceptions, tuple):
            if fclass in exceptions:
                drop.append(idx)

    return geo_data_frame.drop(labels=drop, axis=0)


def remove_redundant(geo_data_frame):
    # option 1
    # points_within_bounds.drop_duplicates(subset=["name"])
    # option 2

    geo_data_frame = geo_data_frame.to_crs(32643)
    drop = []
    # filter according to hierarchy; if hierarchy is same, drop
    for idx_1, geometry_1, fclass_1, name_1 in geo_data_frame.get(["geometry", "fclass", "name"]).itertuples(
            index=True):
        for idx_2, geometry_2, fclass_2, name_2 in geo_data_frame.get(["geometry", "fclass", "name"]).itertuples(
                index=True):
            check_distance = hierarchy_distance[transport_station_hierarchy[fclass_1]]
            if geometry_1.distance(geometry_2) < check_distance and idx_1 != idx_2:
                if transport_station_hierarchy[fclass_1] <= transport_station_hierarchy[fclass_2]:
                    drop.append(idx_2)
    geo_data_frame = geo_data_frame.drop(labels=drop, axis=0)
    geo_data_frame = geo_data_frame.to_crs(4326)
    return geo_data_frame


def remove_duplicates(geo_data_frame):
    """removes stations with the same name."""
    return geo_data_frame.drop_duplicates(subset=["name"])


def get_bounds(files, filter):
    concat = []
    for file in files:
        data = geopandas.read_file(
            ROOT_DIR + rf'/data/{file}', encoding='utf-8')
        data = data.to_crs(4326)

        concat.append(data)

    df = geopandas.GeoDataFrame(pandas.concat(concat))

    bounds = {}

    for geometry, name in df.get(
            ["geometry", "GN_KLAR"]).itertuples(index=False):
        if name in filter:
            sim_geo = geopandas.GeoSeries(geometry)
            bounds[name] = geopandas.GeoDataFrame(geometry=sim_geo)

    return bounds


class Map:
    def __init__(self):
        """create the base map"""

        logging.info("Creating Base Map...")
        # create base map
        self.map = folium.Map(location=(51.5074631, 11.4801049), zoom_start=10, min_zoom=4, tiles="OpenStreetMap",
                              prefer_canvas=True)

        folium.TileLayer("CartoDB positron").add_to(self.map)
        folium.TileLayer("CartoDB dark_matter").add_to(self.map)

        self.test_point = folium.Circle(location=(51.5184191, 11.5490143), radius=300)
        self.test_point.get_bounds()

        logging.info("Adding layers")
        self.bounds: GeoDataFrame = self.get_district_bounds()
        self.add_railways()
        self.add_roads()
        self.add_landuse_a_fg()
        self.add_test_marker_fg()
        self.add_transport_stations()
        # self.add_pois_fg()
        self.add_landkreis()
        # self.add_buildings_a_fg()
        self.add_parking_fg()
        # self.add_login_window()
        self.add_pois_near_stations()
        # self.add_parking_near_stations()
        self.add_parking_zones()

        logging.info("Adding plugins...")
        fs = Fullscreen()
        self.map.add_child(fs)

        folium.LayerControl().add_to(self.map)

        logging.info("Saving html...")

        # popup.render()
        self.map.save("templates\\map.html")
        logging.info("DONE!")

    def get_district_bounds(self):
        landkreis_data = geopandas.read_file(
            ROOT_DIR + r'/data/Landkreise_und_kreisfreie_Staedte.zip', encoding='utf-8')
        landkreis_data = landkreis_data.to_crs(4326)

        for geometry, name in landkreis_data.get(
                ["geometry", "GN_KLAR"]).itertuples(index=False):
            if name in districts:
                sim_geo = geopandas.GeoSeries(geometry)
                self.bounds = geopandas.GeoDataFrame(geometry=sim_geo)

        return self.bounds

    def add_landkreis(self):
        landkreis_data = geopandas.read_file(
            ROOT_DIR + r'/data/Landkreise_und_kreisfreie_Staedte.zip', encoding='utf-8')
        landkreis_data = landkreis_data.to_crs(4326)

        landkreise_fg = folium.FeatureGroup(name="Landkreise")

        for geometry, name in landkreis_data.get(
                ["geometry", "GN_KLAR"]).itertuples(index=False):
            if name in districts:
                sim_geo = geopandas.GeoSeries(geometry)
                geo_j = sim_geo.to_json()
                geo_folium = folium.GeoJson(data=geo_j, zoom_on_click=True, style_function=lambda x: {"color": "black"})
                geo_folium.add_to(landkreise_fg)

        landkreise_fg.add_to(self.map)

    def add_pois_fg(self):
        # todo: only add POIs that are within the radius of a station
        pois_data = geopandas.read_file(
            ROOT_DIR + r'/data/pois.zip', encoding='utf-8')
        pois_data.to_crs(4326)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(pois_data, self.bounds, predicate="within")

        # make a heat map layer
        pois_geo = points_within_bounds.get("geometry")
        pois_array = np.array([(point.y, point.x) for point in pois_geo])
        heatmap = HeatMap(data=pois_array, name="Heatmap All POIs")
        heatmap.add_to(self.map)

        poi_fg_sorted = {}
        poi_marker_cluster = {}

        for data, fclass, name in zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass"),
                                      points_within_bounds.get("name")):
            category = poi_categories.get(fclass)
            if category not in poi_fg_sorted.keys() and fclass in poi_categories.keys():
                category = poi_categories[fclass]
                # update keys and marker cluster if fg doesn't exist yet
                poi_fg_sorted.update({category: folium.FeatureGroup(name=category)})
                poi_marker_cluster.update({category: MarkerCluster(name=f"{category} marker cluster")})

            if fclass in poi_categories.keys():
                folium.Circle(location=(data.y, data.x), fill=True, radius=5, tooltip=fclass,
                              color=poi_category_color[category]).add_to(
                    poi_fg_sorted[category])
                folium.Marker(location=(data.y, data.x), tooltip=fclass).add_to(poi_marker_cluster[category])

        for fg in poi_fg_sorted.values():
            fg.add_to(self.map)

        for mc in poi_marker_cluster.values():
            mc.add_to(self.map)

    def add_pois_near_stations(self):
        pois_data = geopandas.read_file(
            ROOT_DIR + r'/data/pois.zip', encoding='utf-8')
        pois_data.to_crs(4326)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(pois_data, self.bounds, predicate="within")
        points_within_bounds = remove_exceptions_from_data(points_within_bounds, poi_categories)
        points_within_bounds = self.get_geo_data_within_stations(points_within_bounds)

        # make a heat map layer
        pois_geo = points_within_bounds.get("geometry")
        pois_array = np.array([(point.y, point.x) for point in pois_geo])
        heatmap = HeatMap(data=pois_array, name="Heatmap All POIs NS")
        heatmap.add_to(self.map)

        poi_fg_sorted = {}
        poi_marker_cluster = {}

        for data, fclass, name in zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass"),
                                      points_within_bounds.get("name")):
            category = poi_categories.get(fclass)
            if category not in poi_fg_sorted.keys() and fclass in poi_categories.keys():
                category = poi_categories[fclass]
                # update keys and marker cluster if fg doesn't exist yet
                poi_fg_sorted.update({category: folium.FeatureGroup(name=category)})
                poi_marker_cluster.update({category: MarkerCluster(name=f"{category} marker cluster NS")})

            if fclass in poi_categories.keys():
                folium.Circle(location=(data.y, data.x), fill=True, radius=5, tooltip=fclass,
                              color=poi_category_color[category], popup=folium.Popup(name)).add_to(
                    poi_fg_sorted[category])
                folium.Marker(location=(data.y, data.x), tooltip=fclass).add_to(poi_marker_cluster[category])

        for fg in poi_fg_sorted.values():
            fg.add_to(self.map)

        for mc in poi_marker_cluster.values():
            mc.add_to(self.map)

    def add_parking_fg(self):
        parking_data = geopandas.read_file(
            ROOT_DIR + r'/data/traffic.zip', encoding='utf-8')
        parking_data.to_crs(4326)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(parking_data, self.bounds, predicate="within")

        parking_marker_cluster = MarkerCluster(name="parking marker cluster")

        # make a heat map layer
        pois_geo = points_within_bounds.get("geometry")
        pois_array = np.array([(point.y, point.x) for point in pois_geo])
        heatmap = HeatMap(data=pois_array, name="Heatmap Parking")
        heatmap.add_to(self.map)

        parking_fg = folium.FeatureGroup(name="Parking")

        for data, fclass in zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass")):

            if fclass in parking.keys():
                folium.Circle(location=(data.y, data.x), fill=True, radius=5, tooltip=fclass).add_to(
                    parking_fg)
                folium.Marker(location=(data.y, data.x), tooltip=fclass).add_to(parking_marker_cluster)

        parking_marker_cluster.add_to(self.map)
        parking_fg.add_to(self.map)

    def add_parking_near_stations(self):
        parking_data = geopandas.read_file(
            ROOT_DIR + r'/data/traffic.zip', encoding='utf-8')
        parking_data.to_crs(4326)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(parking_data, self.bounds, predicate="within")
        points_within_bounds = remove_exceptions_from_data(points_within_bounds, parking)
        points_within_bounds = self.get_geo_data_within_stations(points_within_bounds)

        parking_marker_cluster = MarkerCluster(name="parking marker cluster")

        # make a heat map layer
        pois_geo = points_within_bounds.get("geometry")
        pois_array = np.array([(point.y, point.x) for point in pois_geo])
        heatmap = HeatMap(data=pois_array, name="Heatmap Parking")
        heatmap.add_to(self.map)

        parking_fg = folium.FeatureGroup(name="Parking NS")

        for data, fclass in zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass")):
            folium.Circle(location=(data.y, data.x), fill=True, radius=5, tooltip=fclass).add_to(
                parking_fg)
            folium.Marker(location=(data.y, data.x), tooltip=fclass).add_to(parking_marker_cluster)

        parking_marker_cluster.add_to(self.map)
        parking_fg.add_to(self.map)
        pass

    def add_landuse_a_fg(self):
        landuse_data = geopandas.read_file(
            ROOT_DIR + r'/data/gis_osm_landuse_a_free_1.zip', encoding='utf-8')

        landuse_data.to_crs(4326)

        landuse_fg = folium.FeatureGroup(name="Landnutzung")
        #
        # for polygon, fclass in zip(landuse_data.get("geometry"), landuse_data.get("fclass")):
        #     if fclass not in landuse_exceptions:
        #         locations = zip(*[iter(polygon)] * 2)
        #
        #         folium.Polygon(locations=locations, fill=True, radius=5, tooltip=fclass).add_to(landuse_fg)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(landuse_data, self.bounds, predicate="within")

        for geometry, fclass in points_within_bounds.get(
                ["geometry", "fclass"]).itertuples(index=False):
            if fclass not in landuse_exceptions:
                sim_geo = geopandas.GeoSeries(geometry)
                geo_j = sim_geo.to_json()
                geo_folium = folium.GeoJson(data=geo_j, tooltip=fclass,
                                            style_function=lambda x: {"fillColor": "blue"})
                geo_folium.add_to(landuse_fg)

        landuse_fg.add_to(self.map)
        self.map.keep_in_front(landuse_fg)

    def add_buildings_a_fg(self):
        buildings_data = geopandas.read_file(
            ROOT_DIR + r'/data/gis_osm_buildings_a_free_1.zip', encoding='utf-8')

        buildings_data.to_crs(4326)

        buildings_fg = folium.FeatureGroup(name="Buildings")
        #
        # for polygon, fclass in zip(buildings_data.get("geometry"), buildings_data.get("fclass")):
        #     if fclass not in buildings_exceptions:
        #         locations = zip(*[iter(polygon)] * 2)
        #
        #         folium.Polygon(locations=locations, fill=True, radius=5, tooltip=fclass).add_to(buildings_fg)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(buildings_data, self.bounds, predicate="within")

        for geometry, fclass in points_within_bounds.get(
                ["geometry", "fclass"]).itertuples(index=False):
            sim_geo = geopandas.GeoSeries(geometry)
            geo_j = sim_geo.to_json()
            geo_folium = folium.GeoJson(data=geo_j, tooltip=fclass,
                                        style_function=lambda x: {"fillColor": "blue"})
            geo_folium.add_to(buildings_fg)

        buildings_fg.add_to(self.map)
        self.map.keep_in_front(buildings_fg)

    def add_parking_zones(self):
        parking_data = geopandas.read_file(
            ROOT_DIR + r'/data/gis_osm_traffic_a_free_1.zip', encoding='utf-8')

        parking_data.to_crs(4326)
        parking_data = geopandas.sjoin(parking_data, self.bounds)
        parking_data = self.get_geo_data_within_stations(parking_data)

        parking_fg = folium.FeatureGroup(name="Parking Zones")

        #
        # for polygon, fclass in zip(buildings_data.get("geometry"), buildings_data.get("fclass")):
        #     if fclass not in buildings_exceptions:
        #         locations = zip(*[iter(polygon)] * 2)
        #
        #         folium.Polygon(locations=locations, fill=True, radius=5, tooltip=fclass).add_to(buildings_fg)

        # filter points in chosen district
        parking_data = parking_data.drop(['index_right'], axis=1)
        # parking_data.rename("index_right", "idx_r")
        points_within_bounds = geopandas.sjoin(parking_data, self.bounds, predicate="intersects")

        for geometry, fclass in points_within_bounds.get(
                ["geometry", "fclass"]).itertuples(index=False):
            if fclass in parking.keys():
                sim_geo = geopandas.GeoSeries(geometry)
                geo_j = sim_geo.to_json()
                geo_folium = folium.GeoJson(data=geo_j, tooltip=fclass,
                                            style_function=lambda x: {"fillColor": "blue"})
                geo_folium.add_to(parking_fg)

        parking_fg.add_to(self.map)

    def add_flur_test_fg(self):
        flur_data = geopandas.read_file(
            ROOT_DIR + r'/data/flurstueck.zip', encoding='utf-8')

        flur_data = flur_data.to_crs(4326)  # convert to a EPSG4326 coordinate system
        flur_layer = folium.FeatureGroup(name="flur")

        for geometry, gemarkung, flur, flurstnr in flur_data.get(
                ["geometry", "GEMARKUNG", "FLUR", "FLURSTNR"]).itertuples(index=False):
            sim_geo = geopandas.GeoSeries(geometry)
            geo_j = sim_geo.to_json()
            geo_folium = folium.GeoJson(data=geo_j, tooltip="hi", style_function=lambda x: {"fillColor": "#0000ff"})
            folium.Popup(f"{gemarkung}").add_to(geo_folium)
            geo_folium.add_to(flur_layer)

        flur_layer.add_to(self.map)

    def add_railways(self):
        railway_data = geopandas.read_file(
            ROOT_DIR + r'/data/gis_osm_railways_free_1.zip', encoding='utf-8')

        railway_data.to_crs(4326)

        railways_fg_sorted = {}

        for geometry, fclass in railway_data.get(
                ["geometry", "fclass"]).itertuples(index=False):
            # if fclass in railways.keys():
            if fclass not in railways_fg_sorted.keys():
                railways_fg_sorted.update({fclass: folium.FeatureGroup(name=fclass)})

            sim_geo = geopandas.GeoSeries(geometry)
            geo_j = sim_geo.to_json()
            geo_folium = folium.GeoJson(data=geo_j, tooltip=fclass,
                                        style_function=lambda x, y=fclass: {"color": railways[y]})  # railways.get(y)})
            geo_folium.add_to(railways_fg_sorted[fclass])

        for fg in railways_fg_sorted.values():
            fg.add_to(self.map)

    def add_roads(self):
        road_data = geopandas.read_file(
            ROOT_DIR + r'/data/gis_osm_roads_free_1.zip', encoding='utf-8')

        road_data.to_crs(4326)

        road_fg_sorted = {}

        for geometry, fclass in road_data.get(
                ["geometry", "fclass"]).itertuples(index=False):
            if fclass in roads.keys():
                # update keys if fg doesnt exist yet
                if fclass not in road_fg_sorted.keys():
                    road_fg_sorted.update({fclass: folium.FeatureGroup(name=fclass)})

                sim_geo = geopandas.GeoSeries(geometry)
                geo_j = sim_geo.to_json()
                geo_folium = folium.GeoJson(data=geo_j, tooltip=fclass,
                                            style_function=lambda x, y=fclass: {"color": "red"})  # roads.get(y)})
                geo_folium.add_to(road_fg_sorted[fclass])

        for fg in road_fg_sorted.values():
            fg.add_to(self.map)

    def add_transport_stations(self):
        # todo: filter names if they are in other names
        stations_data = geopandas.read_file(
            ROOT_DIR + r'/data/transport_stations.zip', encoding='utf-8')
        stations_marker_cluster = MarkerCluster(name="Transport Stations Marker Cluster")

        stations_data.to_crs(4326)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(stations_data, self.bounds, predicate="within")
        points_within_bounds = remove_exceptions_from_data(points_within_bounds, transport_station_exceptions)
        points_within_bounds = remove_duplicates(points_within_bounds)
        points_within_bounds = remove_redundant(points_within_bounds)

        self.stations_geo_data = points_within_bounds

        # make a heat map layer
        stations_geo = zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass"))
        stations_array = np.array([(point.y, point.x) for point, fclass in stations_geo
                                   if fclass not in transport_station_exceptions])
        heatmap = HeatMap(data=stations_array, name="Heatmap Bus- und Bahnstationen")
        heatmap.add_to(self.map)

        stations_fg = folium.FeatureGroup(name="Bus-, Bahn und Tramstationen")

        for data, name, fclass in zip(points_within_bounds.get("geometry"), points_within_bounds.get("name"),
                                      points_within_bounds.get("fclass")):
            folium.Marker(location=(data.y, data.x), tooltip=fclass, popup=folium.Popup(name)).add_to(
                stations_fg)
            folium.Marker(location=(data.y, data.x), tooltip=fclass).add_to(stations_marker_cluster)

        stations_fg.add_to(self.map)
        stations_marker_cluster.add_to(self.map)
        self.map.keep_in_front(stations_fg)

    def add_test_marker_fg(self):
        with open("templates/station_info_window_test.html", "r") as element:
            html_string = element.read()
            # b = branca.element.Html(data=html_string)
            iframe = branca.element.IFrame(html=html_string, width=200, height=200)
            # iframe = iframe.render(allow_same_origin=True)

            macro = MacroElement()
            macro._template = Template(html_string)

            # template = branca.element.Template(html_string)
            station_info_popup = folium.Popup(iframe)

        test_marker_fg = folium.FeatureGroup(name="test marker")

        test_marker_central_station = folium.Marker((51.5184191, 11.5490143), popup=station_info_popup)
        test_marker_central_station_circle = folium.Circle((51.5184191, 11.5490143), radius=300, color="blue")
        test_marker_central_station.add_to(test_marker_fg)
        test_marker_central_station_circle.add_to(test_marker_fg)

        test_marker_local_station = folium.Marker((51.5282581, 11.5455341), popup=station_info_popup)
        test_marker_local_station_circle = folium.Circle((51.5282581, 11.5455341), radius=300, color="lightblue")
        test_marker_local_station.add_to(test_marker_fg)
        test_marker_local_station_circle.add_to(test_marker_fg)

        test_marker_decentral_station = folium.Marker((51.5116274, 11.5734862), popup=station_info_popup)
        test_marker_decentral_station_circle = folium.Circle((51.5116274, 11.5734862), radius=300, color="cyan")
        test_marker_decentral_station.add_to(test_marker_fg)
        test_marker_decentral_station_circle.add_to(test_marker_fg)

        test_marker_rural_central_station = folium.Marker((51.5129271, 11.5062205), popup=station_info_popup)
        test_marker_rural_central_station_circle = folium.Circle((51.5129271, 11.5062205), radius=300, color="green")
        test_marker_rural_central_station.add_to(test_marker_fg)
        test_marker_rural_central_station_circle.add_to(test_marker_fg)

        test_marker_fg.add_to(self.map)

    def add_login_window(self):
        # todo: create login window
        with open("templates/login.html", "r") as element:
            template = element.read()

        macro = MacroElement()
        macro._template = Template(template)
        self.map.get_root().add_child(macro)

    def get_geo_data_within_stations(self, geo_data_frame):
        drop = []
        geo_data_frame = geo_data_frame.to_crs(32643)
        stations_geo_data = self.stations_geo_data.to_crs(32643)
        for idx_1, geometry_1, fclass_1, name_1 in geo_data_frame.get(["geometry", "fclass", "name"]).itertuples(
                index=True):
            counter = 0
            for idx_2, geometry_2, fclass_2, name_2 in stations_geo_data.get(["geometry", "fclass", "name"]).itertuples(
                    index=True):
                if geometry_1.distance(geometry_2) <= 300:
                    counter += 1

            if counter <= 0:
                drop.append(idx_1)
        geo_data_frame = geo_data_frame.drop(labels=drop, axis=0)
        return geo_data_frame.to_crs(4326)


def get_heat_map(geo_data, bounds, name, exceptions=None, keep_duplicates=False, keep_redundant=False):
    geo_data.to_crs(4326)

    logging.info("Filtering data...")
    # filter points in chosen district
    geo_data = geo_data.drop(['index_right'], axis=1)
    points_within_bounds = geopandas.sjoin(geo_data, bounds, predicate="within")
    points_within_bounds = remove_exceptions_from_data(points_within_bounds, exceptions)
    if not keep_duplicates:
        points_within_bounds = remove_duplicates(points_within_bounds)
    if not keep_redundant:
        points_within_bounds = remove_redundant(points_within_bounds)
    logging.info("Creating heat map layer...")
    # make a heat map layer
    geo_zip = zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass"))

    stations_array = np.array([(point.y, point.x) for point, fclass in geo_zip])

    return HeatMap(data=stations_array, name=name, show=False)


def get_geo_data_within_geo_data(data_1, data_2):
    drop = []
    data_1 = data_1.to_crs(32643)
    data_2 = data_2.to_crs(32643)
    for idx_1, geometry_1, fclass_1, name_1 in data_1.get(["geometry", "fclass", "name"]).itertuples(
            index=True):
        counter = 0
        for idx_2, geometry_2, fclass_2, name_2 in data_2.get(["geometry", "fclass", "name"]).itertuples(
                index=True):
            if geometry_1.distance(geometry_2) <= 300:
                counter += 1

        if counter <= 0:
            drop.append(idx_1)

    data_1 = data_1.drop(labels=drop, axis=0)
    return data_1.to_crs(4326)


# if __name__ == "__main__":
#     fmap = Map()
#     webbrowser.open("templates\\map.html")

if __name__ == "__main__":
    map = folium.Map(location=(51.5074631, 11.4801049), zoom_start=10, min_zoom=4, tiles="OpenStreetMap")
    folium.TileLayer("CartoDB positron").add_to(map)
    folium.TileLayer("CartoDB dark_matter").add_to(map)
    bounds = get_bounds(["Einheitsgemeinde.zip", "Gemeinde.zip", "Verbandsgemeinden.zip"],
                        filter=["Lutherstadt Eisleben", "Hettstedt", "Sangerhausen", "Mansfeld", "Südharz", "Arnstein",
                                "Gerbstedt", "Allstedt", "Mansfelder Grund-Helbra",
                                "Seegebiet Mansfelder Land", "Goldene Aue"])



    logging.info(f"Processing transport data")
    transport_data = geopandas.read_file(
        ROOT_DIR + rf'/data/transport_stations.zip', encoding='utf-8')

    logging.info(f"Processing poi data")
    pois_data = geopandas.read_file(
        ROOT_DIR + rf'/data/pois.zip', encoding='utf-8')

    # reduce the data to mansfeld-südharz only
    lk_bound = get_bounds(["Landkreise_und_kreisfreie_Staedte.zip"], filter=["Mansfeld-Südharz"])
    for lk in lk_bound.values():
        pois_data = geopandas.sjoin(pois_data, lk, predicate="within")
        transport_data = geopandas.sjoin(transport_data, lk, predicate="within")

    pois_data_near_station = get_geo_data_within_geo_data(pois_data, transport_data)

    for name, bound in bounds.items():
        logging.info(f"Processing: {name}")
        for geometry in bound.get(
                ["geometry"]).itertuples(index=False):
            fg = folium.FeatureGroup(name=name)
            sim_geo = geopandas.GeoSeries(geometry)
            geo_j = sim_geo.to_json()
            geo_folium = folium.GeoJson(data=geo_j, zoom_on_click=True,
                                        style_function=lambda x: {"color": "black"}, tooltip=f"{name}: Verwaltungsgrenzen")
            geo_folium.add_to(fg)
            fg.add_to(map)

        logging.info(f"Creating heat maps")
        get_heat_map(transport_data, bounds=bound,
                     exceptions=transport_station_exceptions,
                     name=f"{name}: Heatmap Haltestellen").add_to(map)

        get_heat_map(pois_data, bounds=bound,
                     exceptions=poi_categories.keys(),
                     name=f"{name}: Heatmap Points of Interest", keep_redundant=True, keep_duplicates=True).add_to(map)

        get_heat_map(pois_data_near_station, bounds=bound,
                     exceptions=poi_categories.keys(),
                     name=f"{name}: Heatmap Points of Interest in Haltestellennähe", keep_redundant=True, keep_duplicates=True).add_to(map)

    folium.LayerControl().add_to(map)
    map.save("templates\\map_communal.html")
