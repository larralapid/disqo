#!/bin/bash 

# guide the user through an interactive process to set up their environment

# ask the user if they have registered a new app on spotify
echo "Have you registered a new app on spotify? (y/n)"
read response

# if they have, ask them for their client id and client secret
if [ $response == "y" ]
then
    echo "What is your client id?"
    read client_id
    echo "What is your client secret?"
    read client_secret
    echo "export SPOTIPY_CLIENT_ID=$client_id" >> ~/.bashrc
    echo "export SPOTIPY_CLIENT_SECRET=$client_secret" >> ~/.bashrc
    echo "export SPOTIPY_REDIRECT_URI=http://localhost:8888/callback" >> ~/.bashrc
    source ~/.bashrc
    echo "Your environment variables have been set."
    echo "You can now run the program."
    exit 0
else
    # if they haven't, ask them to register a new app on spotify    
    echo "Please register a new app on spotify and then run this script again."
    echo "You can register a new app here: https://developer.spotify.com/dashboard/applications"
    exit 1
fi


# and then ask them for their client id and client secret
