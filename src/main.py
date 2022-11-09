import pandas as ps
import ssl
import os
#import json
from OpenSSL import crypto
from src.form import Search, Upload
from src.format2json import importSingle2json
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, jsonify, redirect, render_template, session, url_for
from flask_cors import CORS
from flask_moment import Moment
from flask_bootstrap import Bootstrap
from elasticsearch import Elasticsearch




# Elastisearch configs
# Connection: hostname, port
HOSTNAME, PORT='127.0.0.1', 9200
# Certificates for secure connections
cert = ssl.get_server_certificate((HOSTNAME, PORT))
cert_x509 = crypto.load_certificate(crypto.FILETYPE_PEM,cert)
FINGERPRINT = cert_x509.digest("sha256").decode()
# Basic Authentication: User and Pass
USER, PASS='elastic', 'jHYmfqosfJX=mHPFdHF0'


# Flask server configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'This is a string used for secure the connections'
CORS(app)
bootstrap = Bootstrap(app)
moment = Moment(app)


# ElasticSearch engine connection
elastic = Elasticsearch(
    "https://127.0.0.1:9200",
    ssl_assert_fingerprint=FINGERPRINT,
    basic_auth=(USER, PASS)
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
    elastic_db = getIndexAll()
    if search.validate_on_submit():
        result = searchIndex(search)
        session['result']=result
        url_for('index')
    return render_template('index.html',
    current_time=datetime.utcnow(),
    current_data=elastic_db,
    view_search=search)

@app.route('/upload', methods=['GET','POST'])
def upload():
    upload=Upload()
    if upload.validate_on_submit():
        # Saving the file locally
        f = upload.file_2_json.data
        # Same name and extension for compatibility
        filename = secure_filename(f.filename)
        name = os.path.splitext(filename)
        # Correct location doc_loc
        f.save(doc_loc+filename)
        # Excel to Json
        importing = importSingle2json(doc_loc)
        # Ingest data to elastic
        elastic.index(index=name[0], document=importing)
        # Session variable for rendering the view correctly
        return render_template('upload.html',
        current_time=datetime.utcnow(),
        content_json=importing,
        view_upload=upload)
    return render_template('upload.html',
    current_time=datetime.utcnow(),
    view_upload=upload)

# Errors
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html', error="Not found"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html', error="Internal server error"), 500



# Api Elastic
"""def getIndexSource(index:str, id:int):
    resp = elastic.get(index=index, id=id)
    jsonr = resp['_source']
    return jsonr"""

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
