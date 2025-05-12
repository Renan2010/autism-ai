#!/bin/bash

# Add token
ngrok config add-authtoken $NGROK_TOKEN

# Execute Autism AI
python main.py
