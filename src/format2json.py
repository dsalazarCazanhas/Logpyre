import os
import pandas as pd


# Format excel to json
def importSingle2json(doc_loc):
    # Change directory to where the documents are
    os.chdir(doc_loc)
    # Find the file
    with os.scandir(doc_loc) as ficheros:
        ficheros = [fichero.name for fichero in ficheros if fichero.is_file() and fichero.name.endswith('.xlsx')]
    # Get the file
    file = ficheros[0]
    # Read the excel with pandas
    excel_data_df = pd.read_excel(file)
    # Make the convertion
    json_str = excel_data_df.to_json()
    # Delete the file because it is not needed anymore
    os.remove(file)
    return json_str