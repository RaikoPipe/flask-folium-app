import geopandas
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

flur_data = geopandas.read_file(
    ROOT_DIR + r'/data/flurstueck.zip', encoding='utf-8')

flur_unpack: geopandas.GeoDataFrame = flur_data.get(["geometry", "GEMARKUNG", "FLUR", "FLURSTNR"])

for geometry, e, s,t  in flur_unpack.itertuples(index=False):
    sim_geo = geopandas.GeoSeries(geometry).simplify(tolerance=0.001)
    geo_j = sim_geo.to_json()
