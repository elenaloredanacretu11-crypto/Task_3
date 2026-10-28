import csv
from pipeline import run_pipeline
FIELDS=["order_id","shipment_id","order_date","dispatch_date","delivery_date","region","carrier","status","shipping_cost","weight_kg"]
def row(oid="O1",cost="10",shipment_id="S1"):
 return {"order_id":oid,"shipment_id":shipment_id,"order_date":"2026-01-01","dispatch_date":"2026-01-02","delivery_date":"2026-01-04","region":"North","carrier":"Test","status":"Delivered","shipping_cost":cost,"weight_kg":"2.5"}
def write(p,rs):
 with p.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rs)
def test_valid_transform(tmp_path):
 s=tmp_path/"in.csv";o=tmp_path/"out.csv";write(s,[row()]);r=run_pipeline(s,o)
 assert r["processed_rows"]==1 and r["rejected_rows"]==0
 with o.open(newline="",encoding="utf-8") as f: assert next(csv.DictReader(f))["dispatch_to_delivery_days"]=="2"
def test_invalid_cost_rejected(tmp_path):
 s=tmp_path/"in.csv";o=tmp_path/"out.csv";write(s,[row(cost="-2")]);r=run_pipeline(s,o)
 assert r["processed_rows"]==0 and r["rejected_rows"]==1
def test_duplicate_rejected(tmp_path):
 s=tmp_path/"in.csv";o=tmp_path/"out.csv";write(s,[row(),row()]);r=run_pipeline(s,o)
 assert r["processed_rows"]==1 and r["rejected_rows"]==1
def test_split_shipments_for_one_order_are_allowed(tmp_path):
 s=tmp_path/"in.csv";o=tmp_path/"out.csv";write(s,[row(shipment_id="S1"),row(shipment_id="S2")]);r=run_pipeline(s,o)
 assert r["processed_rows"]==2 and r["rejected_rows"]==0
def test_invalid_date_rejected(tmp_path):
 s=tmp_path/"in.csv";o=tmp_path/"out.csv";invalid=row();invalid["dispatch_date"]="not-a-date";write(s,[invalid]);r=run_pipeline(s,o)
 assert r["processed_rows"]==0 and r["rejected_rows"]==1
