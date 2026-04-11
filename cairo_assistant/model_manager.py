# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 02:56:38 2026

@author: Samia
"""

_pipe = None
_tokenizer = None
_model = None


def get_models():
    global _pipe, _tokenizer, _model

    if _model is None:
        print("Loading models for the first time...")
        from .model_setup_ import load_models
        _pipe, _tokenizer, _model = load_models()
        print(" Models loaded and cached.")
    else:
        print(" Using cached models.")

    return _pipe, _tokenizer, _model