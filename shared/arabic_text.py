# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 14:34:51 2026

@author: Samia
"""

import re

def normalize_arabic(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[ًٌٍَُِّْـ]', '', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ؤ', 'و', text)
    text = re.sub(r'ئ', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text