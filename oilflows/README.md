# Persian Gulf Oil Flow Monitor — v1 starter

This starter implements the first three build steps:

1. download the IMF PortWatch static port registry;
2. resolve a hand-curated list of Persian Gulf / bypass oil terminal names to PortWatch `portid`s;
3. after manual approval, download daily tanker export estimates for those ports plus the Strait of Hormuz tanker series.

It deliberately **does not auto-approve fuzzy matches**. A wrong terminal silently contaminates every downstream result, so terminal resolution is a review gate. The seed list intentionally contains a few **candidates** (for example Yanbu versus King Fahd Port, and mixed-liquids ports) that should not enter the crude series until their PortWatch identity and cargo role are validated.

## Source endpoints

The implementation uses IMF PortWatch's public ArcGIS FeatureServer endpoints:

- Port registry: `PortWatch_ports_database/FeatureServer/0/query`
- Daily port activity: `Daily_Ports_Data/FeatureServer/0/query`
- Daily chokepoints: `Daily_Chokepoints_Data/FeatureServer/0/query`
- Strait of Hormuz: `portid = chokepoint6`

For port activity, `export_tanker` is PortWatch's estimated metric tons loaded onto tanker-class vessels. It is **not yet crude-only**. The terminal whitelist is the first filter; JODI calibration comes later.

## Windows setup

From PowerShell:

```powershell
cd C:\path\to\oilflows_v1_starter
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

## Step 1 — discover PortWatch terminal IDs

```powershell
py -m oilflows.discover_ports
```

This writes:

- `data\raw\portwatch_ports_registry.csv`
- `data\processed\terminal_candidates.csv`

Open `terminal_candidates.csv`. For each seed terminal, inspect the top candidates and set `approved` to `1` for exactly one match when justified.

Do not approve a row merely because its name is similar. Check country, coordinates, tanker activity, industries, LOCODE, and the actual role of the port.

## Step 2 — pull daily histories

```powershell
py -m oilflows.pull_portwatch
```

This writes:

- `data\raw\portwatch_daily_selected_ports.csv`
- `data\raw\portwatch_hormuz_daily.csv`

The default start is `2025-06-22`.

## Step 3 — inspect weekly raw signal

```powershell
py -m oilflows.inspect_raw
```

This writes:

- `data\processed\weekly_terminal_proxy.csv`

We use weekly aggregation initially because daily loading activity is intrinsically lumpy.

## Tests

```powershell
py -m pytest
```

## Next build step

Once the terminal whitelist is validated against real PortWatch results:

1. create the raw SQLite ingestion tables;
2. add JODI monthly crude exports country-by-country;
3. calibrate the daily PortWatch shape to JODI monthly crude totals;
4. add Brent and BNO;
5. build the daily analytical table and 7-day averages.
