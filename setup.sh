#!/bin/bash

# Exit immediately if a command exits with a non-zero status
# set -e

# Print a message indicating the start of the setup
echo "Setting up the environment..."

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating a virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
echo "Activating the virtual environment..."
source venv/bin/activate

# Upgrade pip to the latest version
echo "Upgrading pip..."
pip install --upgrade pip

# Install the required packages
echo "Installing required packages..."
pip install -r requirements.txt

# Print a message indicating the setup is complete
echo "Setup complete! You can now run your application."

# Run the application (optional)
# echo "Running the application..."
# python main.py

# Deactivate the virtual environment
# echo "Deactivating the virtual environment..."
# deactivate