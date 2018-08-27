A self-hosted slack bot for handling asynchronous estimation meetings.

# Setup Instructions

## Prerequisites

A server with a public domain name or static IP. Docker and docker-compose must be installed

A slack workspace

A jira workspace

## Server Installation part 1

Make a directory on the server to be the composition location (data and configs will go here)

Copy `docker-compose-deployment.yml` to this directory and rename it `docker-compose.yml`

Copy `bot/config.yml` to this directory as well.

Make a file called `.env` in the same directory. 

Add a line to `.env` to define `SCRUMBOT_PORT` like the following

```.env
SCRUMBOT_PORT=5000
```

You will be editing this one a lot, so keep it open.


## Slack Setup

From your slack workspace, click the dropdown in the top left (should be a big button that
includes your workspace name and your username). Click "Customize Slack"

On the left bar, click "Configure Apps"

In the top bar, click "Build"

In the top bar, click "Your Apps"

Click "Create New App"

Give your bot a name (the recommendation is "estimationbot"). You can change this later

Select your workspace in the dropdown. 

Under "Add Features or Functionality" click "Permissions"

Scroll down to "Scopes". Estimationbot needs three permissions: 

Conversations: 
Access information about user's public channels (channels:read)
Send messages as estimationbot (chat:write:bot)
Interactivity:
Add a bot user (bot)

In the left bar, click "Bot Users"

Click "Add a Bot User"

Give it a display name and a default username. "estimationbot" 
should be the default, you can change it now or later. 

Click "Save Changes"

In the left bar, click "OAuth and Permissions"

Click "Install App to Workspace", and authorize the app.

You should now see two tokens. Copy the Bot User OAuth Access Token, and add it to .env

It should now read

```
SCRUMBOT_PORT=5000
SLACK_BOT_TOKEN=xoxb-#######-#####-#####
```


Almost done. Now in the left bar, click "Interactive Components". Flip the switch to "on", 
and type in the URL that you will use for the server. If you use the recommended nginx configuration,
you don't need to include a port number. Add /app/slack to the end. For example:

`https://my-domain-name.noip.com/api/slack`


At this point you can test your progress by running `docker-compose up scrumbot_bot`. The slack API should 
connect and output empty lists to the log every second. 

## Jira Setup

Log in to 
https://id.atlassian.com/

Click *API tokens* then *Create API token*. Copy it to your clipboard, and put in `.env` as JIRA_TOKEN, 
along with your jira email



```
SCRUMBOT_PORT=5000
SLACK_BOT_TOKEN=xoxb-#######-#####-#####
JIRA_TOKEN=########
JIRA_UNAME=my-jira-email-address@company.com
```

The basic functionality of the app should now be available! The last step only affects the reporting function.



## Configuration

Now is the best time to make sure your `config.yml` is properly set up.
I hope the naming and comments in config.yml are self-explanatory. Use the what already exists as a template.

The most important things to change at this stage are the team name, users to notify (a list of email addresses 
associated with slack accounts), meeting_channel, and `jql_search_query`. 

I recommend copying the search query of your scrum board
on Jira and adding `AND status = "To  Do" AND type != Epic AND "Story Points" is EMPTY` and changing the 
order by expression to `ORDER BY createdDate ASC`

**Make sure you invite the bot to your meeting channel!** 

### Testing your configuration

You can test your configuration by editing docker-compose.yml and switching the environment variable `TEST` from 
"0" to "1". This will make the estimations for the first team on your list start as soon as you run `docker-compose up`. The estimation meeting 
will begin two minutes later (but it shouldn't throw some kind of error when you press the button unti you finish the next sectio.) 

## Sever Setup Part 2

Install nginx on your server. 

Edit the server config file in /etc/nginx/sites-enabled/

Make or edit a server config block to follow this template:

```
server {

        server_name your.domain.name.com;

        location / {
                add_header 'Access-Control-Allow-Origin' '*';
                add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
                proxy_set_header HOST $host;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_set_header X-Forwarded-Host $host:$server_port;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_pass http://localhost:YOUR_SCRUMBOT_PORT_NUMBER/;
        }

}
```

Then follow this guide to enable SSL: 
https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-16-04

You're done! Run another test with TEST="1" to make sure that the meeting functionality works. 