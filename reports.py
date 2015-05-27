
import sys
import os.path
import glob
import math
import yaml
import urllib
import ConfigParser

import MySQLdb,MySQLdb.cursors


from flask import Flask,request
from flask.ext.mako import MakoTemplates,render_template
import mako.exceptions
app = Flask(__name__)
app.config['MAKO_TRANSLATE_EXCEPTIONS'] = False

makotmpl = MakoTemplates(app)

REPORTDATAFILE = os.path.join(
    os.path.dirname(
        os.path.abspath(sys.argv[0])
    ),
    'report_data.yml'
    )

cfg = ConfigParser.ConfigParser()
cfg.read(['db.cfg'])

def make_args(args):
	return urllib.urlencode([(x,v) for (x,v) in args.iteritems() ])

with open(REPORTDATAFILE) as fp:
    REPORTDATA = yaml.safe_load(fp)

def db_connect(): 
	return MySQLdb.connect(
		cursorclass=MySQLdb.cursors.DictCursor,
		**dict(cfg.items('mysql'))
		)

def run_report(report, index, page=1, **kwargs):
    conn = db_connect()
    c = conn.cursor()

    if report['paging']:
        c.execute("select count(*) as ct from ({}) x".format(report['sql']),kwargs)
        row = c.fetchone()
        rowcount = row['ct']
        sql = "{} LIMIT 25 OFFSET {}".format(report['sql'], (page-1)*25)
        pages=int(math.ceil(rowcount / 25.0))
    else:
        sql = report['sql']
        rowcount = c.rowcount
        pages=1

    c.execute(sql, kwargs)

    
    return render_template('results.html', 
        report=report, 
        index=index,
        data=c,
        page=page,
        pages=pages,
        rowcount=rowcount,
        args=make_args(kwargs) or ''
        )

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

        try:
            return run_report(REPORTDATA[index], index)
        except Exception,v:
            return mako.exceptions.html_error_template().render()

    else:
        return render_template('params.html', report=REPORTDATA[index], index=index)

@app.route('/results/<int:index>')
@app.route('/results/<int:index>/<int:page>')
def results(index, page=1):
    print REPORTDATA[index]['sql']
    try:
        return run_report(REPORTDATA[index], index, page, **request.args.to_dict(True))
    except Exception,v:
        return mako.exceptions.html_error_template().render()



@app.route('/robots.txt')
def robotstxt():
	return """User-agent: *
Disallow: /"""

app.debug=True
app.run()
