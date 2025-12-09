# Deploying Event Stream to Microsoft Fabric (Custom App)

This guide shows how to configure a Custom App source in Fabric Event Streams, add a KQL Database destination, and configure JSON ingestion mapping so events arrive as typed columns (not nested JSON).

Prerequisites
- Fabric workspace with Contributor permissions
- An Eventhouse and a KQL Database created (e.g., `egx_eventhouse` / `egx_market_data`)
- Access to the Event Streams designer (Real-Time Intelligence experience)

1) Create or open an Event Stream
- In your Fabric workspace, switch to **Real-Time Intelligence**.
- Click **New** → **Eventstream** and give it a friendly name (e.g., `egx_stream`).

2) Add a Custom App source
- In the Event Stream canvas, click **+ Add source** → **Custom App**.
- Give it a name (e.g., `egx_producer_app`).
- Copy the **Connection details**: you'll get an Event Hub-compatible connection string and an event hub name. Use that in `fabric/eventstream/config.json` or as env vars `FABRIC_EVENTHUB_CONNECTION_STRING` and `FABRIC_EVENTHUB_NAME` for the producer.
- Set Data format to **JSON**.

3) Configure source parsing preview
- Use the sample JSON produced by `fabric/eventstream/producer.py` (run `python producer.py --once --config config.json` locally to preview messages) to inspect fields.
- Ensure the JSON has top-level fields: `symbol, exchange, interval, timestamp, open, high, low, close, volume, ingestion_time`.

4) Add a KQL Database destination
- Click **New destination** → **KQL Database**.
- Select workspace, then the KQL database (e.g., `egx_market_data`).
- Enter the target table name: `MarketData`.
- Select **JSON** as the data format.
- Click **Add and configure** to open the ingestion wizard.

5) Configure ingestion mapping
- On the **Schema** step, choose **JSON mapping** and create a mapping named `MarketDataMapping`.
- Map JSON paths to columns (example mapping):
  - `$.symbol` -> `symbol` (string)
  - `$.exchange` -> `exchange` (string)
  - `$.interval` -> `interval` (string)
  - `$.timestamp` -> `timestamp` (datetime)
  - `$.open` -> `open` (real)
  - `$.high` -> `high` (real)
  - `$.low` -> `low` (real)
  - `$.close` -> `close` (real)
  - `$.volume` -> `volume` (long)
  - `$.ingestion_time` -> `ingestion_time` (datetime)

6) Validate end-to-end flow
- Start the `producer.py` locally in single-run mode to send a sample batch:

```bash
cd fabric/eventstream
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python producer.py --config config.json --once
```

- In Fabric Event Stream canvas use **View live** to confirm events arriving.
- In KQL Database, run `MarketData | top 50 by ingestion_time desc` to validate typed columns (not nested JSON).

7) Production notes
- Use connection string authentication for custom apps. For higher security, register a managed identity or service principal and use Azure AD authentication where supported.
- Choose an appropriate Fabric capacity (F4 recommended) for production streaming workloads.
- Use partition key = `symbol` to preserve ordering per symbol.

If anything is unclear or you want, I can generate an ARM/Bicep snippet or a Fabric CLI/REST automation script to provision these resources programmatically.