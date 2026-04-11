# -*- coding: utf-8 -*-

import torch, os
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from huggingface_hub import login

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
if HF_TOKEN and HF_TOKEN != "your_token":
    login(HF_TOKEN)

def load_models(adapter_path="nilechat_cairo_final_v1"):
    # Whisper ASR
    whisper_model_id = "AbdelrahmanHassan/whisper-large-v3-egyptian-arabic"
    pipe = pipeline(
        task="automatic-speech-recognition",
        model=whisper_model_id,
        chunk_length_s=30,
        device="cuda" if torch.cuda.is_available() else "cpu",
        model_kwargs={"attn_implementation": "sdpa"},
        #trust_remote_code=True,  
        #download_in_chunks=True, # forces Windows-friendly streaming
        local_files_only=True
    )

    # NileChat
    base_model_id = "MBZUAI-Paris/Nile-Chat-4B"
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained(
        base_model_id,
        # if downloaded
        local_files_only=True
        )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        quantization_config=bnb_config,
        device_map="auto",
        low_cpu_mem_usage=True,
        # if downloaded
        local_files_only=True,  
        #trust_remote_code=True,  # for Nile-Chat
        #download_in_chunks=True  # forces Windows-friendly streaming
    )

    if os.path.exists(adapter_path):
        model = PeftModel.from_pretrained(base_model, adapter_path, local_files_only=True)
        model.eval()
    else:
        raise FileNotFoundError(f"{adapter_path} not found.")

    return pipe, tokenizer, model
