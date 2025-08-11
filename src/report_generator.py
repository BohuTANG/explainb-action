#!/usr/bin/env python3
"""
Report Generator for ExplainB Database Comparison Action

This script bridges the GitHub Action's database analysis data with the ExplainB 
HTML report generation system. It takes JSON results from database queries and
generates a comprehensive HTML comparison report.
"""

import argparse
import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Import ExplainB classes
from explainb import ExplainResult, ComparisonResult, HTMLReportGenerator, ExplainComparator

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

class DatabaseComparisonReportGenerator:
    """Generate ExplainB-style reports from database analysis data"""
    
    def __init__(self):
        self.logger = logging.getLogger("ReportGenerator")
    
    def parse_database_results(self, results_file: str) -> List[Dict[str, Any]]:
        """Parse database analysis results from JSON file"""
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to parse {results_file}: {e}")
            return []
    
    def parse_schema_results(self, schema_file: str) -> List[Dict[str, Any]]:
        """Parse schema information from JSON file"""
        try:
            with open(schema_file, 'r') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to parse {schema_file}: {e}")
            return []
    
    def create_database_info_query(self, results: List[Dict[str, Any]]) -> str:
        """Create a synthetic SQL query representing database info analysis"""
        info_items = []
        for item in results:
            category = item.get('category', 'unknown')
            metric = item.get('metric', 'unknown')
            value = item.get('value', 'unknown')
            info_items.append(f"{category}.{metric}: {value}")
        
        if not info_items:
            return "-- Database information query\nSELECT 'No database information available' as info;"
        
        query_parts = [
            "-- Database Information Analysis",
            "SELECT 'database_info' as category, 'current_database' as metric, current_database() as value",
            "UNION ALL",
            "SELECT 'database_info' as category, 'current_user' as metric, current_user() as value", 
            "UNION ALL",
            "SELECT 'database_info' as category, 'version' as metric, version() as value",
            "UNION ALL",
            "SELECT 'tables' as category, 'total_tables' as metric, COUNT(*)::STRING as value",
            "FROM information_schema.tables",
            "WHERE table_schema != 'information_schema'",
            "ORDER BY category, metric;"
        ]
        
        return '\n'.join(query_parts)
    
    def create_schema_analysis_query(self, schemas: List[Dict[str, Any]]) -> str:
        """Create a synthetic SQL query representing schema analysis"""
        if not schemas:
            return "-- Schema analysis query\nSELECT 'No schema information available' as info;"
            
        query_parts = [
            "-- Schema Analysis Query",
            "SELECT",
            "    table_schema,",
            "    table_name,", 
            "    column_name,",
            "    data_type,",
            "    is_nullable",
            "FROM information_schema.columns",
            "WHERE table_schema != 'information_schema'",
            "ORDER BY table_schema, table_name, ordinal_position;"
        ]
        
        return '\n'.join(query_parts)
    
    def create_comparison_results(self, dsn1_results: List[Dict], dsn2_results: List[Dict],
                                dsn1_schemas: List[Dict], dsn2_schemas: List[Dict],
                                dsn1_name: str = "Database 1", dsn2_name: str = "Database 2") -> List[ComparisonResult]:
        """Create comparison results from database analysis data"""
        comparisons = []
        
        # Create database info comparison
        db_query = self.create_database_info_query(dsn1_results)
        dsn1_plan = self.format_database_results(dsn1_results, "Database Information")
        dsn2_plan = self.format_database_results(dsn2_results, "Database Information")
        
        dsn1_result = ExplainResult(
            query_index=1,
            sql_query=db_query,
            success=True,
            explain_plan=dsn1_plan,
            execution_time=0.5,
            engine_name=dsn1_name
        )
        
        dsn2_result = ExplainResult(
            query_index=1,
            sql_query=db_query,
            success=True,
            explain_plan=dsn2_plan,
            execution_time=0.5,
            engine_name=dsn2_name
        )
        
        comparison = ExplainComparator.compare_plans(dsn1_result, dsn2_result)
        comparisons.append(comparison)
        
        # Create schema comparison if schema data exists
        if dsn1_schemas or dsn2_schemas:
            schema_query = self.create_schema_analysis_query(dsn1_schemas)
            dsn1_schema_plan = self.format_schema_results(dsn1_schemas, "Schema Analysis")
            dsn2_schema_plan = self.format_schema_results(dsn2_schemas, "Schema Analysis")
            
            dsn1_schema_result = ExplainResult(
                query_index=2,
                sql_query=schema_query,
                success=True,
                explain_plan=dsn1_schema_plan,
                execution_time=1.0,
                engine_name=dsn1_name
            )
            
            dsn2_schema_result = ExplainResult(
                query_index=2,
                sql_query=schema_query,
                success=True,
                explain_plan=dsn2_schema_plan,
                execution_time=1.0,
                engine_name=dsn2_name
            )
            
            schema_comparison = ExplainComparator.compare_plans(dsn1_schema_result, dsn2_schema_result)
            comparisons.append(schema_comparison)
        
        return comparisons
    
    def format_database_results(self, results: List[Dict], title: str = "Database Analysis") -> str:
        """Format database results into a readable plan format"""
        if not results:
            return f"-- {title}\n-- No data available"
        
        lines = [f"-- {title}", "-- " + "="*50]
        
        # Group results by category
        categories = {}
        for item in results:
            category = item.get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        for category, items in categories.items():
            lines.append(f"-- {category.upper()}")
            for item in items:
                metric = item.get('metric', 'unknown')
                value = item.get('value', 'unknown')
                lines.append(f"--   {metric}: {value}")
            lines.append("--")
        
        return '\n'.join(lines)
    
    def format_schema_results(self, schemas: List[Dict], title: str = "Schema Analysis") -> str:
        """Format schema results into a readable plan format"""
        if not schemas:
            return f"-- {title}\n-- No schema data available"
        
        lines = [f"-- {title}", "-- " + "="*50]
        
        # Group by table_schema and table_name
        tables = {}
        for item in schemas:
            table_schema = item.get('table_schema', 'unknown')
            table_name = item.get('table_name', 'unknown')
            table_key = f"{table_schema}.{table_name}"
            
            if table_key not in tables:
                tables[table_key] = []
            tables[table_key].append(item)
        
        for table_key, columns in tables.items():
            lines.append(f"-- TABLE: {table_key}")
            lines.append(f"--   Columns: {len(columns)}")
            
            for col in sorted(columns, key=lambda x: x.get('column_name', '')):
                col_name = col.get('column_name', 'unknown')
                data_type = col.get('data_type', 'unknown')
                is_nullable = col.get('is_nullable', 'unknown')
                lines.append(f"--     {col_name}: {data_type} (nullable: {is_nullable})")
            lines.append("--")
        
        return '\n'.join(lines)
    
    def extract_dsn_info(self, dsn_name: str) -> Dict[str, str]:
        """Extract warehouse and database info from results or environment"""
        # For GitHub Actions, we'll use environment variables or defaults
        return {
            "warehouse": os.environ.get(f'{dsn_name.upper()}_WAREHOUSE', 'Default'),
            "database": os.environ.get(f'{dsn_name.upper()}_DATABASE', 'default')
        }
    
    def generate_report(self, dsn1_results_file: str, dsn2_results_file: str,
                       dsn1_schemas_file: str, dsn2_schemas_file: str,
                       output_file: str, dsn1_name: str = "Database 1", 
                       dsn2_name: str = "Database 2") -> None:
        """Generate the HTML comparison report"""
        
        self.logger.info("Loading database analysis results...")
        
        # Parse results
        dsn1_results = self.parse_database_results(dsn1_results_file)
        dsn2_results = self.parse_database_results(dsn2_results_file)
        dsn1_schemas = self.parse_schema_results(dsn1_schemas_file)
        dsn2_schemas = self.parse_schema_results(dsn2_schemas_file)
        
        self.logger.info(f"DSN1 results: {len(dsn1_results)} items, {len(dsn1_schemas)} schema items")
        self.logger.info(f"DSN2 results: {len(dsn2_results)} items, {len(dsn2_schemas)} schema items")
        
        # Create comparison results
        comparisons = self.create_comparison_results(
            dsn1_results, dsn2_results, dsn1_schemas, dsn2_schemas, dsn1_name, dsn2_name
        )
        
        # Generate HTML report
        self.logger.info("Generating HTML report...")
        report_generator = HTMLReportGenerator()
        
        # Create DSN info
        dsn1_info = self.extract_dsn_info("dsn1")
        dsn2_info = self.extract_dsn_info("dsn2")
        
        # Extract versions from results if available
        version1 = self.extract_version_from_results(dsn1_results)
        version2 = self.extract_version_from_results(dsn2_results)
        
        html_report = report_generator.generate_report(
            comparisons=comparisons,
            dsn1=f"***:***@{dsn1_name}",  # Masked DSN
            dsn2=f"***:***@{dsn2_name}",  # Masked DSN
            sql_file="Database Analysis Queries",
            version1=version1,
            version2=version2,
            dsn1_info=dsn1_info,
            dsn2_info=dsn2_info,
            snowflake_version=""  # No Snowflake in database comparison mode
        )
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        self.logger.info(f"Report generated: {os.path.abspath(output_file)}")
        
        # Print summary
        self.print_summary(comparisons, output_file)
    
    def extract_version_from_results(self, results: List[Dict]) -> str:
        """Extract database version from results"""
        for item in results:
            if item.get('category') == 'database_info' and item.get('metric') == 'version':
                return item.get('value', 'Unknown')
        return 'Unknown'
    
    def print_summary(self, comparisons: List[ComparisonResult], output_file: str):
        """Print execution summary"""
        total = len(comparisons)
        identical = sum(1 for c in comparisons if c.is_identical)
        similar = sum(1 for c in comparisons if c.status == "SIMILAR") 
        different = sum(1 for c in comparisons if c.status == "DIFFERENT")
        errors = sum(1 for c in comparisons if c.status == "ERROR")
        
        avg_similarity = sum(c.similarity_score for c in comparisons) / total if total > 0 else 0
        
        print(f"\n{'='*60}")
        print("DATABASE COMPARISON COMPLETED")
        print(f"{'='*60}")
        print(f"Total Analyses:       {total}")
        print(f"Identical Results:    {identical} ({identical/total:.1%})")
        print(f"Similar Results:      {similar} ({similar/total:.1%})")
        print(f"Different Results:    {different} ({different/total:.1%})")
        print(f"Error Results:        {errors} ({errors/total:.1%})")
        print(f"Avg Similarity:       {avg_similarity:.1%}")
        print(f"Report Generated:     {os.path.abspath(output_file)}")
        print(f"{'='*60}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate ExplainB-style comparison report from database analysis results",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--dsn1-results", 
        required=True,
        help="JSON file with DSN1 database analysis results"
    )
    
    parser.add_argument(
        "--dsn2-results",
        required=True, 
        help="JSON file with DSN2 database analysis results"
    )
    
    parser.add_argument(
        "--dsn1-schemas",
        required=True,
        help="JSON file with DSN1 schema information"
    )
    
    parser.add_argument(
        "--dsn2-schemas", 
        required=True,
        help="JSON file with DSN2 schema information"
    )
    
    parser.add_argument(
        "--output",
        required=True,
        help="Output HTML report file"
    )
    
    parser.add_argument(
        "--dsn1-name",
        default="Database 1",
        help="Display name for first database"
    )
    
    parser.add_argument(
        "--dsn2-name", 
        default="Database 2",
        help="Display name for second database"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    try:
        generator = DatabaseComparisonReportGenerator()
        generator.generate_report(
            args.dsn1_results,
            args.dsn2_results, 
            args.dsn1_schemas,
            args.dsn2_schemas,
            args.output,
            args.dsn1_name,
            args.dsn2_name
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()