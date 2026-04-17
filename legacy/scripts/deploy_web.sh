#!/bin/bash
# Deployment script for synaptic-inputs-slices dashboard

# Configuration
USER="ymolkov"
HOST="math.gsu.edu"
REMOTE_DIR="synaptic-inputs-slices"
LOCAL_DIR="web"

# Check if lftp is installed
if ! command -v lftp &> /dev/null; then
    echo "Error: lftp is not installed. Please install it using 'brew install lftp' or your package manager."
    exit 1
fi

if [ ! -d "$LOCAL_DIR" ]; then
    echo "Error: Local directory '$LOCAL_DIR' not found. Run 'make dashboard' first."
    exit 1
fi

echo "Deploying $LOCAL_DIR to $USER@$HOST/$REMOTE_DIR..."

# Use lftp to mirror the directory
# -R means reverse mirror (local to remote)
# --delete means delete files on remote that are not on local
# --parallel=10 for faster transfer
# Removing -u and password from command to trigger interactive prompt if not using keys
lftp -e "set sftp:auto-confirm yes; mkdir -p $REMOTE_DIR; cd $REMOTE_DIR; mirror -R --delete --ignore-time --parallel=10 --verbose=3 $LOCAL_DIR .; quit" $USER@$HOST

if [ $? -eq 0 ]; then
    echo "Deployment successful!"
    echo "Dashboard available at: https://math.gsu.edu/~$USER/$REMOTE_DIR/index.html"
else
    echo "Deployment failed."
    exit 1
fi
