import os
import pandas as pd


# Formatear excel a json
def importSingle2json(doc_loc):
    # Nos ubicamos en la carpeta documentos
    os.chdir(doc_loc)
    # Se escanea en busca del fichero a convertir
    with os.scandir(doc_loc) as ficheros:
        ficheros = [fichero.name for fichero in ficheros if fichero.is_file() and fichero.name.endswith('.xlsx')]
    # Se escoge el fichero
    file = ficheros[0]
    # Se usa panda para leer el excel
    excel_data_df = pd.read_excel(file)
    # Se convierte a json(tipo dict)
    json_str = excel_data_df.to_json()
    # Se elimina el xlsx luego de la conversion
    os.remove(file)
    # Devolver resultados
    return json_str