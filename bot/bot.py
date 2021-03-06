import os
from slackclient import SlackClient
from slackclient.server import SlackConnectionError
import datetime
from tzlocal import get_localzone
import sys
import logging
import requests
from time import sleep
import dateutil.parser
from dateutil import tz
import yaml
import client

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
jira_user = os.environ["JIRA_UNAME"]
jira_pass = os.environ["JIRA_TOKEN"]

answers = {}
'''
{
  "team":
    {
      "issue_id":
        {
          "user_name": "answer",
          "user_name2": "answer"
        },
      "issue_id2":
        ...
    }
  "team2": ...
}
'''


def set_up_logging(loglevel):
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)


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
        output.append({"id": issue["id"],
                       "team": team,
                       "key": issue["key"],
                       "summary": issue["fields"]["summary"],
                       "url": cfg["base_url"]+"/browse/"+issue["key"]})
    return output


def start_conversation(channel, unestimated_tasks, end_time: str):
    logging.debug("starting conversation in channel {}".format(channel))
    client.add_conversation(channel, unestimated_tasks)

    send_message(channel, str(cfg["start_message"]) + "\nYou have until " + end_time)
    send_message(channel, "\n".join(client.get_conversation(channel)[0][2:]))
    client.set_awaiting_response(channel, True)


def start_estimations(team: str):
    # client.wipe_answers(team)
    unestimated_tasks = get_unestimated_tasks(team, cfg["teams"][team]["max_per_meeting"])
    user_list = slack_client.api_call("users.list")["members"]  # use this to get users.
    for email in cfg["teams"][team]["users_to_notify"]:
        try:
            user = [user for user in user_list if user["profile"].get("email", "") == email][0] # use this to get id
        except IndexError:
            logging.error("No user in slack for email {}".format(email))
            continue
        user_channel = slack_client.api_call("im.open", user=user["id"])["channel"]["id"] # use this to get dm channel

        client.add_user(user["profile"]["display_name"], user_channel)
        start_conversation(user_channel, unestimated_tasks, cfg["teams"][team]["end_time"]["time"])


def end_conversation(user_channel, team):
    client.set_awaiting_response(user_channel, False)
    remove_list = []
    for issue in client.get_conversation(user_channel):
        if issue[1] == team:
            remove_list.append(issue)
            logging.debug("removed {} from queue".format(issue))
    client.add_conversation(user_channel,
                            [e for e in client.get_conversation(user_channel) if e not in remove_list],
                            reset=True)
    logging.debug("remaining queue: {}".format(client.get_conversation(user_channel)))
    if remove_list:
        send_message(user_channel, "Out of time for {}".format(team))
        if client.get_conversation(user_channel):
            send_message(user_channel, "Please estimate these:\n"+"\n".join(client.get_conversation(user_channel)[0][2:]))
            client.set_awaiting_response(user_channel, True)


def start_meeting(team):
    try:
        meeting_channel = [c["id"] for c in slack_client.api_call("channels.list")["channels"]
                       if c["name"] == cfg["teams"][team]["meeting_channel"]][0]
    except IndexError:
        logging.ERROR("No channel with name {}".format(cfg["teams"][team]["meeting_channel"]))
    send_message(meeting_channel,
                 "The results from the estimation poll are ready:\n",
                 [{"fallback": "Show Results",
                   "callback_id": team,
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

def send_reminder(user_channel, team):
    # this could be made way more efficient if a method could be made for selecting users with open
    #   answers in a particular team
    for issue in client.get_conversation(user_channel):
        if issue[1] == team:
            send_message(user_channel, "Only 1 hour left, please estimate these issues :point_up:")
            break



def send_warnings(team: str):
    logging.info("Sending warning! Results: \n{}".format(client.get_answer(team,
                                                                           show_all=True)))
    user_list = slack_client.api_call("users.list")["members"] # use this to get users.
    for email in cfg["teams"][team]["users_to_notify"]:
        user = [user for user in user_list if user["profile"].get("email", "") == email][0] # use this to get id
        user_channel = slack_client.api_call("im.open", user=user["id"])["channel"]["id"] # use this to get dm channel

        send_reminder(user_channel, team)



def stop_estimations(team: str):
    logging.info("Estimation finished! Results: \n{}".format(client.get_answer(team,
                                                                               show_all=True)))
    user_list = slack_client.api_call("users.list")["members"] # use this to get users.
    for email in cfg["teams"][team]["users_to_notify"]:
        user = [user for user in user_list if user["profile"].get("email", "") == email][0] # use this to get id
        user_channel = slack_client.api_call("im.open", user=user["id"])["channel"]["id"] # use this to get dm channel

        end_conversation(user_channel, team)
    start_meeting(team)


def process_message(message: str, channel):
    if not client.get_awaiting_response(channel):
        logging.debug("Got unexpected reply from {} ({})".format(channel, client.get_user(channel)["user_name"]))
        return
    issue = client.get_conversation(channel)[0]
    team = issue[1]
    if message.strip() not in cfg["teams"][team]["allowed_responses"]:
        send_message(channel, "Invalid response, please try again")
        return
    logging.debug("conversation is {}\nissue is {}".format(client.get_conversation(channel), issue))
    client.add_answer(team, client.get_user(channel)["user_name"], issue[0], message.strip())
    client.pop_conversation(channel)
    if client.get_conversation(channel):
        send_message(channel, "Thanks! next: \n\n"+"\n".join(client.get_conversation(channel)[0][2:]))
    else:
        send_message(channel, "Good Job! you're done!")
        client.set_awaiting_response(channel, False)


def parse_slack_output(slack_rtm_output):
    '''
    The slack real time messaging API is an events firehose.
    This parsing function returns none unless a message is directed
    at the bot based on its id
    '''
    logging.debug(slack_rtm_output)

    if slack_rtm_output and len(slack_rtm_output) > 0:
        for output in slack_rtm_output:
            if output and output["type"] == "message" and "bot_id" not in output \
                    and 'text' in output \
                    and client.get_awaiting_response(output['channel']):
                # return text after the @ mention, whitespace removed
                logging.debug("Response triggered from {}".format(client.get_user(output["channel"])["user_name"]))
                return output['text'].strip().lower(), \
                    output['channel'], output['user']
    return None, None, None

def settings_to_datetime(team_settings: dict):
    output = dateutil.parser.parse(team_settings["day_of_week"])
    hour = dateutil.parser.parse(team_settings["time"])
    tzinfo = tz.gettz(team_settings["time_zone"])
    local_tzinfo = get_localzone()
    output = output.replace(hour=hour.hour, minute=hour.minute, tzinfo=tzinfo)
    if output < datetime.datetime.now(tz=local_tzinfo):
        output += datetime.timedelta(days=7)
    return output

def main():
    set_up_logging(os.environ.get("BOT_LOGLEVEL"))
    READ_WEBSOCKET_DELAY = 1  # second delay between reading from firehose

    while not client.check():
        sleep(1)
        logging.info("waiting for flask to come up")

    start_times = {settings_to_datetime(cfg["teams"][team]["start_time"]): team for team in cfg["teams"]}
    end_times = {settings_to_datetime(cfg["teams"][team]["end_time"]): team for team in cfg["teams"]}
    warn_times = {settings_to_datetime(cfg["teams"][team]["end_time"]) - datetime.timedelta(hours=1): team for team in cfg["teams"]}

    if os.environ.get("TEST") == "1":
        start_times[datetime.datetime.now(tz=get_localzone()).replace(microsecond=0) +
                    datetime.timedelta(seconds=10)] = list(cfg["teams"].keys())[0]
        end_times[datetime.datetime.now(tz=get_localzone()).replace(microsecond=0) +
                  datetime.timedelta(seconds=120)] = list(cfg["teams"].keys())[0]
        warn_times[datetime.datetime.now(tz=get_localzone()).replace(microsecond=0) +
                  datetime.timedelta(seconds=60)] = list(cfg["teams"].keys())[0]

    logging.info("Estimations beginning at {}".format(start_times))

    if slack_client.rtm_connect():
        logging.info("ScrumBot connected and running")
        timeout = 1

        while True:
            try:
                message, channel, user = parse_slack_output(
                                                            slack_client.rtm_read())
            except SlackConnectionError:
                if slack_client.rtm_connect():
                    logging.warning("Slack Connection Error: recovered after {}".format(timeout))
                else:
                    logging.warning("Slack Connection Error: sleeping {} seconds".format(timeout))
                    sleep(timeout)
                    timeout = timeout * 2
                continue
            except requests.ConnectionError:
                if slack_client.rtm_connect():
                    logging.warning("Requests Connection Error: recovered after {}".format(timeout))
                else:
                    logging.warning("Requests Connection Error: sleeping {} seconds".format(timeout))
                    sleep(timeout)
                    timeout = timeout * 2
                continue
            except ConnectionResetError:
                if slack_client.rtm_connect():
                    logging.warning("Connection Reset Error: recovered after {}".format(timeout))
                else:
                    logging.warning("Connection Reset Error: sleeping {} seconds".format(timeout))
                    sleep(timeout)
                    timeout = timeout * 2
                continue
            else:
                timeout = 1

            if message and channel:
                process_message(message, channel)

            now = datetime.datetime.now(tz=get_localzone()).replace(microsecond=0)
            trigger_team = start_times.get(now)
            if trigger_team:
                start_estimations(trigger_team)

            trigger_team = end_times.get(now)
            if trigger_team:
                stop_estimations(trigger_team)
                start_times = {settings_to_datetime(cfg["teams"][team]["start_time"]): team for team in cfg["teams"]}
                end_times = {settings_to_datetime(cfg["teams"][team]["end_time"]): team for team in cfg["teams"]}
                warn_times = {settings_to_datetime(cfg["teams"][team]["end_time"]) - datetime.timedelta(hours=1): team for team in cfg["teams"]}

            trigger_team = warn_times.get(now)
            if trigger_team:
                pass
                send_warnings(trigger_team)
                # warning

            sleep(READ_WEBSOCKET_DELAY)
    else:
        logging.error("connection failed, invalid slack token or bot id?")
        return False

