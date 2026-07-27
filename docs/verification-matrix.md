# Verification Matrix

Verification Matrix
Use Case: UC-TOKENIZE

    Module Gate: M-BASE
    Scenario Check: SCN-TOKEN (Tokenize "Hello World" -> ["hello", "world"])
    Phase Gate: PHASE-NLP
    Verification Command: python -m pytest tests/test_tokenizer.py -v
    Expected Traces: 
        M-BASE, TOKENIZE

Use Case: UC-STOPWORDS

    Module Gate: M-BASE
    Scenario Check: SCN-STOP (Remove "the" -> [])
    Phase Gate: PHASE-NLP
    Verification Command: python -m pytest tests/test_tokenizer.py -v

Use Case: UC-STEM

    Module Gate: M-STEM
    Scenario Check: SCN-STEM (Stem "running" -> "run")
    Phase Gate: PHASE-NLP
    Verification Command: python -m pytest tests/test_stemmer.py -v

Use Case: UC-SENTIMENT

    Module Gate: M-SENT
    Scenario Check: SCN-SENT (Analyze "good" -> > 0.0)
    Phase Gate: PHASE-NLP
    Verification Command: python -m pytest tests/test_sentiment.py -v

Use Case: UC-PIPELINE

    Module Gate: M-PIPE
    Scenario Check: SCN-PIPE (Process text -> dict)
    Phase Gate: PHASE-NLP
    Verification Command: python -m pytest tests/test_pipeline.py -v

Use Case: UC-CLI

    Module Gate: M-APP
    Scenario Check: SCN-CLI (Run app -> JSON output)
    Phase Gate: PHASE-NLP
    Verification Command: `python -m pytest tests/test_app.py -v