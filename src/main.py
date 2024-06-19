import ssl
import os
from OpenSSL import crypto
from form import Search, Upload
from format2json import import_single2json
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import Flask, redirect, render_template, session, url_for
from flask_cors import CORS
from flask_moment import Moment
from flask_bootstrap import Bootstrap
from elasticsearch import Elasticsearch

# Elastisearch configs
# Connection: hostname, port
HOSTNAME, PORT = '127.0.0.1', 9200
# Certificates for secure connections
cert = ssl.get_server_certificate((HOSTNAME, PORT))
cert_x509 = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
FINGERPRINT = cert_x509.digest("sha256").decode()
# Basic Authentication: User and Pass
USER, PASS = 'elastic', 'uvba2R4aeF*WNoXepBuX'

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


# Global Vars
doc_loc = app.root_path + "/static/documents/"


@app.before_request
def redirect_all():
    from flask import request
    allowed_endpoints = ['index', 'upload']
    if request.endpoint not in allowed_endpoints:
        return redirect('/index')

# Endpoints
# @app.route('/', methods=['GET'])
# def root():
#     return redirect('/index')


@app.route('/index', methods=['POST', 'GET'])
def index():
    search = Search()
    elastic_db = get_index_all()
    if search.validate_on_submit():
        result = search_index(search)
        session['result'] = result
        url_for('index')
    return render_template('index.html',
                           current_time=datetime.now(timezone.utc),
                           current_data=elastic_db,
                           view_search=search)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    upload = Upload()
    if upload.validate_on_submit():
        # Saving the file locally
        f = upload.file_2_json.data
        # Same name and extension for compatibility
        filename = secure_filename(f.filename)
        name = os.path.splitext(filename)
        # Correct location doc_loc
        f.save(doc_loc + filename)
        # Excel to Json
        importing = import_single2json(doc_loc)
        # Ingest data to elastic
        elastic.index(index=name[0], document=importing)
        # Session variable for rendering the view correctly
        return render_template('upload.html',
                               current_time=datetime.now(timezone.utc),
                               content_json=importing,
                               view_upload=upload)
    return render_template('upload.html',
                           current_time=datetime.now(timezone.utc),
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


def get_index_all():
    resp = elastic.indices.get(index="*")
    return resp


def search_index(index2search):
    resp = elastic.search(index=index2search, query={"match_all": {}})
    for hit in resp['hits']['hits']:
        resource = (hit["_source"])
        read_keys = resource.keys()
        read_values = resource.values()
    return resource, read_keys, read_values

# resp = elastic.search(index="test-index", query={"match_all": {}})
# print("Got %d Hits:" % resp['hits']['total']['value'])
# for hit in resp['hits']['hits']:
#    print("%(timestamp)s %(author)s: %(text)s" % hit["_source"])


if __name__ == '__main__':
    app.run(debug=True)
