
import sys
import os.path
import csv
import glob
import math
import yaml
import urllib
import datetime
import StringIO
import tempfile
import ConfigParser

import MySQLdb,MySQLdb.cursors


from flask import Flask,request,make_response,send_file
from flask.ext.mako import MakoTemplates,render_template
import mako.exceptions
app = Flask(__name__)
app.config['MAKO_TRANSLATE_EXCEPTIONS'] = False

makotmpl = MakoTemplates(app)

cfg = ConfigParser.ConfigParser()
cfg.read(['db.cfg'])

def make_args(args):
	return urllib.urlencode([(x,v) for (x,v) in args.iteritems() ])

@app.before_request
def read_report_definitions():
    global REPORTDATA
    with open(cfg.get('app','reports')) as fp:
        reportdata = yaml.safe_load(fp)
        REPORTDATA = {x['name']:x for x in reportdata}

def db_connect(): 
	return MySQLdb.connect(
		cursorclass=MySQLdb.cursors.DictCursor,
		**dict(cfg.items('mysql'))
		)

def run_report(report, index, page=1, template=True, **kwargs):
    conn = db_connect()
    c = conn.cursor()

    if report['paging'] and template is True:
        c.execute("select count(*) as ct from ({}) x".format(report['sql']),kwargs)
        row = c.fetchone()
        rowcount = row['ct']
        sql = "{} LIMIT 25 OFFSET {}".format(report['sql'], (page-1)*25)
        pages=int(math.ceil(rowcount / 25.0))
    else:
        sql = report['sql']
        pages=1

    c.execute(sql, kwargs)
    if not report['paging']:
        rowcount = c.rowcount

    if template is False:
        return c
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

@app.route('/report/<index>')
def report(index):
    if len(REPORTDATA[index].get('fields',[])) == 0:
        # no parameters, just run the report

        try:
            return run_report(REPORTDATA[index], index)
        except Exception,v:
            return mako.exceptions.html_error_template().render()

    else:
        return render_template('params.html', report=REPORTDATA[index], index=index)

@app.route('/results/<index>')
@app.route('/results/<index>/<int:page>')
def results(index, page=1):
    print REPORTDATA[index]['sql']
    try:
        return run_report(REPORTDATA[index], index, page, **request.args.to_dict(True))
    except Exception,v:
        return mako.exceptions.html_error_template().render()

@app.route('/results/<index>/download')
def download(index):
    try:
        fp = tempfile.NamedTemporaryFile()
        writer = csv.writer(fp)

        rows = run_report(REPORTDATA[index],index, template=False,**request.args.to_dict(True))
        cols = [ x[0] for x in rows.description ]
        writer.writerow(cols)
        for row in rows:
            writer.writerow([str(row[x] or '') for x in cols])
        fp.seek(0)
        return send_file(fp, mimetype='text/csv', as_attachment=True, 
            attachment_filename='{}_{}.csv'.format(index, datetime.datetime.now()))
    except Exception,v:
        return mako.exceptions.html_error_template().render()


@app.route('/robots.txt')
def robotstxt():
	return """User-agent: *
Disallow: /"""

read_report_definitions()
app.run(host='0.0.0.0')
