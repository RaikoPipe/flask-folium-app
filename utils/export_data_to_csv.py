import os
import geopandas
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def export_to_csv(file_name:str):

    with open(ROOT_DIR + "\\export\\" + file_name.replace(".zip", ".csv"), "w", encoding='utf-8') as f:
        print("reading file...")
        wells_explo = geopandas.read_file(
            ROOT_DIR + "\\import\\" + file_name, encoding='utf-8', rows=1000)

        wells_explo = pd.DataFrame(wells_explo)

        print("exporting data...")
        wells_explo.to_csv(f, index=False, sep=",")

    print("DONE!")

if __name__ == "__main__":
    # traverse root directory, and list directories as dirs and files as files
    for root, dirs, files in os.walk(ROOT_DIR + r'/import'):
        for file in files:
            export_to_csv(file)

