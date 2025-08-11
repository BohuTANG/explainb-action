# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-08-11

### Added
- 🚀 Initial release of ExplainB Action
- 📊 Databend SQL explain plan comparison functionality
- 🔍 TPC-DS 100GB benchmark query analysis (10 predefined queries)
- 📝 Beautiful HTML report generation with GitHub-style diff viewer
- ⚡ Support for two Databend DSN connections comparison
- 🛡️ Secure credential handling via GitHub Secrets
- 🔧 Configurable parameters:
  - `bendsql-dsn1`: First Databend database DSN (required)
  - `bendsql-dsn2`: Second Databend database DSN (required)
  - `runbend`: Skip Snowflake comparison mode (default: false)
  - `verbose`: Enable verbose logging (default: false)
  - `output-file`: Custom report filename (default: report.html)
  - `query-timeout`: Query timeout in seconds (default: 60)
- 📦 Docker-based execution environment
- 🧪 Local testing scripts with security best practices
- 📚 Comprehensive documentation and usage examples

### Features
- **Database Version Detection**: Automatically detects and displays Databend versions
- **Query Execution**: Runs EXPLAIN plans on both database instances
- **Similarity Analysis**: Calculates similarity scores between explain plans
- **Diff Visualization**: GitHub-style side-by-side diff viewer
- **Error Handling**: Graceful handling of connection failures and query errors
- **Report Artifacts**: Generates uploadable HTML reports for CI/CD pipelines

### Technical Details
- Based on original [databendlabs/wizard/explainb](https://github.com/databendlabs/wizard/tree/main/explainb) codebase
- Uses BendSQL for native Databend connectivity
- Written in Python 3.11+ with Docker containerization
- Responsive HTML reports with modern CSS and JavaScript

### Security
- No hardcoded credentials in source code
- Environment variable-based DSN configuration
- GitHub Secrets integration for CI/CD
- Comprehensive .gitignore for sensitive files

### Examples
```yaml
- name: Compare Databend Versions
  uses: datafuselabs/explainb-action@v0.1.0
  with:
    bendsql-dsn1: ${{ secrets.DATABEND_DSN_OLD }}
    bendsql-dsn2: ${{ secrets.DATABEND_DSN_NEW }}
    runbend: 'true'
    verbose: 'true'
```

[0.1.0]: https://github.com/BohuTANG/explainb-action/releases/tag/v0.1.0