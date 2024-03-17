# Hugin, the KDR Bot

A Bot to Run Yugioh Roguelike Experiences in Discord.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Special Thanks](#special-thanks)
- [Contributing](#contributing)
- [License](#license)

## Features

TODO.

## Installation

Ensure you have Python 3.8 installed.

You'll also need a MongoDB Database instance. Make sure to configure your MongoDB connection in the `config/config.py` file.

## Usage

Run main.py to initiate the bot.
TODO: Finish rest of Instructions

## Configuration

To configure the project, you'll need to create a `secret_values.py` file manually in the `config` folder. This file should contain the following information:

```python
from discord import Object

# server
SERVER_ID = 0 # replace with the id of your main server to update commands
GUILD = Object(id=SERVER_ID)

TOKEN = "" # your discord bot token goes here

# allowed servers for data manipulation:
SERVER_WHITELIST=[]
```

## Special Thanks

To Mike, whom without this could've never happened, thanks for coaching me and helping me code every step of the way.

To Jacob and Bryant, for designing an incredibly fun format and way to play Yugioh.

To the KingdomsMC Staff team and Community, for giving me endless avenues to express my passion for the card game.
