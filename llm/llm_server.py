# llm_server.py
# A very small FastAPI server that accepts prompts and returns JSON responses.
# If HF_MODEL_ID is set and transformers can load it, it will attempt to use that model.
# Otherwise it will fallback to a deterministic mock that uses rule-based prioritizer.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, json
from typing import Optional
import uvicorn

app = FastAPI()

class GenRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 256

# Try to import transformers pipeline if available
USE_HF = False
HF_MODEL = os.getenv('HF_MODEL_ID') or os.getenv('HF_MODEL') or ''
try:
    if HF_MODEL:
        from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
        # attempt to initialize -- this may be heavy; user must provide weights locally or have internet.
        tokenizer = AutoTokenizer.from_pretrained(HF_MODEL)
        model = AutoModelForCausalLM.from_pretrained(HF_MODEL)
        gen = pipeline('text-generation', model=model, tokenizer=tokenizer, device_map='auto' if True else None)
        USE_HF = True
except Exception as e:
    print('HF model not available or failed to load:', e)
    USE_HF = False

# Local rule-based fallback logic reused from project
def rule_based_priority_simple(patient_text):
    # Simple heuristic: find numbers for glucose and bp in the prompt
    import re
    g = re.search(r'Glucose\D*(\d+)', patient_text)
    sys = re.search(r'BP\D*(\d+)/(\d+)', patient_text)
    glucose = int(g.group(1)) if g else 0
    sys_val = int(sys.group(1)) if sys else 0
    dia_val = int(sys.group(2)) if sys else 0
    score = 0
    reasons = []
    if glucose >= 400:
        reasons.append(f'Glucose {glucose} >= 400 (hyperglycemic crisis)')
        score += 50
    elif glucose >= 300:
        reasons.append(f'Glucose {glucose} >= 300')
        score += 25
    elif glucose >= 200:
        reasons.append(f'Glucose {glucose} >= 200')
        score += 10
    if sys_val >= 180 or dia_val >= 110:
        reasons.append(f'BP {sys_val}/{dia_val} hypertensive emergency')
        score += 40
    elif sys_val >= 160 or dia_val >= 100:
        reasons.append(f'BP {sys_val}/{dia_val} elevated')
        score += 20
    level = 'Low'
    if score >= 60:
        level = 'Emergency'
    elif score >= 35:
        level = 'High'
    elif score >= 15:
        level = 'Medium'
    return {'priority_level': level, 'score': score, 'reasons': reasons}

@app.post("/generate")
async def generate(req: GenRequest):
    prompt = req.prompt
    # If HF model available, try to generate text and then attempt to parse JSON from it.
    if USE_HF:
        try:
            out = gen(prompt, max_new_tokens=req.max_tokens, do_sample=False)
            text = out[0]['generated_text']
            # Expecting JSON response in text; attempt to extract JSON object
            import re
            m = re.search(r'\{.*\}', text, re.S)
            if m:
                j = json.loads(m.group(0))
                return j
            else:
                # return raw text if no JSON found
                return {'text': text}
        except Exception as e:
            return {'error': str(e), 'note': 'HF generation failed, falling back to rule-based.'}
    else:
        # Fallback: use deterministic rule-based parser on the prompt
        return rule_based_priority_simple(prompt)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)