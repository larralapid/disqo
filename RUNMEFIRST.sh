#!/bin/bash 

# guide the user through an interactive process to set up their environment

# ask the user if they have registered a new app on spotify
echo "Have you registered a new app on spotify? (y/n)"
read response

# if they have, ask them for their client id and client secret
if [ $response == "y" ]
then
    #!/bin/bash

    # Ask the user for their client ID and secret
    echo "Please enter your client ID:"
    read client_id
    echo "Please enter your client secret:"
    read client_secret
    echo "Please enter your redirect URI:"
    read redirect_uri

    # Write these values to the .env.template file
    echo "clientID=$client_id" > .env.template
    echo "clientSecret=$client_secret" >> .env.template
    echo "redirectURI=$redirect_uri" >> .env.template

    # If there is no existing .env file, copy the template to .env
    if [ ! -f .env ]; then
        cp .env.template .env
    else
        # If there is an existing .env file, update any differing values
        while IFS= read -r line; do
            key=$(echo $line | cut -d '=' -f 1)
            if ! grep -q $key .env; then
                echo $line >> .env
            fi
        done < .env.template
    fi

    # Clear the .env.template file back to its original state
    echo "# spotify api stuff" > .env.template
    echo "clientID=" >> .env.template
    echo "clientSecret=" >> .env.template
    echo "# redirect uri" >> .env.template
    echo "redirectURI=" >> .env.template
else
    # if they haven't, ask them to register a new app on spotify    
    echo "Please register a new app on spotify and then run this script again."
    echo "You can register a new app here: https://developer.spotify.com/dashboard/applications"
    exit 1
fi


#TODO: #1 ask for user_id, username to populate config.py
