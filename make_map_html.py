import html
import os
import sys
import traceback
import webbrowser

import branca.element
import folium
import numpy as np
from folium.plugins import FastMarkerCluster
from folium.plugins import Fullscreen, HeatMap
from branca.element import Template, MacroElement

import geopandas
import logging

from geopandas import GeoSeries, GeoDataFrame
from shapely.geometry import Point

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

districts = ["Mansfeld-Südharz"]
roads = {"motorway": "red", "trunk": "orange", "primary": "yellow", "secondary": "green", "tertiary": "blue"}
railways = {"rail": "red", "light_rail": "orange", "tram": "blue"}

landuse_exceptions = ("forest", "meadow", "military", "quarry", "orchard", "vineyard", "scrub", "grass", "heath",
                      "farmland", "farmyard", "national_park", "nature_reserve", "allotments")

transport_station_exceptions = ("taxi_rank", "helipad", "apron", "ferry_terminal")

poi_category = {
    # health category
    **dict.fromkeys(["clinic", "hospital"], "health")
}


class Map:
    def __init__(self):
        """create the base map"""

        logging.info("Creating Base Map...")
        # create base map
        self.map = folium.Map(location=(51.5074631, 11.4801049), zoom_start=10, min_zoom=4, tiles="OpenStreetMap",
                              prefer_canvas=True)

        folium.TileLayer("CartoDB positron").add_to(self.map)
        folium.TileLayer("CartoDB dark_matter").add_to(self.map)

        logging.info("Adding layers")
        self.bounds: GeoDataFrame = self.get_district_bounds()
        self.add_railways()
        self.add_roads()
        self.add_landuse_a_fg()
        self.add_test_marker_fg()
        self.add_transport_stations()
        self.add_pois_fg()
        self.add_landkreis()
        # self.add_login_window()

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
        pois_data = geopandas.read_file(
            ROOT_DIR + r'/data/pois.zip', encoding='utf-8')
        pois_data.to_crs(4326)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(pois_data, self.bounds, predicate="within")

        # make a heat map layer
        pois_geo = points_within_bounds.get("geometry")
        pois_array = np.array([(point.y, point.x) for point in pois_geo])
        heatmap = HeatMap(data=pois_array, name="Heatmap POIs")
        heatmap.add_to(self.map)

        pois_fg = folium.FeatureGroup(name="POI")

        for data, fclass in zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass")):
            folium.Circle(location=(data.y, data.x), fill=True, radius=5, tooltip=fclass).add_to(pois_fg)

        pois_fg.add_to(self.map)
        self.map.keep_in_front(pois_fg)

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
            if fclass in railways.keys():
                if fclass not in railways_fg_sorted.keys():
                    railways_fg_sorted.update({fclass: folium.FeatureGroup(name=fclass)})

                sim_geo = geopandas.GeoSeries(geometry)
                geo_j = sim_geo.to_json()
                geo_folium = folium.GeoJson(data=geo_j, tooltip=fclass,
                                            style_function=lambda x, y=fclass: {"color": railways.get(y)})
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
                                            style_function=lambda x, y=fclass: {"color": roads.get(y)})
                geo_folium.add_to(road_fg_sorted[fclass])

        for fg in road_fg_sorted.values():
            fg.add_to(self.map)

    def add_transport_stations(self):
        stations_data = geopandas.read_file(
            ROOT_DIR + r'/data/gis_osm_transport_free_1.zip', encoding='utf-8')

        stations_data.to_crs(4326)

        # filter points in chosen district
        points_within_bounds = geopandas.sjoin(stations_data, self.bounds, predicate="within")

        # make a heat map layer
        stations_geo = zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass"))
        stations_array = np.array([(point.y, point.x) for point, fclass in stations_geo
                                   if fclass not in transport_station_exceptions])
        heatmap = HeatMap(data=stations_array, name="Heatmap Bus- und Bahnstationen")
        heatmap.add_to(self.map)

        stations_fg = folium.FeatureGroup(name="Bus-, Bahn und Tramstationen")

        for data, fclass in zip(points_within_bounds.get("geometry"), points_within_bounds.get("fclass")):
            folium.Circle(location=(data.y, data.x), fill=True, radius=50, tooltip=fclass).add_to(stations_fg)

        stations_fg.add_to(self.map)
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
        test_marker = folium.Marker((51.5074631, 11.4801049), popup=station_info_popup)
        test_marker.add_to(test_marker_fg)

        test_marker_fg.add_to(self.map)

    def add_login_window(self):
        # todo: create login window
        with open("templates/login.html", "r") as element:
            template = element.read()

        macro = MacroElement()
        macro._template = Template(template)
        self.map.get_root().add_child(macro)


if __name__ == "__main__":
    fmap = Map()
    webbrowser.open("templates\\map.html")
