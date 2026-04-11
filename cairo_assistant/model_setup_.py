# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 01:47:36 2026

@author: Samia
"""

import torch, os
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from huggingface_hub import login, snapshot_download

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
if HF_TOKEN and HF_TOKEN != "your_token":
    login(HF_TOKEN)

FAST_HF_CACHE = os.getenv(
    "NAVITOUR_HF_CACHE",
    os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
)
os.makedirs(FAST_HF_CACHE, exist_ok=True)

def load_models(adapter_path="cairo_assistant/nilechat_cairo_final_v1"):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # -----------------------------
    # Whisper ASR
    # -----------------------------
    whisper_model_id = "AbdelrahmanHassan/whisper-large-v3-egyptian-arabic"
    # Ensure snapshot downloaded to fast cache
    local_whisper_path = snapshot_download(
        repo_id=whisper_model_id,
        cache_dir=FAST_HF_CACHE,
        local_files_only=False,
        #use_auth_token=HF_TOKEN
    )

    whisper_pipe = pipeline(
        task="automatic-speech-recognition",
        model=local_whisper_path,
        chunk_length_s=30,
        device=device,
        model_kwargs={"attn_implementation": "sdpa"},
        #use_auth_token=HF_TOKEN,
    )

    # -----------------------------
    # NileChat 4B
    # -----------------------------
    base_model_id = "MBZUAI-Paris/Nile-Chat-4B"

    # Pre-download model to fast cache
    local_nile_path = snapshot_download(
        repo_id=base_model_id,
        cache_dir=FAST_HF_CACHE,
        local_files_only=False,
        #use_auth_token=HF_TOKEN
    )

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained(local_nile_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Force GPU if available for speed
    device_map = "auto"
    if device == "cuda":
        device_map = {"": 0}  # load full model on GPU if enough memory

    base_model = AutoModelForCausalLM.from_pretrained(
        local_nile_path,
        quantization_config=bnb_config,
        device_map=device_map,
        low_cpu_mem_usage=False,  # load fully into GPU for speed
    )

    # Load PEFT adapter
    if os.path.exists(adapter_path):
        model = PeftModel.from_pretrained(base_model, adapter_path, local_files_only=True)
        model.eval()
    else:
        raise FileNotFoundError(f"{adapter_path} not found.")

    return whisper_pipe, tokenizer, model
