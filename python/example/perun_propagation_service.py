import tarfile
import os.path
import datetime


from flask import Flask
from flask import request
from denbi.bielefeld.perun.endpoint import Endpoint
from denbi.bielefeld.perun.keystone import KeyStone
from threading import Thread

app = Flask(__name__)


BASEDIR = '/usr/share/perun/upload/'


@app.route("/upload", methods=['PUT'])
def upload():
    # create unique upload dir
    d = datetime.datetime.today()
    dir = BASEDIR+"/"+str(d.year)+"_"+str(d.month)+"_"+str(d.day)+"-"+str(d.hour)+":"+str(d.minute)+":"+str(d.second)+"."+str(d.microsecond)
    os.mkdir(dir)
    file = dir+"/file.tar.gz"

    # store uploaded data
    f = open(file,'wb')
    f.write(request.get_data())
    f.close()

    # parse propagated data in separate thread
    t = Thread(target=_perun_propagation,args=(file,))
    t.start()

    # return immediately
    return ""




def _perun_propagation(file):
    workdir = os.path.dirname(file)

    # extract tar file
    tar = tarfile.open(file, "r:gz")
    tar.extractall(path=workdir)
    tar.close()

    _print_toFile(workdir+"/keystone.log","start : "+str(datetime.datetime.now()))

    # import into keystone
    keystone = KeyStone(default_role="user",create_default_role=True, support_quotas= False, target_domain_name='elixir')
    endpoint = Endpoint(keystone=keystone,mode="denbi_portal_compute_center",support_quotas=False)
    endpoint.import_data(workdir+'/users.scim',workdir+'/groups.scim')

    _print_toFile(workdir+"/keystone.log","end   : "+str(datetime.datetime.now()),mode='a')

def _print_toFile(file,content,mode='w'):
    f = open(file,mode)
    f.write(content+"\n")
    f.close()



if __name__ == "__main__":
    app.run()