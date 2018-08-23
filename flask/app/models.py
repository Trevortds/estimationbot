from app import db


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(64), index=True)
    issue_id = db.Column(db.Integer, index=True)
    user_name = db.Column(db.String(64), index=True)

    def __repr__(self):
        return "<{}'s Answer for {} issue {}>".format(self.user_name, self.team, self.issue_id)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(32), index= True, unique=True)
    user_name = db.Column(db.String(64), index=True)
    awaiting_response = db.Column(db.Boolean())
    conversation = db.Column(db.String(1024))  # comma-separated list of issue ids
    def __repr__(self):
        return "<User {}>".format(self.user_name)

class Issues(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(64), index=True)
    key = db.Column(db.String(64), index=True)
    summary = db.Column(db.String(256))
    url = db.Column(db.String(128))

    def __repr__(self):
        return "<{} Issue {}>".format(self.team, self.key)

# http://flask-sqlalchemy.pocoo.org/2.3/models/#many-to-many-relationships
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database
# http://ondras.zarovi.cz/sql/demo/
