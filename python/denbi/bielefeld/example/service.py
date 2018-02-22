from flask import Flask
from flask import request

app = Flask(__name__)


@app.route("/upload", methods=['PUT'])
def upload():
    f = open('/usr/share/perun/upload/file','wb')
    f.write(request.get_data())
    f.close()
    return ""

if __name__ == "__main__":
    app.run()