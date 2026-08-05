import os
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import math

app = FastAPI(title="Message Router API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_FILE = "output.csv"
MESSAGES_FILE = "dataset/messages.csv"

@app.get("/api/messages")
def get_messages():
    if not os.path.exists(OUTPUT_FILE) or not os.path.exists(MESSAGES_FILE):
        return {"status": "error", "message": "Data files not found."}
        
    df_out = pd.read_csv(OUTPUT_FILE)
    df_msg = pd.read_csv(MESSAGES_FILE)
    
    # Merge and replace NaN with None for JSON serialization
    df = pd.merge(df_msg, df_out, on="message_id", how="inner")
    df = df.where(pd.notnull(df), None)
    
    records = df.to_dict(orient="records")
    return {"status": "success", "data": records}

@app.get("/api/stats")
def get_stats():
    if not os.path.exists(OUTPUT_FILE):
        return {"status": "error"}
    df_out = pd.read_csv(OUTPUT_FILE)
    counts = df_out["action"].value_counts().to_dict()
    total = len(df_out)
    return {
        "status": "success",
        "stats": {
            "total": total,
            "notify": counts.get("notify", 0),
            "digest": counts.get("digest", 0),
            "mute": counts.get("mute", 0),
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
