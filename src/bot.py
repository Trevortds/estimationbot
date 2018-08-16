import os
from slackclient import SlackClient
import datetime
import sys
import logging
import requests
from time import sleep
import dateutil.parser
from dateutil import tz

import yaml

try:
    with open("api.txt", 'r') as f:
        api_token = f.readline()[:-1]
except FileNotFoundError:
    api_token = os.environ['SLACK_BOT_TOKEN']

if api_token == "":
    print("NO API TOKEN FOUND")
    sys.exit(1)


try:
    with open("config.yml", "r") as yamlfile:
        cfg = yaml.load(yamlfile)
except FileNotFoundError:
    with open("default-config.yml", "r") as yamlfile:
        cfg = yaml.load(yamlfile)

slack_client = SlackClient(api_token)
start_time = datetime.datetime.now()
jira_user = os.environ["JIRA_UNAME"] # TODO use oauth
jira_pass = os.environ["JIRA_PWORD"]

awaiting_response = set()

conversations = {}

answers = {}

channel_to_name = {}


def set_up_logging(log_file_name=None):
    _logger = logging.getLogger('')
    _logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    _logger.addHandler(ch)
    if log_file_name:
        fh = logging.FileHandler(log_file_name)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(process)d %(thread)d %(module)s::%('
                                          'funcName)s[%(lineno)d] - %(message)s'))
        _logger.addHandler(fh)
    logging.getLogger('elasticsearch').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return _logger


def send_message(channel, message, attachments=None):
    # if channel not in channel_codes.keys():
    #     print("channel doesn't exist, please pick from one of these")
    #     for key in channel_codes.keys():
    #         print(key)


    # use this instead
    # curl -X POST -H 'Content-type: application/json' --data '{"text":"Hello, World!"}' https://hooks.slack.com/services/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
    # in final deployment, swap the url for one achieved this way https://api.slack.com/incoming-webhooks# (scroll down to "generating programmatically")
    slack_client.api_call("chat.postMessage",
                          channel=channel, text=message, as_user=True, attachments=attachments)


def get_unestimated_tasks(team: str, max=10):
    response = requests.get(cfg["base_url"]+"/rest/api/2/search",
                            params={"maxResults": max, "jql": cfg["teams"][team]["jql_search_query"]},
                            auth=requests.auth.HTTPBasicAuth(jira_user, jira_pass))
    todo_list = response.json()["issues"]
    output = []
    for issue in todo_list:
        output.append((issue["id"],
                       team,
                       issue["key"],
                       issue["fields"]["summary"],
                       cfg["base_url"]+"/browse/"+issue["key"]))
    return output


def start_conversation(channel, unestimated_tasks):
    logging.debug("starting conversation in channel {}".format(channel))
    if channel in conversations and conversations[channel]["tasks"] != []:
        conversations[channel]["tasks"] += unestimated_tasks
    else:
        conversations[channel] = {}
        conversations[channel]["tasks"] = unestimated_tasks
    send_message(channel, cfg["start_message"])
    send_message(channel, "\n".join(conversations[channel]["tasks"][0][2:]))
    awaiting_response.add(channel)


def start_estimations(team: str):
    unestimated_tasks = get_unestimated_tasks(team)
    for email in cfg["teams"][team]["users_to_notify"]:
        user_list = slack_client.api_call("users.list")["members"] # use this to get users.
        user = [user for user in user_list if user["profile"].get("email", "") == email][0] # use this to get id
        user_channel = slack_client.api_call("im.open", user=user["id"])["channel"]["id"] # use this to get dm channel

        start_conversation(user_channel, unestimated_tasks)
        channel_to_name[user_channel] = user["profile"]["display_name"]
    answers[team] = {}


def end_conversation(user_channel, team):
    awaiting_response.remove(user_channel)
    remove_list = []
    for issue in conversations[user_channel]["tasks"]:
        if issue[1] == team:
            remove_list.append(issue)
            logging.debug("removed {} from queue".format(issue))
    conversations[user_channel]["tasks"] = [e for e in conversations[user_channel]["tasks"] if e not in remove_list]
    logging.debug("remaining queue: {}".format(conversations[user_channel]["tasks"]))
    if remove_list:
        send_message(user_channel, "Out of time for {}".format(team))
        if conversations[user_channel]["tasks"]:
            send_message(user_channel, "Please estimate these:\n"+"\n".join(conversations[user_channel]["tasks"][0][2:]))


def start_meeting(team):
    meeting_channel = [c["id"] for c in slack_client.api_call("channels.list")["channels"]
                       if c["name"] == cfg["teams"][team]["meeting_channel"]][0]
    send_message(meeting_channel,
                 "The results from the estimation poll are ready:\n",
                 [{"fallback": "Show Results",
                   "actions": [
                       {
                           "name": "Action",
                           "type": "button",
                           "text": "See next",
                           "value": "next"
                       }
                   ]
                   }
                 ])
    # TODO implement callback from see next button


def stop_estimations(team: str):
    logging.info("Estimation finished! Results: \n{}".format(answers[team]))
    for email in cfg["teams"][team]["users_to_notify"]:
        user_list = slack_client.api_call("users.list")["members"] # use this to get users.
        user = [user for user in user_list if user["profile"].get("email", "") == email][0] # use this to get id
        user_channel = slack_client.api_call("im.open", user=user["id"])["channel"]["id"] # use this to get dm channel

        end_conversation(user_channel, team)
    start_meeting(team)
    answers[team] = {}


def process_message(message: str, channel):
    if channel not in awaiting_response:
        logging.debug("Got unexpected reply from {} ({})\n{}".format(channel, channel_to_name[channel], awaiting_response))
        return
    issue = conversations[channel]["tasks"][0]
    team = issue[1]
    if message.strip() not in cfg["teams"][team]["allowed_responses"]:
        send_message(channel, "Invalid response, please try again")
        return
    logging.debug("conversation is {}\nissue is {}".format(conversations[channel], issue))
    if issue[0] not in answers[team]:
        answers[team][issue[0]] = {}
    answers[team][issue[0]][channel_to_name[channel]] = message.strip()
    conversations[channel]["tasks"].pop(0)
    if conversations[channel]["tasks"]:
        send_message(channel, "Thanks! next: \n\n"+"\n".join(conversations[channel]["tasks"][0][2:]))
    else:
        send_message(channel, "Good Job! you're done!")
        awaiting_response.remove(channel)


def parse_slack_output(slack_rtm_output):
    '''
    The slack real time messaging API is an events firehose.
    This parsing function returns none unless a message is directed
    at the bot based on its id
    '''
    logging.debug(slack_rtm_output)


    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and output["type"] == "message" and "bot_id" not in output \
                    and 'text' in output \
                    and output['channel'] in awaiting_response:
                # return text after the @ mention, whitespace removed
                logging.debug("Response triggered from {}".format(channel_to_name[output["channel"]]))
                return output['text'].strip().lower(), \
                    output['channel'], output['user']
    return None, None, None

def settings_to_datetime(team_settings: dict):
    output = dateutil.parser.parse(team_settings["day_of_week"])
    if output < datetime.datetime.today():
        output += datetime.timedelta(days=7)
    hour = dateutil.parser.parse(team_settings["time"])
    tzinfo = tz.gettz(team_settings["time_zone"])
    output = output.replace(hour=hour.hour, minute=hour.minute, tzinfo=tzinfo)
    return output

def main():
    set_up_logging()
    READ_WEBSOCKET_DELAY = 1  # second delay between reading from firehose

    start_times = {settings_to_datetime(cfg["teams"][team]["start_time"]): team for team in cfg["teams"]}
    start_times[datetime.datetime.now().replace(microsecond=0)] = "professional-services"

    end_times = {settings_to_datetime(cfg["teams"][team]["end_time"]): team for team in cfg["teams"]}
    end_times[datetime.datetime.now().replace(microsecond=0) + datetime.timedelta(seconds=20)] = "professional-services"
    logging.info("Estimations beginning at {}".format(start_times))

    if slack_client.rtm_connect():
        logging.info("ScrumBot connected and running")
        while True:
            message, channel, user = parse_slack_output(
                slack_client.rtm_read())

            if message and channel:
                process_message(message, channel)

            now = datetime.datetime.now().replace(microsecond=0)
            trigger_team = start_times.get(now)
            if trigger_team:
                start_estimations(trigger_team)


            trigger_team = end_times.get(now)
            if trigger_team:
                stop_estimations(trigger_team)

            # if command and channel:
            #     active.handle_command(command, channel, user)
            # else:
            #     passive.check()
            sleep(READ_WEBSOCKET_DELAY)
    else:
        logging.info("connection failed, invalid slack token or bot id?")
        return False

