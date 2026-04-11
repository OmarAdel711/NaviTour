# -*- coding: utf-8 -*-
"""
Created on Thu Feb 26 16:37:18 2026

@author: Samia
"""

from .model_manager import get_models
from .audio_utils import process_audio, record_live_audio
from raptor.services.raptor_service import run_raptor_from_assistant_json

def main():
    pipe, tokenizer, model = get_models()

    while True:
        audio_b64 = record_live_audio()
        response, is_nav = process_audio(audio_b64, pipe, tokenizer, model)
        
        if is_nav:
            legs_or_error = run_raptor_from_assistant_json(response)
            if isinstance(legs_or_error, dict) and "error" in legs_or_error:
                print("❗", legs_or_error["message"])
                if "suggestions" in legs_or_error:
                    print("💡 Suggestions:", legs_or_error["suggestions"])
            else:
                for leg in legs_or_error:
                    print(leg)
        else:
            print("\n🤖 Assistant:", response)

if __name__ == "__main__":
    main()