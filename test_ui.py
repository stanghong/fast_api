# %%
import requests
import json

# %%
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np


# Define the API endpoint
#local
url = 'http://127.0.0.1:8000/api/voicebot/'
# docker
# url = 'http://0.0.0.0:8000/api/voicebot/'
# aws
# url = 'http://184.73.60.223:8000/api/voicebot/'
#aws ip with url
# url = 'http://54.226.8.225:8000/api/voicebot/'
# railway url
# url = 'https://fastapi-production-6f0a.up.railway.app/api/voicebot/'

# Function to send a text query
def send_text_query(query: str):
    data = {
        'text': query  # Text is sent as form data
    }
    response = requests.post(url, data=data)
    return response

# Function to send an audio file
def send_audio_file(filepath: str):
    with open(filepath, 'rb') as f:
        files = {'audio': (filepath, f, 'audio/wav')}  # 'audio' matches the UploadFile parameter in FastAPI
        response = requests.post(url, files=files)
    return response

# Set the sample rate and duration
fs = 44100  # Sample rate in Hz
duration = 5  # Duration of recording in seconds
# List available input devices
print(sd.query_devices())
sd.default.reset()
print("Recording...") 

# %%
# need to check the devices from print list make sure the name matches 
sd.default.device = (1, 2) 
# %%
# Record audio
myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
sd.wait()  # Wait until recording is finished

print("Recording complete.")
# %%
# Normalize and convert the recording to 16-bit data
myrecording_int16 = np.int16(myrecording / np.max(np.abs(myrecording)) * 32767)

# Save the recording as a WAV file
write('./data/downloaded_audio.wav', fs, myrecording_int16)

# %%
audio_file_path = "./data/downloaded_audio.wav"
response = send_audio_file(audio_file_path)
print(f"Response status code: {response.status_code}")
print(f"Raw response content: {response.content.decode()}")

if response.status_code == 200:
    try:
        json_data = json.loads(response.text)
        print(f"Response text: {json_data['return_text']}")
    except json.JSONDecodeError:
        print("Failed to parse JSON from response")
    except KeyError:
        print("Key 'return_text' not found in the JSON response")
else:
    print(f"Server returned an error with status code: {response.status_code}")
    print(f"Error details: {response.text}")

# %%
