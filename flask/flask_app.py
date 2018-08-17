from flask import Flask

app = Flask(__name__)

@app.route('/')
def root_route():
    return "Hello there"

# TODO Add a database based on this https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database
# TODO move global data from bot into database
# TODO add endpoint to recieve slack data
# TODO add an authentication configuration website


if __name__ == '__main__':
    app.run()