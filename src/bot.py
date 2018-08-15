import os
import time
from slackclient import SlackClient
import datetime
import sys
import logging
import requests
from dateutil.parser import parse
from dateutil.tz import gettz
from subprocess import call
import random
import re
import yaml

#
# from lingbot.features.nlprg_schedule_reader import nlprg_meeting
# from lingbot.features import ai
# from lingbot.features import generic_schedule_reader
# from lingbot import passive_feats, active_feats


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


def send_message(channel, message):
    # if channel not in channel_codes.keys():
    #     print("channel doesn't exist, please pick from one of these")
    #     for key in channel_codes.keys():
    #         print(key)


    # use this instead
    # curl -X POST -H 'Content-type: application/json' --data '{"text":"Hello, World!"}' https://hooks.slack.com/services/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
    # in final deployment, swap the url for one achieved this way https://api.slack.com/incoming-webhooks# (scroll down to "generating programmatically")
    slack_client.api_call("chat.postMessage",
                          channel=channel, text=message, as_user=True)

def get_unestimated_tasks(team, max=10):
    response = requests.get(cfg["base_url"]+"/rest/api/2/search",
                            params={"jql":cfg["teams"][team]["jql-search-query"]},
                            auth=requests.auth.HTTPBasicAuth(jira_user, jira_pass))
    logging.info(response.json())
    # TODO return list of tuples (id, name, url) up to max

def start_estimations(team):
    unestimated_tasks = get_unestimated_tasks(team)
    # TODO initialize a conversation with each person on the team
    # Check if we're already awaiting a response for that person, if so, append to the
    # existing conversation

def parse_slack_output(slack_rtm_output):
    '''
    The slack real time messaging API is an events firehose.
    This parsing function returns none unless a message is directed
    at the bot based on its id
    '''
    logging.info(slack_rtm_output)
    user_list = slack_client.api_call("users.list")["members"] # use this to get users.
    trevor = [user["id"] for user in user_list if user["profile"]["display_name"] == "trevor"][0] # use this to get id
    user_channel = slack_client.api_call("im.open", user=trevor)["channel"]["id"] # use this to get dm channel
    send_message(user_channel, "hi, I know who you are")

    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and output['user'] in awaiting_response:
                # return text after the @ mention, whitespace removed
                return output['text'].strip().lower(), \
                    output['channel'], output['user']
    return None, None, None


def main(test = False):
    set_up_logging()
    READ_WEBSOCKET_DELAY = 5  # second delay between reading from firehose
    start_time = datetime.datetime.now()
    logging.info(get_unestimated_tasks("professional-services"))

    if slack_client.rtm_connect():
        logging.info("ScrumBot connected and running")
        while True:
            message, channel, user = parse_slack_output(
                slack_client.rtm_read())

            # TODO If there's a message, parse it and advance that user's conversation


            # TODO check if now is the time to send a message to a team
            # if so, start conversations with that team

            # TODO check if it's now expiration hours past time
            # if so, clear that team's conversations and tell them that they're
            # out of time

            # if command and channel:
            #     active.handle_command(command, channel, user)
            # else:
            #     passive.check()
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        logging.info("connection failed, invalid slack token or bot id?")
        return False

