# TargetHawk Bot

A Telegram bot for tracking cryptocurrency trading signals with user management, referral system, and administrative features.

## Features

- **Signal Tracking**: Track entry prices, targets, and stop-loss levels
- **User Management**: Free, Pro, and VIP tier system with trial periods
- **Referral System**: Earn upgrades through referrals
- **Admin Controls**: Administrative commands for user management and statistics
- **Payment Integration**: Support for Stripe and crypto payments

## Available Commands

### User Commands
- `/start` - Initialize the bot and register with referral support
- `/plans` - View available subscription plans
- `/upgrade` - Access payment options for plan upgrades
- `/refer` - Get your referral link and view referral statistics
- `/status` - Check your current plan and active signals
- `/leaderboard` - View top referrers
- `/track <symbol> <entry_price> <target_price> <stop_loss> [tags]` - Add a new signal
- `/signals` - Manage your tracked signals (list, edit, delete)

### Admin Commands
- `/admin` - Access admin menu (admin only)
- `/structure` - View project file structure and module descriptions

## Project Structure

The bot now supports a `/structure` command which lists all the project files along with their respective roles. This command is intended for internal documentation and developer reference. When invoked, the bot responds with a neatly formatted list of the following files:

- **main.py** - Entry point; sets up the bot and registers command handlers
- **db.py** - Manages database connections and initializes tables
- **bot_commands.py** - Contains shared DB functions, logging, and initialization routines
- **start_commands.py** - Handles the /start command and referral logic
- **user_commands.py** - Provides user commands (plans, upgrade, refer, status, leaderboard)
- **signal_management.py** - Handles signal tracking, editing, and deletion flows
- **admin_commands.py** - Admin-only commands and upgrade/statistics functionality
- **payment.py** - Displays available payment options and plans
- **upgrade.py** - Logs and processes user upgrades
- **referral.py** - Manages referral tracking and related functionality
- **structure.py** - Provides project structure listing
- **README.md** - Basic project documentation

Simply type `/structure` in the chat to view the project structure.

## Setup

1. Set up environment variables:
   - `TELEGRAM_BOT_TOKEN1` - Your Telegram bot token
   - `DATABASE_URL1` - PostgreSQL database connection string
   - `ADMIN_USER_ID` - Admin user ID for administrative commands

2. Install dependencies and run the bot:
   ```bash
   python main.py
   ```

## Database Schema

The bot uses PostgreSQL with the following tables:
- `users` - User information, tiers, and referral data
- `signals` - Trading signal tracking
- `upgrades` - User upgrade history
- `referrals` - Referral relationship tracking
