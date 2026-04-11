---
library_name: peft
license: other
base_model: MBZUAI-Paris/Nile-Chat-4B
tags:
- base_model:adapter:MBZUAI-Paris/Nile-Chat-4B
- llama-factory
- lora
- transformers
pipeline_tag: text-generation
model-index:
- name: nilechat_4b_cairo_model
  results: []
---

<!-- This model card has been generated automatically according to the information the Trainer had access to. You
should probably proofread and complete it, then remove this comment. -->

# nilechat_4b_cairo_model

This model is a fine-tuned version of [MBZUAI-Paris/Nile-Chat-4B](https://huggingface.co/MBZUAI-Paris/Nile-Chat-4B) on the transport_data_train dataset.

## Model description

More information needed

## Intended uses & limitations

More information needed

## Training and evaluation data

More information needed

## Training procedure

### Training hyperparameters

The following hyperparameters were used during training:
- learning_rate: 0.0002
- train_batch_size: 4
- eval_batch_size: 8
- seed: 42
- gradient_accumulation_steps: 2
- total_train_batch_size: 8
- optimizer: Use OptimizerNames.ADAMW_TORCH_FUSED with betas=(0.9,0.999) and epsilon=1e-08 and optimizer_args=No additional optimizer arguments
- lr_scheduler_type: cosine
- lr_scheduler_warmup_steps: 0.1
- num_epochs: 1.0

### Training results



### Framework versions

- PEFT 0.18.1
- Transformers 5.0.0
- Pytorch 2.10.0+cu128
- Datasets 3.2.0
- Tokenizers 0.22.2