#!/usr/bin/env python
# Github/Twitter: @zom3y3
# Email: master@zomeye.org
#coding:utf-8
import bottle
from bottle import hook, request, response
import json
import re
import datetime
import urlparse
import os
import posixpath
import urllib
import shutil
import hashlib
import tftpy
import time

with open(os.path.join(os.path.dirname(__file__), 'template.html')) as f:
    page_template = f.read()

with open(os.path.join(os.path.dirname(__file__), 'globe.html')) as f:
    page_globe = f.read()
  
app = bottle.default_app()
app.config.load_config(os.path.join(os.path.dirname(__file__),'tr-064.conf'))

def tr064_check(uri):
    if "/globe" in uri:
        return True
    elif "/UD/act" in uri:
        return True
    else:
        return False
        
def filemd5(file):
    if os.path.exists(file):
        f = open(file, 'rb')
        m = hashlib.md5(f.read())
        md5 = m.hexdigest()
        f.close()
        return md5
            
def retrieve_url(url, filename=None):
    try:
        urllib.URLopener.version = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/1.0.154.53 Safari/525.19'
        filename, _ = urllib.urlretrieve(url, filename)
    except:
        filename = None
    return filename

def download_file(url):
    original = posixpath.split(urlparse.urlsplit(url).path)[-1]
    filename = retrieve_url(url)
    if filename:
        sample_md5 = str((filemd5(filename)))
        destination = os.path.join("sample/", "%s" % sample_md5)
        shutil.move(filename, destination)
        
def tftp_download(host, rfile, lfile):
    try:
        client = tftpy.TftpClient(host, 69)
        client.download(rfile, lfile)
        return True
    except Exception as e:
        return False

#analysis bash script file        
def child_sample_analysis(sample):
    child_sample_list = []
    if os.path.getsize(sample) < (1024*5):
        parent_file = open(sample, 'r')
        for line in parent_file.readlines():
            download_url_match = re.search(r"((http|ftp|https)://)(([a-zA-Z0-9\._-]+\.[a-zA-Z]{2,6})|([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}))(:[0-9]{1,6})*(/[a-zA-Z0-9\&%_\./-~-]*)?", str(line))
            tftp_match = re.search(r"tftp [^;]*", str(line))
            if download_url_match and 'wget' in line:
                download_url = download_url_match.group(0)
                #print download_url
                if ';' in download_url:
                    download_url = download_url.split(';')[0]
                if '|' in download_url:
                    download_url = download_url.split('|')[0]
                child_original = posixpath.split(urlparse.urlsplit(download_url).path)[-1]
                child_filename = retrieve_url(download_url)
                if child_filename:
                    child_sample_md5 = str((filemd5(child_filename)))
                    child_destination = os.path.join("sample/", "%s" % child_sample_md5)
                    child_sample_list.append((download_url,child_sample_md5))
                    shutil.move(child_filename, child_destination)
            if tftp_match:
                tftp_payload = tftp_match.group(0)
                rfile_match = tftp_match = re.search(r"-r [^\s]*", tftp_payload)
                rhost_match = tftp_match = re.search(r"-g [^\s]*", tftp_payload)
                if rfile_match and rhost_match:
                    rfile = rfile_match.group(0).split(' ')[1]
                    rhost = rhost_match.group(0).split(' ')[1]
                    lfile = os.path.join("sample/", "%s" % rfile)
                    if tftp_download(rhost, rfile, lfile):
                        sample_md5 = str((filemd5(lfile)))
                        tftp_url = 'tftp://' + rhost + '/' + rfile
                        child_sample_list.append((tftp_url, sample_md5))
                        newfile = os.path.join("sample/", "%s" % sample_md5)
                        os.rename(lfile, newfile)

        parent_file.close()
        
    return child_sample_list

    
def get_request_record():
    headers = [[name, value,] for name, value in request.headers.items()]
    body_data = request.body.readlines()              
    is_tr064 = tr064_check(request.path)
    payload = "None"
    sample_md5 = ""
    child_sample_md5 = ""
    sample_list = []
    child_sample_list = []
    if is_tr064:
        payload = re.search(r'<NewNTPServer1>(.*)</NewNTPServer1>', str(body_data)) 
        if payload:
            payload = payload.group(1).strip()
            http_match = re.search(r"(?i)(wget|curl).+(http[^ >;\"']+)", payload)
            tftp_match = re.search(r"tftp [^;]*", payload)
            #http download method
            if http_match:
                url = http_match.group(2)
                original = posixpath.split(urlparse.urlsplit(url).path)[-1]
                filename = retrieve_url(url)
                if filename:
                    sample_md5 = str((filemd5(filename)))
                    destination = os.path.join("sample/", "%s" % sample_md5)
                    sample_list.append((url, sample_md5))
                    shutil.move(filename, destination)
                    child_sample_list = child_sample_analysis(destination)

            #tftp download method                        
            elif tftp_match:
                tftp_payload = tftp_match.group(0)
                rfile_match = tftp_match = re.search(r"-r [^\s]*", tftp_payload)
                rhost_match = tftp_match = re.search(r"-g [^\s]*", tftp_payload)
                if rfile_match and rhost_match:
                    rfile = rfile_match.group(0).split(' ')[1]
                    rhost = rhost_match.group(0).split(' ')[1]
                    lfile = os.path.join("sample/", "%s" % rfile)
                    if tftp_download(rhost, rfile, lfile):
                        sample_md5 = str((filemd5(lfile)))
                        tftp_url = 'tftp://' + rhost + '/' + rfile
                        sample_list.append((tftp_url, sample_md5))
                        child_sample_list = child_sample_analysis(lfile)
                        newfile = os.path.join("sample/", "%s" % sample_md5)
                        os.rename(lfile, newfile)

    dest_host = urlparse.urlparse(request.url).netloc.split(':',1)[0]
    return {
        'method': request.method,
        'url': request.url,
        'path': request.path,
        'query_string': request.query_string,
        'headers': headers,
        'body': str(body_data),
        'source_ip': request.environ.get('REMOTE_ADDR'),
        'dest_port': request.environ.get('SERVER_PORT'),
        'dest_host': dest_host,
        'tr-064': is_tr064,
        'sample' : str(sample_list),
        'child_sample': str(child_sample_list),
        'payload' : payload,
        'gmt_create': str(time.strftime("%Y-%m-%d %H:%M:%S %Z"))
    }
                
def log_request(record):
    global hpclient
    req = json.dumps(record)
    log_data = req + "\r\n"
    log = open('tr-064.log','a+')
    log.write(log_data)
    log.close()
    
@app.route('/globe')
def globe():
    response.status = 404
    return page_globe
    
@app.route('/')
@app.route('/<path:re:.+>')
@app.route('/', method="POST")
@app.route('/<path:re:.+>', method="POST")
@hook('after_request')
def func(**kwargs):
    template_config = dict([(name[9:], value) for name, value in app.config.items() if name.startswith("template.")])
    log_request(get_request_record())
    response.set_header('Server', app.config['headers.server'])
    response.set_header('EXT', '')
    return bottle.template(page_template, **template_config)

bottle.run(server='paste', host=app.config['server.host'], port=int(app.config['server.port']))

