import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import os
import config
import random

class Spot:
    SCOPES = [
        'playlist-read-private', 'playlist-read-collaborative',
        'playlist-modify-private', 'playlist-modify-public',
        'user-follow-modify', 'user-follow-read',
        'user-read-playback-position', 'user-top-read',
        'user-read-recently-played', 'user-library-modify', 'user-library-read',
    ]

    def __init__(self):
        self.inBetaID = config.beta_id
        self.pq_id = config.pq_id
        self.clientID = os.getenv('clientID')
        self.clientSecret = os.getenv('clientSecret')
        self.user_id = config.user_id
        self.username = config.username
        self.redirectURI = os.getenv('redirectURI')

        scope = ' '.join(self.SCOPES)
        token = util.prompt_for_user_token(
            username=self.username,
            scope=scope,
            client_id=self.clientID,
            client_secret=self.clientSecret,
            redirect_uri=self.redirectURI
        )

        # create a Spotify object
        self.sp = spotipy.Spotify(auth=token)

    def get_all_saved_tracks(self):
        offset = 0
        limit = 50
        saved_tracks = []

        while True:
            results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            if results['items']:
                for item in results['items']:
                    saved_tracks.append(item['track']['id'])
                offset += limit
            else:
                break

        return saved_tracks

    def get_liked_songs(self):
        # this gets all liked songs 
        # Use 'me' as the argument for liked songs
        liked_songs_ids = self.get_all_saved_tracks()
        self.liked_count = len(liked_songs_ids)
        print(f"Pre-process Liked Songs: {self.liked_count}")
        self.liked_songs_ids = liked_songs_ids
        
        return liked_songs_ids

    def get_playlist_items(self, playlist_id):

        items = []
        playlist = self.sp.playlist_items(playlist_id)

        while playlist['next']:
            playlist = self.sp.playlist_items(playlist_id, offset=len(items))
            for item in playlist['items']:
                if str(item) == "None" or str(item) == "" or item is None:
                    continue
                else:
                    track = item['track']
                    items.append(track['id'])
        return items

    def delete_tracks(self, playlist_id, tracks):
        while tracks:
            self.sp.playlist_remove_all_occurrences_of_items(playlist_id=playlist_id, items=tracks[:100])
            tracks = tracks[100:]


# TODO: REFACTOR REST OF THIS FILE'S METHODS FROM #3
    def get_in_beta(self):
        in_beta_ids = []
        # get tracks for beta songs 
        in_beta = self.get_playlist_items(self.inBetaID)
        
        #keep getting in beta songs until we have all of them and update the offset parameter
        while in_beta['next']:
            #TODO: check if the item is still valid in spotify
            
            removed_from_beta = 0
            for item in in_beta['items']:
                if str(item) == "None" or str(item) == "" or item == None:
                    # remove the track from the in_beta playlist
                    self.sp.playlist_remove_all_occurrences_of_items(playlist_id=self.inBetaID, items=[item])
                    print("Removed None or empty string from In Beta")
                    removed_from_beta += 1
                else:
                    track = item['track']
                    in_beta_ids.append(track['id'])
        self.in_beta_count = len(in_beta_ids)
        self.in_beta_ids = in_beta_ids
        print(f"In Beta: {self.in_beta_count}") 
        
    def get_queued(self):
        q_ids = []

        # get tracks that exist in the queued playlist 
        q = self.sp.playlist_items(self.pq_id, offset=len(q_ids))

        while q['next']:
            q = self.sp.playlist_items(self.pq_id, offset=len(q_ids))
            for item in q['items']:
                track = item['track']
                q_ids.append(track['id'])
        
        self.q_count = len(q_ids)
        self.q_ids = q_ids

    def get_beta_dupe_liked(self):
        # find saved/liked songs in the beta playlist 
        liked_song_ids = self.liked_songs_ids
        in_beta_ids = self.in_beta_ids
        
        betaDupe_liked = []
        for track_id in in_beta_ids:
            if track_id in liked_song_ids:
                betaDupe_liked.append(track_id)
        self.betaDupe_liked = betaDupe_liked
        print(f"Found {len(betaDupe_liked)} liked songs in beta playlist")

    def get_beta_dupe_q(self):
        # find beta songs in queued playlsit 
        q_ids = self.q_ids
        in_beta_ids = self.in_beta_ids

        betaDupe_q = []
        for track_id in in_beta_ids:
            if track_id in q_ids:
                betaDupe_q.append(track_id)
        print(f"Found {len(betaDupe_q)} beta songs in queued playlist")
        self.betaDupe_q = betaDupe_q

    #  delete tracks returned from get_beta_dupe_liked from beta playlist 
    def delete_betaDupe_likes(self):
        betaDupe_liked = self.betaDupe_liked
        items_to_remove = betaDupe_liked.copy()
        removed_items = []
        print(f"Deleting {len(betaDupe_liked)} liked songs from beta playlist")
        betaDupeCount_liked = 0
        while items_to_remove:
            removed = self.sp.playlist_remove_all_occurrences_of_items(playlist_id=self.inBetaID, items=items_to_remove[:100])
            removed_items.extend(removed['snapshot_id'])
            items_to_remove = items_to_remove[100:]

        
# TODO: refactor this method from #3
    def delete_betaDupe_q(self):
        betaDupe_q = self.betaDupe_q
        items_to_remove = betaDupe_q.copy()
        print(f"Deleting {len(betaDupe_q)} queued songs from beta playlist")
        betaDupeCount_q = 0
        removed_items = []
        while items_to_remove:
            removed = self.sp.playlist_remove_all_occurrences_of_items(playlist_id=self.inBetaID, items=items_to_remove[:100])
            removed_items.extend(removed['snapshot_id'])
            items_to_remove = items_to_remove[100:]

    def exe_deletes(self):
        self.delete_betaDupe_likes()
        print("betadupe likes deleted")
        print("delete betaDupe q")
        self.delete_betaDupe_q()
        print("betadupe q deleted")
        self.get_in_beta()

    def create_queue(self):
        random.shuffle(self.liked_songs_ids)
        self.q_liked_songs = self.liked_songs_ids
        self.q_beta_songs =  random.sample(self.in_beta_ids, len(self.liked_songs_ids)) # for the count of liked_songs, get the same number of items from in_beta_ids after shuffling

        
        new_q = [] #queue playlist subset 

        print(f"generating new queue")

        beta_removals = self.q_beta_songs.copy() # songs to remove from beta playlist after adding to queue
        for item in self.q_liked_songs[:]:
            new_q.append("spotify:track:" + item)
            new_q.append("spotify:track:" + self.q_beta_songs.pop())
        print(f"new subset for queue has {len(new_q)} songs")
        
        print(f"Adding {len(new_q)} songs to queue")
        for item in new_q:
            self.sp.playlist_add_items(playlist_id=self.pq_id, items=[item])

        print("queue updated")

        # delete the beta songs that were added to the queue from the beta playlist
        print(f"Deleting {len(beta_removals)} songs from beta playlist")
        for item in beta_removals:
            self.sp.playlist_remove_all_occurrences_of_items(playlist_id=self.inBetaID, items=[item])
        print("beta playlist updated. New total:" + {self.sp.playlist_items(self.inBetaID)['total']})

    def delete_qDupesFromBeta(self):
        print("collecting in beta songs")
        self.get_in_beta() #TODO: i don't think this is necessary, instead just use self.in_beta_ids
        print("collecting queued songs")
        self.get_queued()
        print("deleting queued songs from beta playlist")
        self.delete_betaDupe_q()

        
    def exe(self):
        self.get_liked_songs()
        self.get_in_beta()
        self.get_queued()
        self.get_beta_dupe_liked()
        self.get_beta_dupe_q()
        self.exe_deletes()
        self.create_queue()
        print("Done")

    def new_playlist(self, name):
        playlist = self.sp.user_playlist_create(self.user_id, name)
        return playlist['id']

    #todo: create a sweep class that will handle the entire process of cleaning up the playlists