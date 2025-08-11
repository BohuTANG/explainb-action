# ExplainB Action

[![Release](https://img.shields.io/github/v/release/BohuTANG/explainb-action)](https://github.com/BohuTANG/explainb-action/releases)
[![Test](https://github.com/BohuTANG/explainb-action/workflows/Test/badge.svg)](https://github.com/BohuTANG/explainb-action/actions)

GitHub Action for Databend SQL explain plan analysis using TPC-DS benchmark queries.

## Usage

```yaml
- name: Run ExplainB Analysis  
  uses: BohuTANG/explainb-action@v0.1.0
  with:
    bendsql-dsn1: ${{ secrets.DATABEND_DSN_OLD }}
    bendsql-dsn2: ${{ secrets.DATABEND_DSN_NEW }}
```

## Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `bendsql-dsn1` | First Databend DSN | ✅ | - |
| `bendsql-dsn2` | Second Databend DSN | ✅ | - |
| `runbend` | Skip Snowflake comparison | ❌ | `false` |
| `verbose` | Enable verbose logging | ❌ | `false` |
| `output-file` | Report filename | ❌ | `report.html` |
| `query-timeout` | Timeout in seconds | ❌ | `60` |

## DSN Format

Database must be `tpcds_100`:

```
databend://user:password@host:port/tpcds_100
```

## Complete Example

```yaml
name: ExplainB Analysis
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - name: Run ExplainB Analysis
        uses: BohuTANG/explainb-action@v0.1.0
        with:
          bendsql-dsn1: ${{ secrets.DATABEND_DSN_OLD }}
          bendsql-dsn2: ${{ secrets.DATABEND_DSN_NEW }}
          runbend: 'true'
          verbose: 'true'
          
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: explainb-report
          path: report.html
```

## Secrets Setup

Add these secrets in **Settings** → **Secrets and variables** → **Actions**:

- `DATABEND_DSN_OLD`: `databend://username:password@host1:443/tpcds_100`
- `DATABEND_DSN_NEW`: `databend://username:password@host2:443/tpcds_100`

## Output

Generates `report.html` with TPC-DS query explain plan comparisons.

---

Made by [Datafuse Labs](https://datafuselabs.com)