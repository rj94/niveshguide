from google_sheets.sheets_client import load_batch_config, read_batch
from ingestion.normalize import normalize_rows
from ingestion.validate import validate_rows

print("=== StockFilter (live) ===")
raw = read_batch(
    {
        "spreadsheet_id": "1RAX7B2YJfdHrhDbuS4ohUBUwwU7ROsozP8j-zkjUoAM",
        "gid": 1375108259,
        "sheet_name": "StockFilter",
    }
)
print("raw rows including header:", len(raw))
print("headers:", raw[0])
rows = normalize_rows(raw)
valid, invalid = validate_rows(rows)
print("normalized:", len(rows), "valid:", len(valid), "invalid:", len(invalid))
if valid:
    sample = valid[0]
    print(
        "sample:",
        sample.get("symbol"),
        "ltp",
        sample.get("ltp"),
        "ma3",
        sample.get("ma_3"),
        "trend",
        sample.get("trend"),
        "pe",
        sample.get("pe"),
    )

print()
print("=== Six new workbooks ===")
for item in load_batch_config():
    if item["batch_name"] == "STOCKFILTER":
        continue
    sheet_rows = read_batch(item)
    print(f"{item['batch_name']:16} status={item['status']:8} csv_rows={len(sheet_rows)}")
