#!/bin/bash
# Double-click this file to launch CircleFi. Closing this Terminal window stops the app.
cd "$(dirname "$0")"
echo "Starting CircleFi... your browser will open automatically."
echo "" | streamlit run app.py
