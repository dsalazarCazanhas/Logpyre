from flask import Flask, redirect, render_template
from flask_cors import CORS
from flask_moment import Moment
from elasticsearch import Elasticsearch

# Servidor de Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Esto es el pass para asegurar las sesiones'
CORS(app)
moment = Moment(app)

# Conexion con ElasticSearch
elastic = Elasticsearch(
    "https://127.0.0.1:9200",
    #ca_certs="../elasticsearch-8.4.1/config/certs/http_ca.crt",
    ssl_assert_fingerprint=("7f4381d7d6802648a0675eb76081e9a0a52f364c68694a43039bb61f04aabee5"),
    basic_auth=("elastic", "fLyIqQvWaOxCblH+ypEe")
)

# Endpoints
@app.route('/')
def root():
    return redirect('/index')

@app.route('/index')
def index():
    return redirect('index.html')

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
