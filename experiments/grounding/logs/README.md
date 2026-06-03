# Experiment logs

- `sweep.log` - chunk size/overlap/strategy sweep (AUC of recall separation) for word/charngram/phonetic
- `install.log` - background install of lingua-language-detector + semantic/NLI deps (huggingface_hub, transformers, faiss-cpu, sentencepiece)
- `opus.log` - OPUS-MT (mul-en) engine tournament run (exp#3), compared against argos in BENCHMARK.md

Log files themselves are git-ignored (`*.log`); only this README is tracked.
