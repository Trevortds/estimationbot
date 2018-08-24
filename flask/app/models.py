from app import db


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(64), index=True)
    issue_id = db.Column(db.Integer, index=True)
    user_name = db.Column(db.String(64), index=True)
    value = db.Column(db.String(64))

    def __repr__(self):
        return "<{}'s Answer for {} issue {}>".format(self.user_name, self.team, self.issue_id)

    def to_dict(self):
        return {
            "id": self.id,
            "team": self.team,
            "issue_id": self.issue_id,
            "user_name": self.user_name,
            "value": self.value,
        }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(32), index= True, unique=True)
    user_name = db.Column(db.String(64), index=True)
    awaiting_response = db.Column(db.Boolean())
    conversation = db.Column(db.String(1024))  # comma-separated list of issue ids

    def __repr__(self):
        return "<User {}>".format(self.user_name)

    def to_dict(self):
        return {
            "id": self.id,
            "channel": self.channel,
            "user_name": self.user_name,
            "awaiting_response": self.awaiting_response,
            "conversation": self.conversation.split(",") if self.conversation else [],
        }


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(64), index=True)
    key = db.Column(db.String(64), index=True)
    summary = db.Column(db.String(256))
    url = db.Column(db.String(128))

    def __repr__(self):
        return "<{} Issue {}>".format(self.team, self.key)

    def to_dict(self):
        return {
            "id": self.id,
            "team": self.team,
            "key": self.key,
            "summary": self.summary,
            "url": self.url,
        }

# http://flask-sqlalchemy.pocoo.org/2.3/models/#many-to-many-relationships
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database
# http://ondras.zarovi.cz/sql/demo/
