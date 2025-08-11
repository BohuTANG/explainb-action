# ExplainB Action v0.1.0 🚀

**Release Date**: August 11, 2025

ExplainB Action is a GitHub Action for comparing Databend SQL explain plans between two database instances using TPC-DS benchmark queries.

## 🎯 What's New

### Core Features
- **📊 Explain Plan Comparison**: Compare SQL execution plans between two Databend instances
- **🔍 TPC-DS Benchmarks**: Built-in TPC-DS 100GB scale queries for comprehensive analysis
- **📝 Beautiful Reports**: GitHub-style HTML reports with interactive diff viewer
- **⚡ Fast Analysis**: Efficient query execution with configurable timeouts
- **🛡️ Secure**: No hardcoded credentials, uses GitHub Secrets

### Key Capabilities
- ✅ **Database Version Detection**: Automatically identifies Databend versions
- ✅ **Similarity Scoring**: Calculates explain plan similarity percentages  
- ✅ **Error Handling**: Graceful handling of failed queries and connections
- ✅ **Responsive Design**: Mobile-friendly HTML reports
- ✅ **CI/CD Ready**: Designed for GitHub Actions workflows

## 🚀 Quick Start

```yaml
name: Database Performance Analysis
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - name: Compare Database Versions
        uses: BohuTANG/explainb-action@v0.1.0
        with:
          bendsql-dsn1: ${{ secrets.DATABEND_DSN_OLD }}
          bendsql-dsn2: ${{ secrets.DATABEND_DSN_NEW }}
          runbend: 'true'
          
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: explainb-report
          path: report.html
```

## 📋 Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `bendsql-dsn1` | First Databend DSN | ✅ | - |
| `bendsql-dsn2` | Second Databend DSN | ✅ | - |
| `runbend` | Skip Snowflake comparison | ❌ | `false` |
| `verbose` | Enable verbose logging | ❌ | `false` |
| `output-file` | Report filename | ❌ | `report.html` |
| `query-timeout` | Timeout in seconds | ❌ | `60` |

## 🏗️ Architecture

- **Base**: Original [databendlabs/wizard/explainb](https://github.com/databendlabs/wizard/tree/main/explainb) codebase
- **Runtime**: Docker container with Python 3.11 and BendSQL
- **Queries**: TPC-DS 100GB benchmark queries (10 queries)
- **Output**: Interactive HTML report with diff visualization

## 📊 Sample Output

The action generates detailed reports showing:
- 📈 **Summary Statistics**: Total queries, identical/similar/different counts
- 🔍 **Query Details**: Individual SQL queries with explain plans
- 📊 **Similarity Scores**: Percentage similarity between plans  
- 🎨 **Visual Diffs**: Side-by-side plan comparison with syntax highlighting
- ⚡ **Performance Data**: Execution times and database versions

## 🔒 Security

- Uses GitHub Secrets for database credentials
- No sensitive information in logs or source code
- Environment variable-based configuration
- Comprehensive .gitignore for security

## 🐛 Known Issues

None at this time. Please report issues on [GitHub Issues](https://github.com/BohuTANG/explainb-action/issues).

## 🚦 Next Steps

After installing:
1. Set up your `DATABEND_DSN_OLD` and `DATABEND_DSN_NEW` secrets
2. Ensure both databases have TPC-DS 100GB data loaded in `tpcds_100` database
3. Run your first comparison and review the generated report

---

**Full Changelog**: https://github.com/BohuTANG/explainb-action/blob/main/CHANGELOG.md