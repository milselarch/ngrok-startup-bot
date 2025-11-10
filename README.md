Setup a service to automatically startup ngrok connections, and this 
Telegram bot will tell you what the created ngrok connections are on startup + 
let you read what ngrok connections you have via the `/view_tunnels` command.

This project uses python3.12  

## Setup Instructions

1. Install htop, and install and setup ngrok
2. setup virtual environment
   ```shell
   $ python3.12 -m venv venv
   $ source venv/bin/activate
   ```
3. Create a config.yml file at the project root (use config.example.yml as a template)
4. Install dependencies and do database initialisation
   ```shell
   (venv) $ python -m pip install -r requirements.txt
   ```
5. Run the bot
   ```shell
   (venv) $ python bot.py
   ```
    
To run it as a service, 
create a service file at /etc/systemd/system/ngrok-bot.service
(see `ngrok-tele-bot.service` for reference)  
and activate it using: 

1. `sudo systemctl daemon-reload`
2. `sudo systemctl start ngrok-bot`
3. `sudo systemctl enable ngrok-bot`

