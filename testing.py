import geopandas
import os
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

places_data = geopandas.read_file(
    ROOT_DIR + r'/data/places.zip', encoding='utf-8')

for data, fclass in zip(places_data.get("geometry"), places_data.get("fclass")):
    print("hi")