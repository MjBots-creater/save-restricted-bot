# 🔓 Save Restricted Content Bot

Telegram bot that bypasses forwarding restrictions with revenue generation features

## Features
- Forward restricted content to channels
- Personal delivery option
- Force subscription to channels/groups
- Shortener URL verification for revenue
- Owner controls for:
  - Force-sub channels/groups
  - Verification interval
  - Broadcast messages
- MongoDB database
- 24/7 deployment on Render.com

## Setup

### 1. Clone Repository
       
       git clone https://github.com/MjBots-creater/save-restricted-bot.git
       cd save-restricted-bot

### 2. Install Dependencies
       
       pip install -r requirements.txt


### 3. Configure Environment
      Rename .env.sample to .env

     Fill in your credentials:
    
    env
    TELEGRAM_TOKEN=your_bot_token
    MONGO_URI=your_mongodb_uri
    OWNER_ID=your_telegram_id
    WEBHOOK_URL=https://your-app.onrender.com
    SHORTENER_API_URL=https://your-shortener-api.com/api
    SHORTENER_API_KEY=your_api_key
    VERIFICATION_INTERVAL=24



### 4. Run the Bot
      
      python bot.py
