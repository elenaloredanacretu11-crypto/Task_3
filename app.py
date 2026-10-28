from pathlib import Path
import csv,json,logging,os
from datetime import datetime,timezone
from flask import Flask,jsonify,send_file,send_from_directory
from pipeline import run_pipeline
ROOT=Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s %(message)s")
app=Flask(__name__)
@app.get("/")
def index(): return send_from_directory(ROOT,"index.html")
@app.get("/health")
def health(): return jsonify({"status":"ok","service":"skyroute-pipeline-demo"}),200
@app.get("/api/summary")
def summary():
    out=ROOT/"output/processed_shipments.csv"; s=ROOT/"output/pipeline_summary.json"
    try:
        if not out.exists() or not s.exists():
            run_pipeline(ROOT/"data/logistics_sample.csv",out,s)
        result=json.loads(s.read_text(encoding="utf-8"))
        result["last_run"]=datetime.fromtimestamp(s.stat().st_mtime,timezone.utc).isoformat()
        return jsonify(result)
    except (OSError, ValueError, csv.Error):
        app.logger.exception("pipeline summary failed")
        return jsonify({"status":"error","message":"Pipeline summary unavailable."}),500
@app.get("/api/records")
def records():
    out=ROOT/"output/processed_shipments.csv"
    try:
        if not out.exists():
            run_pipeline(ROOT/"data/logistics_sample.csv",out,ROOT/"output/pipeline_summary.json")
        with out.open("r",encoding="utf-8",newline="") as file:
            return jsonify({"records":list(csv.DictReader(file))})
    except (OSError, ValueError, csv.Error):
        app.logger.exception("processed records unavailable")
        return jsonify({"status":"error","message":"Processed records unavailable."}),500
@app.get("/api/download-sample")
def download_sample():
    sample=ROOT/"data"/"logistics_sample.csv"
    if not sample.is_file():
        app.logger.error("sample CSV is missing: %s",sample)
        return jsonify({"status":"error","message":"Sample CSV is unavailable."}),404
    return send_file(sample,mimetype="text/csv",as_attachment=True,download_name="skyroute_sample_shipments.csv")
@app.post("/api/run")
def run_now():
    try: return jsonify({"status":"completed","summary":run_pipeline(ROOT/"data/logistics_sample.csv",ROOT/"output/processed_shipments.csv",ROOT/"output/pipeline_summary.json")})
    except (OSError, ValueError, csv.Error):
        app.logger.exception("manual run failed")
        return jsonify({"status":"error","message":"Pipeline execution failed."}),500
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")))
