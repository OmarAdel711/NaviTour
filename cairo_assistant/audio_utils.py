# -*- coding: utf-8 -*-
"""
Created on Thu Feb 26 16:37:09 2026

@author: Samia
"""

from base64 import b64decode
from .assistant_core import ask_cairo_assistant
import os

# Add ffmpeg to PATH for this Python session
os.environ["PATH"] = r"C:\ffmpeg\bin;" + os.environ["PATH"]

def process_audio(audio_data, pipe, tokenizer, model):
    # Save audio
    binary = b64decode(audio_data.split(',')[1])
    with open('input.wav', 'wb') as f:
        f.write(binary)

    # Transcribe
    print("Transcribing your voice...")
    prediction = pipe("input.wav", generate_kwargs={"language": "arabic"})
    transcribed_text = prediction['text']
    print(f"\n[You Said]: {transcribed_text}")

    # Ask chatbot
    print("Generating AI Response...")
    ai_response, is_nav = ask_cairo_assistant(transcribed_text, tokenizer, model)

    print("\n" + "="*40)
    print("Assistant Response:")
    try:
        import json
        json_obj = json.loads(ai_response)
        print(json.dumps(json_obj, indent=4, ensure_ascii=False))
    except:
        print(ai_response)
    print("="*40)
    return ai_response, is_nav
    
    
    
def record_live_audio():
    import sounddevice as sd
    from scipy.io.wavfile import write
    import numpy as np
    from base64 import b64encode

    fs = 16000  # sample rate
    audio_buffer = []

    print("Press ENTER to start recording...")
    input()
    print("Recording... Press ENTER again to stop.")

    def callback(indata, frames, time, status):
        if status:
            print(status)
        audio_buffer.append(indata.copy())

    with sd.InputStream(samplerate=fs, channels=1, callback=callback, dtype='int16'):
        input()  # Stop recording on Enter
        print("Recording stopped!")

    audio_data = np.concatenate(audio_buffer, axis=0)
    write("input_live.wav", fs, audio_data)
    print("Saved to input_live.wav")

    with open("input_live.wav", "rb") as f:
        audio_b64 = "data:audio/wav;base64," + b64encode(f.read()).decode()

    return audio_b64