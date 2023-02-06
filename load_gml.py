import geopandas

file = geopandas.read_file("LoD1_326085758.gml", driver="GML")

print(file)