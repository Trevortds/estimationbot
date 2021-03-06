import requests
import os
import logging


flask_url = SQLALCHEMY_DATABASE_URI = os.environ.get('FLASK_URL') or \
                                      'http://flaskapp:5000'


def check():
    try:
        response = requests.get(flask_url)
    except (ConnectionError, requests.exceptions.ConnectionError):
        return False
    if response.status_code < 400:
        return True
    else:
        return False


def get_awaiting_response(user_channel):
    response = requests.get(flask_url+"/api/users",
                            params={"user_channel": user_channel})
    if response.status_code != 200:
        logging.debug("asked for response from unknown channel")
        return False
    else:
        return bool(response.json()["awaiting_response"])


def get_user(user_channel):
    response = requests.get(flask_url+"/api/users",
                            params={"user_channel": user_channel})
    if response.status_code != 200:
        raise RuntimeError("API failed to get user info for {}".format(user_channel))
    else:
        return response.json()


def add_user(user_name, user_channel):
    response = requests.post(flask_url+"/api/users",
                             json={"user_name": user_name,
                                   "user_channel": user_channel})
    if response.status_code == 201:
        return True
    if response.status_code == 409:
        return True
    raise RuntimeError("API failed to create user {} {}: {}".format(user_name, user_channel,
                                                                    response.status_code))


def set_awaiting_response(user_channel, value):
    response = requests.patch(flask_url+"/api/users",
                              json={"user_channel": user_channel,
                              "awaiting_response": value})
    if response.status_code != 201:
        raise RuntimeError("API failed to set awaiting response of {}: {}".format(user_channel, response.status_code))
    else:
        return True


def get_issue(issue_id):
    response = requests.get(flask_url+"/api/issues",
                            params={"id": issue_id})
    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError("API failed to find issue with id {}: {}".format(issue_id, response.status_code))


def add_issue(issue_id, team, key, summary, url):
    response = requests.post(flask_url+"/api/issues",
                             json={"id": issue_id,
                                   "team": team,
                                   "key": key,
                                   "summary": summary,
                                   "url": url})
    if response.status_code == 201:
        return True
    elif response.status_code == 409:
        return True
    else:
        raise RuntimeError("API failed to create issue {} {}: {}".format(issue_id, key,
                                                                         response.status_code))


def add_answer(team, user_name, issue_id, value):
    response = requests.post(flask_url+"/api/answers",
                             json={"team": team,
                                   "user_name": user_name,
                                   "issue_id": issue_id,
                                   "value": value})
    if response.status_code == 201:
        return True
    if response.status_code == 409:
        return True
    raise RuntimeError("API failed to create answer {} {} {}: {}".format(team, issue_id, user_name,
                                                                         response.status_code))


def get_answer(team, show_all=False):
    response = requests.get(flask_url+"/api/answers",
                            params={"team": team, "show_all": show_all})
    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError("API failed to find answers for team {}: {}".format(team,
                                                                               response.status_code))


def get_conversation(user_channel):
    """
    iterate through user.conversation (list of issues) and query the issues api
      to make a tuple from each one
      TODO move this loop to the backend, or use some database magic to make it a single call
    :return:
    """
    user = get_user(user_channel)
    return_list = []
    for issue_id in user["conversation"]:
        issue = get_issue(issue_id)
        return_list.append((issue["id"],
                            issue["team"],
                            issue["key"],
                            issue["summary"],
                            issue["url"]))
    return return_list


def add_conversation(user_channel, unestimated_tasks, reset=False):
    """
    add unestimated tasks to issues, add unestimat task ids to user
    :param user_channel:
    :param unestimated_tasks: list of dicts with keys id, team, key, summary, url
    :return:
    """
    for task in unestimated_tasks:
        add_issue(task["id"],
                  task["team"],
                  task["key"],
                  task["summary"],
                  task["url"])
    response = requests.post(flask_url+"/api/conversations",
                             json={"user_channel": user_channel,
                                   "unestimated_tasks": unestimated_tasks,
                                   "reset": reset})
    if response.status_code == 201:
        return True
    else:
        raise RuntimeError("API failed to create conversation {} {}: {}".format(user_channel,
                                                                          unestimated_tasks,
                                                                          response.status_code))


def pop_conversation(user_channel):
    response = requests.get(flask_url+"/api/conversations/pop",
                            params={"user_channel": user_channel})
    if response.status_code == 200:
        return get_issue(response.json())
    else:
        return None


def wipe_answers(team):
    answerlist = get_answer(team, show_all=True)
    for answer in answerlist:
        response = requests.delete(flask_url+"/api/answers",
                                   params={"team": team,
                                           "user_name": answer["user_name"],
                                           "issue_id": answer["issue_id"]})
        if response.status_code != 200:
            raise RuntimeError("API failed to delete answer {} {}: {}".format(answer["user_name"],
                                                                  answer["issue_id"],
                                                                  response.status_code))
    return True

