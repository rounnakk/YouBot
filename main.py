from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os
import time
import json

class YouTubeAPIBot:
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self.token_path = 'token.pickle'
        
        # Using minimal required scopes
        self.SCOPES = [
            'https://www.googleapis.com/auth/youtube',  # Manage your YouTube account
            'https://www.googleapis.com/auth/youtube.readonly'  # View account info
        ]
        
    def authenticate(self):
        """Handle the OAuth2 flow with minimal scopes"""
        creds = None
        
        if os.path.exists(self.token_path):
            print("Loading saved credentials...")
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing access token...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    if os.path.exists(self.token_path):
                        os.remove(self.token_path)
                    return self.authenticate()
            else:
                print("Starting new OAuth2 flow...")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'client_secrets.json',
                        self.SCOPES,
                        redirect_uri='http://localhost:8080'
                    )
                    
                    print("\nAuthorization Required:")
                    print("1. A browser window will open")
                    print("2. Log in with your Google account")
                    print("3. Accept the minimal permissions required:")
                    print("   - View your YouTube account")
                    print("   - Manage your YouTube account (for chat)")
                    
                    creds = flow.run_local_server(
                        port=8080,
                        prompt='consent',
                        access_type='offline'
                    )
                except Exception as e:
                    print(f"Error during authentication: {e}")
                    return False

            print("Saving credentials for future use...")
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.credentials = creds
        self.youtube = build('youtube', 'v3', credentials=creds)
        return True

    def get_live_chat_id(self, video_id):
        """Get live chat ID using minimal permissions"""
        try:
            request = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=video_id
            )
            response = request.execute()

            if not response['items']:
                raise Exception("Video not found or not a livestream")

            return response['items'][0]['liveStreamingDetails']['activeLiveChatId']
        except Exception as e:
            print(f"Error getting live chat ID: {str(e)}")
            return None

    def get_chat_messages(self, live_chat_id, page_token=None):
        """Get chat messages with minimal scope"""
        try:
            request = self.youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part="snippet,authorDetails",
                pageToken=page_token
            )
            return request.execute()
        except Exception as e:
            print(f"Error getting chat messages: {str(e)}")
            return None

    def send_message(self, live_chat_id, message_text):
        """Send chat message with minimal scope"""
        try:
            request = self.youtube.liveChatMessages().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {
                            "messageText": message_text
                        }
                    }
                }
            )
            return request.execute()
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            return None

    def process_message(self, message):
        """Process messages with basic responses"""
        try:
            author = message['authorDetails']['displayName']
            message_text = message['snippet']['displayMessage'].lower()
            message_type = message['snippet']['type']

            if message_type != 'textMessageEvent':
                return None

            if 'hello' in message_text:
                return f"Hello {author}! 👋"
            elif 'help' in message_text:
                return "Available commands: !help, !about, !time"
            elif '!about' in message_text:
                return "I'm a YouTube chatbot using minimal permissions!"
            elif '!time' in message_text:
                return f"Current time: {time.strftime('%H:%M:%S')}"

            return None

        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return None

    def verify_permissions(self):
        """Verify minimal required permissions"""
        try:
            # Test basic access
            test_response = self.youtube.channels().list(
                part="id",
                mine=True
            ).execute()
            
            print("✓ Successfully verified minimal API access")
            return True
            
        except Exception as e:
            print(f"Permission verification failed: {str(e)}")
            print("\nPlease ensure you have:")
            print("1. Enabled YouTube Data API v3 in Google Cloud Console")
            print("2. Configured OAuth consent screen with minimal scopes:")
            for scope in self.SCOPES:
                print(f"   - {scope}")
            return False

    def run(self, video_id):
        """Main bot loop"""
        print("Starting YouTube chatbot (minimal permissions)...")
        
        if not self.authenticate():
            print("Authentication failed!")
            return
            
        if not self.verify_permissions():
            print("Permission verification failed!")
            return

        live_chat_id = self.get_live_chat_id(video_id)
        if not live_chat_id:
            print("Could not get live chat ID!")
            return

        print(f"Successfully connected to live chat!")
        print(f"Bot is now running! Press Ctrl+C to stop.")

        next_page_token = None
        while True:
            try:
                chat_data = self.get_chat_messages(live_chat_id, next_page_token)
                if not chat_data:
                    continue

                next_page_token = chat_data['nextPageToken']

                for message in chat_data['items']:
                    response = self.process_message(message)
                    if response:
                        self.send_message(live_chat_id, response)

                time_to_sleep = chat_data['pollingIntervalMillis'] / 1000
                time.sleep(time_to_sleep)

            except KeyboardInterrupt:
                print("\nBot stopped by user")
                break
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                time.sleep(5)

if __name__ == "__main__":
    print("YouTube Chat Bot - Minimal Permissions Setup:")
    print("1. Configure OAuth consent screen with these scopes:")
    print("   - https://www.googleapis.com/auth/youtube")
    print("   - https://www.googleapis.com/auth/youtube.readonly")
    print("2. Create OAuth 2.0 credentials")
    print("3. Download and save as client_secrets.json\n")
    
    proceed = input("Ready to proceed? (y/n): ")
    if proceed.lower() != 'y':
        print("Please complete the setup steps and try again.")
        exit()
    
    VIDEO_ID = input("Enter your YouTube livestream video ID: ")
    
    bot = YouTubeAPIBot()
    bot.run(VIDEO_ID)