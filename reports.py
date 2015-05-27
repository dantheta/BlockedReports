
import sys
import os.path
import glob
import yaml
import urllib
import ConfigParser

import MySQLdb,MySQLdb.cursors


from flask import Flask,request
from flask.ext.mako import MakoTemplates,render_template
import mako.exceptions
app = Flask(__name__)

makotmpl = MakoTemplates(app)

REPORTDATAFILE = os.path.join(
    os.path.dirname(
        os.path.abspath(sys.argv[0])
    ),
    'report_data.yml'
    )

cfg = ConfigParser.ConfigParser()
cfg.read(['db.cfg'])

with open(REPORTDATAFILE) as fp:
    REPORTDATA = yaml.safe_load(fp)

def db_connect(): 
	return MySQLdb.connect(
		cursorclass=MySQLdb.cursors.DictCursor,
		**dict(cfg.items('mysql'))
		)

def run_report(report, **kwargs):
    conn = db_connect()
    c = conn.cursor()
    print report['sql']
    c.execute(report['sql'], kwargs)

    return render_template('results.html', report=report, data=c)

@app.route('/')
def index():

    try:
        return render_template('index.html', report_data=REPORTDATA)
    except Exception,v:
        return mako.exceptions.html_error_template().render()

@app.route('/report/<int:index>')
def report(index):
    if len(REPORTDATA[index].get('fields',[])) == 0:
        # no parameters, just run the report

        return run_report(REPORTDATA[index])

    else:
        return render_template('params.html', report=REPORTDATA[index], index=index)

@app.route('/results/<int:index>', methods=['POST'])
def results(index):

    print REPORTDATA[index]['sql']
    print request.form['url']
    return run_report(REPORTDATA[index], **request.form.to_dict(True))



@app.route('/robots.txt')
def robotstxt():
	return """User-agent: *
Disallow: /"""

app.debug=True
app.run()
