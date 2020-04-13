from flask import Flask

app = Flask(__name__, static_folder='enu', static_url_path='')

@app.route('/')
def static_files(**kwargs):
    return app.send_static_file('Default.htm')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
