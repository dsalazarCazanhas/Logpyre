import pandas as ps
from src.form import Search, Upload
from src.format2json import importSingle2json
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, redirect, render_template, session, url_for
from flask_cors import CORS
from flask_moment import Moment
from flask_bootstrap import Bootstrap
from elasticsearch import Elasticsearch

# Flask server configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Esto es el pass para asegurar las sesiones'
CORS(app)
bootstrap = Bootstrap(app)
moment = Moment(app)

# ElasticSearch engine connection
elastic = Elasticsearch(
    "https://127.0.0.1:9200",
    #ca_certs="../elasticsearch-8.4.1/config/certs/http_ca.crt",
    ssl_assert_fingerprint=("7f4381d7d6802648a0675eb76081e9a0a52f364c68694a43039bb61f04aabee5"),
    basic_auth=("elastic", "fLyIqQvWaOxCblH+ypEe")
)


#Global Vars
doc_loc = app.root_path+"/static/documents/"

# Endpoints
@app.route('/')
def root():
    return redirect('/index')

@app.route('/index', methods=['POST','GET'])
def index():
    search = Search()
    upload = Upload()
    if upload.validate_on_submit():
        # Almacenar el archivo
        f = upload.file_2_json.data
        # usar mismo nombre y extension
        filename = secure_filename(f.filename)
        # guardarlo en la ubicacion adecuada
        f.save(doc_loc+filename)
        # Comienza el cambio de excel a json
        # Se llama al metodo para convertirlo a json
        importing = importSingle2json(doc_loc)
        # Se almacenan las variables en la sesion del usuario para respestar el patron POST/redirect/GET y
        #mantener los resultados en la vista
        session['importing'] = importing
        return redirect(url_for('index'))
    return render_template('index.html',
    current_time=datetime.utcnow(),
    view_search=search, view_upload=upload,
    view_results_hard=session.get('importing'))

# Tratamiento de errores
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html', error="Not found"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html', error="Internal server error"), 500



# Api Elastic
def getIndexSource(index:str, id:int):
    resp = elastic.get(index=index, id=id)
    jsonr = resp['_source']
    return jsonr

def getIndexAll():
    resp = elastic.indices.get(index="*")
    return resp

def searchIndex(index2search):
    resp = elastic.search(index=index2search, query={"match_all": {}})
    for hit in resp['hits']['hits']:
        resource = (hit["_source"])
        read_keys = resource.keys()
        read_values = resource.values()
    return resource, read_keys, read_values

#resp = elastic.search(index="test-index", query={"match_all": {}})
#print("Got %d Hits:" % resp['hits']['total']['value'])
#for hit in resp['hits']['hits']:
#    print("%(timestamp)s %(author)s: %(text)s" % hit["_source"])
