from app import app
from app import db
from flask import jsonify, request, abort, make_response
from app.models import User, Issue, Answer
import logging


@app.errorhandler(400)
def custom400(error):
    return make_response(jsonify({"message": error.description}), 400)


@app.errorhandler(404)
def custom404(error):
    return make_response(jsonify({"message": "not found" + error.description}), 404)


@app.route('/')
def root_route():
    return "Hello there"


@app.route('/api/users', methods=["GET"])
def get_user():
    if not request.args:
        abort(400, "invalid request")
    if "user_channel" in request.args:
        user = User.query.filter_by(channel=request.args.get("user_channel")).first()
        if user is not None:
            return jsonify(user.to_dict())
        else:
            abort(404)
    else:
        abort(403)


@app.route('/api/users', methods=['POST'])
def add_user():
    if not request.json or \
            "user_name" not in request.json or \
            "user_channel" not in request.json:
        abort(400, "invalid request")
    if User.query.filter_by(user_name=request.json["user_name"],
                            channel=request.json["user_channel"]).first():
        abort(409, "user already exists")

    if "awaiting_response" not in request.json:
        request.json["awaiting_response"] = False

    db.session.add(User(user_name=request.json["user_name"],
                        channel=request.json["user_channel"],
                        awaiting_response=request.json["awaiting_response"],
                        conversation=None))
    db.session.commit()

    return "created", 201

@app.route('/api/users', methods=['DELETE'])
def delete_user():
    if not request.args:
        abort(400, "invalid request")
    if "user_channel" in request.args:
        user = User.query.filter_by(channel=request.args.get("user_channel")).first()
        if user is not None:
            db.session.delete(user)
            db.session.commit()
            return "deleted", 200
        else:
            abort(404)
    else:
        abort(403)


@app.route('/api/users', methods=['PATCH'])
def update_user():
    if not request.args:
        abort(400, "invalid request")
    if "user_channel" in request.args:
        user = User.query.filter_by(channel=request.args["user_channel"]).first()
        if not user:
            abort(404, "user {} not found".format(request.args.get("user_channel")))
        userdict = user.to_dict()

        userdict.update(request.args)
        user.name = userdict["user_name"]
        user.awaiting_response = userdict["awaiting_response"]

        db.session.add(user)
        db.session.commit()

        return jsonify(userdict), 201
    else:
        abort(400)


@app.route('/api/issues', methods=['GET'])
def get_issue():
    if not request.args:
        abort(400, "invalid request")
    if "id" in request.args:
        issue = Issue.query.get(request.args.get("id"))
        if issue is not None:
            return jsonify(issue.to_dict())
        else:
            abort(404)
    else:
        abort(403)


@app.route('/api/issues', methods=['POST'])
def add_issue():
    if not request.json or \
            "id" not in request.json or \
            "team" not in request.json or \
            "key" not in request.json or \
            "summary" not in request.json or \
            "url" not in request.json:
        abort(400, "invalid request")
    if Issue.query.get(request.json["id"]):
        abort(409, "issue already exists")

    db.session.add(Issue(id=request.json["id"],
                         team=request.json["team"],
                         key=request.json["key"],
                         summary=request.json["summary"],
                         url=request.json["url"]))
    db.session.commit()

    return "created", 201


@app.route('/api/issues', methods=['DELETE'])
def delete_issue():
    if not request.args:
        abort(400, "invalid request")
    if "id" in request.args:
        issue = Issue.query.get(request.args.get("id"))
        if issue is not None:
            db.session.delete(issue)
            db.session.commit()
            return "deleted", 200
        else:
            abort(404)
    else:
        abort(403)


@app.route('/api/answers', methods=['POST'])
def add_answer():
    if not request.json or \
            "team" not in request.json or \
            "value" not in request.json or \
            "user_name" not in request.json or \
            "issue_id" not in request.json:
        abort(400, "invalid request")
    if Answer.query.filter_by(team=request.json["team"],
                              user_name=request.json["user_name"],
                              issue_id=request.json["issue_id"]).first():
        abort(409, "answer already exists")

    db.session.add(Answer(team=request.json["team"],
                          user_name=request.json["user_name"],
                          value=request.json["value"],
                          issue_id=request.json["issue_id"]))
    db.session.commit()

    return "created", 201


@app.route('/api/answers', methods=['GET'])
def get_answer():
    if not request.args:
        abort(400, "invalid request")
    if "team" in request.args:
        answers = Answer.query.filter_by(team=request.args.get("team")).all()
        if answers is None:
            abort(404)
        if request.args.get("show_all") == "True":
            return jsonify([x.to_dict() for x in answers])
        else:
            return jsonify(answers[0].to_dict())
    else:
        abort(403)


@app.route('/api/answers', methods=['DELETE'])
def delete_answer():
    if not request.args:
        abort(400, "invalid request")
    if "team" in request.args and \
            "user_name" in request.args and \
            "issue_id" in request.args:
        answer = Answer.query.filter_by(team=request.args.get("team"),
                                        user_name=request.args.get("user_name"),
                                        issue_id=request.args.get("issue_id"))
        if answer is not None:
            db.session.delete(answer)
            db.session.commit()
            return "deleted", 200
        else:
            abort(404)
    else:
        abort(403)


@app.route("/api/conversations", methods=["POST"])
def add_conversation():
    if not request.json or \
            "user_channel" not in request.json or \
            "unestimated_tasks" not in request.json:
        abort(400, "invalid request")
    user = User.query.filter_by(channel=request.json["user_channel"]).first()
    if not user:
        abort(404, "user {} not found".format(request.json["user_channel"]))
    conversation_list = user.to_dict()["conversation"]
    for task in request.json["unestimated_tasks"]:
        if not Issue.query.get(task["id"]):
            abort(404, "unable to find issue {} ({})".format(task["id"], task["key"]))
        if task["id"] not in conversation_list:
            conversation_list.append(str(task["id"]))
    user.conversation = ",".join(conversation_list)
    db.session.add(user)
    db.session.commit()
    return "created", 201


@app.route('/api/conversations/pop', methods=["GET"])
def pop_conversation():
    if not request.args or \
            "user_channel" not in request.args:
        abort(400, "invalid request")
    user = User.query.filter_by(channel=request.args["user_channel"]).first()
    if not user:
        abort(404, "user {} not found".format(request.args["user_channel"]))
    conversation_list = user.to_dict()["conversation"]
    if not conversation_list:
        abort(404, "user {} has no running conversations".format(request.args.get("user_channel")))
    user.conversation = ",".join(conversation_list[1:])
    db.session.add(user)
    db.session.commit()
    return jsonify(conversation_list[0])


@app.route('/api/slack', methods=['POST'])
def get_slack_response():
    app.logger.error(request.json)
    return "ok", 201
