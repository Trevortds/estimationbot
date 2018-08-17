from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate



app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


from app import routes, models

# TODO Add a database based on this https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database
# TODO move global data from bot into database
# TODO add endpoint to recieve slack data
# TODO add an authentication configuration website