import os
import json
import pandas as pd


# Formatear excel a json recursivo
def importAll2json():
    os.chdir("../Documents")
    files_dir = os.getcwd()
    lista_dir = os.listdir(files_dir)
    for i in lista_dir:
        if os.path.isfile(files_dir + "/" + i):
            file_name, file_extension = os.path.splitext(i)
            if file_extension == ".xlsx":
                print(file_name, "is going to be formated to JSON.")
                excel_data_df = pd.read_excel(i)
                json_str = excel_data_df.to_json()
                to_json = json.loads(json_str)
                return to_json

# Formatear excel a json
def importSingle2json(file):
    if os.path.isfile(file):
        file_name, file_extension = os.path.splitext(file)
        if file_extension == ".xlsx":
            # El fichero se va a formatear a json
            excel_data_df = pd.read_excel(file)
            json_str = excel_data_df.to_json()
            to_json = json.loads(json_str)
            # Se ha convertido de forma satisfactoria
            return to_json