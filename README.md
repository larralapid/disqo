# spotify playlist queuer

I'm really weird about how I discover new music. Most of the time, when I am listening to music, I like to maximize the potential of discovering new music and also not get bored and listen to songs I'm familiar with by creating a queue that alternates known tracks and unknown tracks.

## Components

- [Spotify API](https://developer.spotify.com/documentation/web-api/)
  - A Spotify developer account is required to use the API.
- [Spotipy](https://spotipy.readthedocs.io/en/2.16.1/)
  - A Python library for the Spotify API.
- Properties you'll need to update
  - `username` in `config.py`
  - Playlist IDs
    - Your main queue playlist ID in `config.py`
    - Your listening list playlist ID in `config.py`

## Before Running the Script

- Run the script below in the terminal for authentication

````bash
export SPOTIPY_CLIENT_ID='your-spotify-client-id'
export SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'```
````

- update and save `config.py` with your playlist IDs and username
