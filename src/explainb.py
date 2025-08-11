#!/usr/bin/env python3
"""
ExplainB - Databend Explain Plan Comparison Tool

This tool compares explain plans between two versions of Databend by:
1. Reading SQL queries from tpcds.sql (or other SQL files)
2. Executing EXPLAIN for each query on both Databend instances
3. Comparing the explain plans and generating a detailed HTML report
4. Highlighting differences and providing beautiful visualization

Usage:
    export BENDSQL_DSN1="databend://user:pass@host1:port/db"
    export BENDSQL_DSN2="databend://user:pass@host2:port/db"
    python explainb.py --sql-file sql/tpcds.sql --output report.html
"""

import argparse
import os
import sys
import subprocess
import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
import difflib
import html


@dataclass
class ExplainResult:
    """Container for explain plan results"""
    query_index: int
    sql_query: str
    success: bool
    explain_plan: str = ""
    error_message: str = ""
    execution_time: float = 0.0
    engine_name: str = ""  # "DSN1", "DSN2", or "Snowflake"
    
    @property
    def short_sql(self) -> str:
        """Get shortened SQL for display"""
        sql_oneline = ' '.join(self.sql_query.split())
        if len(sql_oneline) <= 80:
            return sql_oneline
        return sql_oneline[:77] + "..."

@dataclass
class ComparisonResult:
    """Container for comparison results between two explain plans"""
    query_index: int
    sql_query: str
    dsn1_result: ExplainResult
    dsn2_result: ExplainResult
    snowflake_result: ExplainResult = None  # Snowflake reference result
    is_identical: bool = False
    similarity_score: float = 0.0
    diff_html: str = ""  # Keeping for backward compatibility
    diff_data: Dict = None  # New field for structured diff data
    
    @property
    def status(self) -> str:
        """Get comparison status"""
        if not self.dsn1_result.success or not self.dsn2_result.success:
            return "ERROR"
        elif self.is_identical:
            return "IDENTICAL"
        elif self.similarity_score > 0.8:
            return "SIMILAR"
        else:
            return "DIFFERENT"
    
    @property
    def short_sql(self) -> str:
        """Get shortened SQL for display"""
        sql_oneline = ' '.join(self.sql_query.split())
        if len(sql_oneline) <= 80:
            return sql_oneline
        return sql_oneline[:77] + "..."

class SQLExecutor:
    """Base class for SQL executors"""
    
    def __init__(self, dsn: str, name: str, tool_type: str = "bendsql"):
        self.dsn = dsn
        self.name = name
        self.tool_type = tool_type
        self.logger = logging.getLogger(f"{tool_type.upper()}-{name}")
    
    def get_version(self, timeout: int = 30) -> str:
        """Get database version"""
        if self.tool_type == "bendsql":
            return self._get_bendsql_version(timeout)
        elif self.tool_type == "snowsql":
            return self._get_snowsql_version(timeout)
        else:
            return "Unknown tool type"
    
    def execute_explain(self, query: str, timeout: int = 60) -> ExplainResult:
        """Execute EXPLAIN for a SQL query"""
        if self.tool_type == "bendsql":
            return self._execute_bendsql_explain(query, timeout)
        elif self.tool_type == "snowsql":
            return self._execute_snowsql_explain(query, timeout)
        else:
            return ExplainResult(
                query_index=0,
                sql_query=query,
                success=False,
                error_message="Unknown tool type",
                engine_name=self.name
            )

class BendSQLExecutor(SQLExecutor):
    """Execute SQL queries using bendsql with specified DSN"""
    
    def __init__(self, dsn: str, name: str):
        super().__init__(dsn, name, "bendsql")
    
    def _get_bendsql_version(self, timeout: int = 30) -> str:
        """Get Databend version using SELECT version()"""
        try:
            # Use bendsql with DSN environment variable
            env = os.environ.copy()
            env['BENDSQL_DSN'] = self.dsn
            
            cmd = ['bendsql', '--query=SELECT version()']
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                # Extract version from result (first line after any headers)
                lines = result.stdout.strip().split('\n')
                # Find the line that contains version info (usually the last non-empty line)
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith('+') and not line.startswith('|') and 'version()' not in line.lower():
                        return line
                return result.stdout.strip()
            else:
                self.logger.warning(f"Failed to get version for {self.name}: {result.stderr}")
                return "Version unavailable"
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Version query timeout for {self.name}")
            return "Version query timeout"
        except Exception as e:
            self.logger.warning(f"Error getting version for {self.name}: {e}")
            return "Version error"
    

    
    def _parse_snowflake_dsn(self) -> Tuple[str, str]:
        """Parse Snowflake DSN to extract warehouse and database info"""
        # For Snowflake, we'll use environment variables or defaults
        warehouse = os.environ.get('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')
        database = os.environ.get('SNOWFLAKE_DATABASE', 'TPCDS_100')
        return warehouse, database
    
    def _execute_bendsql_explain(self, query: str, timeout: int = 60) -> ExplainResult:
        """Execute EXPLAIN for a SQL query using bendsql"""
        explain_query = f"EXPLAIN {query.rstrip(';')}"
        start_time = time.time()
        
        try:
            # Use bendsql with DSN environment variable
            env = os.environ.copy()
            env['BENDSQL_DSN'] = self.dsn
            
            cmd = ['bendsql', f'--query={explain_query}']
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return ExplainResult(
                    query_index=0,  # Will be set by caller
                    sql_query=query,
                    success=True,
                    explain_plan=result.stdout.strip(),
                    execution_time=execution_time,
                    engine_name=self.name
                )
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return ExplainResult(
                    query_index=0,  # Will be set by caller
                    sql_query=query,
                    success=False,
                    error_message=error_msg.strip(),
                    execution_time=execution_time,
                    engine_name=self.name
                )
                
        except subprocess.TimeoutExpired:
            return ExplainResult(
                query_index=0,
                sql_query=query,
                success=False,
                error_message=f"Query timeout after {timeout} seconds",
                execution_time=timeout,
                engine_name=self.name
            )
        except Exception as e:
            return ExplainResult(
                query_index=0,
                sql_query=query,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time,
                engine_name=self.name
            )
    
    def _execute_snowsql_explain(self, query: str, timeout: int = 60) -> ExplainResult:
        """Execute EXPLAIN for a SQL query using snowsql"""
        explain_query = f"EXPLAIN {query.rstrip(';')}"
        start_time = time.time()
        
        try:
            # Parse warehouse and database from DSN or use defaults
            warehouse, database = self._parse_snowflake_dsn()
            
            cmd = [
                'snowsql', '--query', explain_query,
                '--dbname', database, '--schemaname', 'PUBLIC',
                '-o', 'output_format=tsv', '-o', 'header=false',
                '-o', 'timing=false', '-o', 'friendly=false'
            ]
            if warehouse:
                cmd.extend(['--warehouse', warehouse])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return ExplainResult(
                    query_index=0,  # Will be set by caller
                    sql_query=query,
                    success=True,
                    explain_plan=result.stdout.strip(),
                    execution_time=execution_time,
                    engine_name=self.name
                )
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return ExplainResult(
                    query_index=0,  # Will be set by caller
                    sql_query=query,
                    success=False,
                    error_message=error_msg.strip(),
                    execution_time=execution_time,
                    engine_name=self.name
                )
                
        except subprocess.TimeoutExpired:
            return ExplainResult(
                query_index=0,
                sql_query=query,
                success=False,
                error_message=f"Query timeout after {timeout} seconds",
                execution_time=timeout,
                engine_name=self.name
            )
        except Exception as e:
            return ExplainResult(
                query_index=0,
                sql_query=query,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time,
                engine_name=self.name
            )

class SnowSQLExecutor(SQLExecutor):
    """Execute SQL queries using snowsql"""
    
    def __init__(self, name: str = "Snowflake"):
        # For Snowflake, we don't use a DSN string
        super().__init__("", name, "snowsql")
    
    def _parse_snowflake_dsn(self):
        """Parse Snowflake DSN to extract warehouse and database"""
        # Since we're not using DSN for Snowflake, return default values
        # These should be configured via snowsql config or environment
        warehouse = os.environ.get('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')
        database = os.environ.get('SNOWFLAKE_DATABASE', 'TPCDS_100')
        return warehouse, database
    
    def _get_snowsql_version(self, timeout: int = 30) -> str:
        """Get Snowflake version using SELECT CURRENT_VERSION()"""
        try:
            # Parse warehouse and database from DSN
            warehouse, database = self._parse_snowflake_dsn()
            
            cmd = [
                'snowsql', '--query', 'SELECT CURRENT_VERSION();',
                '--dbname', database, '--schemaname', 'PUBLIC',
                '-o', 'output_format=tsv', '-o', 'header=false', 
                '-o', 'timing=false', '-o', 'friendly=false'
            ]
            if warehouse:
                cmd.extend(['--warehouse', warehouse])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith('CURRENT_VERSION'):
                        return line
                return result.stdout.strip()
            else:
                self.logger.warning(f"Failed to get version for {self.name}: {result.stderr}")
                return "Version unavailable"
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Version query timeout for {self.name}")
            return "Version query timeout"
        except Exception as e:
            self.logger.warning(f"Error getting version for {self.name}: {e}")
            return "Version error"
    
    def _execute_snowsql_explain(self, query: str, timeout: int = 60) -> ExplainResult:
        """Execute EXPLAIN for a SQL query using snowsql"""
        start_time = time.time()
        try:
            # Parse warehouse and database from DSN
            warehouse, database = self._parse_snowflake_dsn()
            
            explain_query = f"EXPLAIN USING TEXT {query.rstrip(';')}"
            cmd = [
                'snowsql', '--query', explain_query,
                '--dbname', database, '--schemaname', 'PUBLIC',
                '-o', 'output_format=tsv', '-o', 'header=false',
                '-o', 'timing=false', '-o', 'friendly=false'
            ]
            if warehouse:
                cmd.extend(['--warehouse', warehouse])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                # Process the result similar to checksb.py
                output = result.stdout.replace("None", "NULL").strip()
                if not output:
                    error_msg = "Snowsql returned empty result"
                    self.logger.warning(error_msg)
                    return ExplainResult(
                        query_index=0,
                        sql_query=query,
                        success=False,
                        explain_plan="",
                        execution_time=0.0,
                        error_message=error_msg
                    )
                
                return ExplainResult(
                    query_index=0,
                    sql_query=query,
                    success=True,
                    explain_plan=output,
                    execution_time=execution_time,
                    error_message="",
                    engine_name=self.name
                )
            else:
                error_msg = f"{result.stdout}\n{result.stderr}".strip() if (result.stdout or result.stderr) else "Unknown error"
                self.logger.error(f"Snowsql explain failed: {error_msg}")
                return ExplainResult(
                    query_index=0,
                    sql_query=query,
                    success=False,
                    explain_plan="",
                    execution_time=execution_time,
                    error_message=error_msg
                )
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_msg = f"Query timeout after {timeout} seconds"
            self.logger.error(error_msg)
            return ExplainResult(
                query_index=0,
                sql_query=query,
                success=False,
                explain_plan="",
                execution_time=execution_time,
                error_message=error_msg
            )
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error executing explain: {e}"
            self.logger.error(error_msg)
            return ExplainResult(
                query_index=0,
                sql_query=query,
                success=False,
                explain_plan="",
                execution_time=execution_time,
                error_message=error_msg
            )

class SQLParser:
    """Parse SQL files and extract individual queries"""
    
    @staticmethod
    def parse_file(file_path: str) -> List[str]:
        """Parse SQL file and return list of queries"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by semicolon and filter out empty queries
            queries = []
            raw_queries = content.split(';')
            
            for raw_query in raw_queries:
                # Remove comments and empty lines
                lines = []
                for line in raw_query.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('--'):
                        lines.append(line)
                
                if lines:
                    query = ' '.join(lines)
                    if query.strip():
                        queries.append(query.strip())
            
            return queries
            
        except Exception as e:
            raise RuntimeError(f"Failed to parse SQL file {file_path}: {e}")

class ExplainComparator:
    """Compare explain plans and generate diff reports"""
    
    @staticmethod
    def normalize_plan(plan: str) -> List[str]:
        """Normalize explain plan for comparison"""
        # Remove timestamps, session IDs, and other variable content
        lines = plan.split('\n')
        normalized = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove common variable elements
            line = re.sub(r'\bsession_id:\s*\w+', '', line)
            line = re.sub(r'\btimestamp:\s*[\d-]+\s+[\d:]+', '', line)
            line = re.sub(r'\bquery_id:\s*\w+', '', line)
            
            normalized.append(line)
        
        return normalized
    
    @classmethod
    def compare_plans(cls, result1: ExplainResult, result2: ExplainResult, snowflake_result: ExplainResult = None) -> ComparisonResult:
        """Compare two explain plan results with optional Snowflake reference"""
        # Normalize plans for comparison
        if result1.success and result2.success:
            plan1_lines = cls.normalize_plan(result1.explain_plan)
            plan2_lines = cls.normalize_plan(result2.explain_plan)
            
            # Check if identical
            is_identical = plan1_lines == plan2_lines
            
            # Calculate similarity score using SequenceMatcher
            matcher = difflib.SequenceMatcher(None, plan1_lines, plan2_lines)
            similarity_score = matcher.ratio()
            
            # Generate diff data
            diff_data = cls._generate_diff_data(result1, result2, plan1_lines, plan2_lines)
        else:
            is_identical = False
            similarity_score = 0.0
            plan1_lines = []
            plan2_lines = []
            diff_data = cls._generate_diff_data(result1, result2, plan1_lines, plan2_lines)
        
        return ComparisonResult(
            query_index=result1.query_index,
            sql_query=result1.sql_query,
            dsn1_result=result1,
            dsn2_result=result2,
            snowflake_result=snowflake_result,
            is_identical=is_identical,
            similarity_score=similarity_score,
            diff_html="",  # Keeping for backward compatibility
            diff_data=diff_data  # New structured data
        )
    
    @staticmethod
    def _generate_diff_data(result1: ExplainResult, result2: ExplainResult, 
                           plan1_lines: List[str], plan2_lines: List[str]) -> Dict:
        """Generate structured diff data with line numbers for GitHub-style view"""
        # Create unified diff view with line numbers
        matcher = difflib.SequenceMatcher(None, plan1_lines, plan2_lines)
        diff_lines = []
        
        dsn1_line_num = 1
        dsn2_line_num = 1
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Both sides have the same lines
                for idx, line in enumerate(plan1_lines[i1:i2]):
                    diff_lines.append({
                        "type": "equal",
                        "dsn1_line_num": dsn1_line_num + idx,
                        "dsn2_line_num": dsn2_line_num + idx,
                        "dsn1_content": line,
                        "dsn2_content": plan2_lines[j1 + idx]
                    })
                dsn1_line_num += i2 - i1
                dsn2_line_num += j2 - j1
                
            elif tag == 'delete':
                # Lines only in DSN1 (removed)
                for idx, line in enumerate(plan1_lines[i1:i2]):
                    diff_lines.append({
                        "type": "delete",
                        "dsn1_line_num": dsn1_line_num + idx,
                        "dsn2_line_num": None,
                        "dsn1_content": line,
                        "dsn2_content": ""
                    })
                dsn1_line_num += i2 - i1
                
            elif tag == 'insert':
                # Lines only in DSN2 (added)
                for idx, line in enumerate(plan2_lines[j1:j2]):
                    diff_lines.append({
                        "type": "insert",
                        "dsn1_line_num": None,
                        "dsn2_line_num": dsn2_line_num + idx,
                        "dsn1_content": "",
                        "dsn2_content": line
                    })
                dsn2_line_num += j2 - j1
                
            elif tag == 'replace':
                # Lines differ between DSN1 and DSN2
                max_lines = max(i2 - i1, j2 - j1)
                for idx in range(max_lines):
                    dsn1_content = plan1_lines[i1 + idx] if idx < (i2 - i1) else ""
                    dsn2_content = plan2_lines[j1 + idx] if idx < (j2 - j1) else ""
                    dsn1_num = (dsn1_line_num + idx) if idx < (i2 - i1) else None
                    dsn2_num = (dsn2_line_num + idx) if idx < (j2 - j1) else None
                    
                    if dsn1_content and not dsn2_content:
                        line_type = "delete"
                    elif not dsn1_content and dsn2_content:
                        line_type = "insert"
                    else:
                        line_type = "replace"
                    
                    diff_lines.append({
                        "type": line_type,
                        "dsn1_line_num": dsn1_num,
                        "dsn2_line_num": dsn2_num,
                        "dsn1_content": dsn1_content,
                        "dsn2_content": dsn2_content
                    })
                dsn1_line_num += i2 - i1
                dsn2_line_num += j2 - j1
        
        return {
            "dsn1_info": {
                "name": "DSN1",
                "execution_time": result1.execution_time,
                "success": result1.success,
                "error_message": result1.error_message if not result1.success else ""
            },
            "dsn2_info": {
                "name": "DSN2", 
                "execution_time": result2.execution_time,
                "success": result2.success,
                "error_message": result2.error_message if not result2.success else ""
            },
            "diff_lines": diff_lines
        }

class HTMLReportGenerator:
    """Generate beautiful HTML reports using JSON data and dynamic rendering"""
    
    def __init__(self):
        self.template_path = Path(__file__).parent.parent / "templates" / "report.html"
    
    def generate_report(self, comparisons: List[ComparisonResult], 
                       dsn1: str, dsn2: str, sql_file: str, version1: str = "", version2: str = "", 
                       dsn1_info: Dict = None, dsn2_info: Dict = None, snowflake_version: str = "") -> str:
        """Generate complete HTML report with JSON data"""
        # Create report data structure
        report_data = self._create_report_data(comparisons, dsn1, dsn2, sql_file, version1, version2, dsn1_info, dsn2_info, snowflake_version)
        
        # Load template
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            raise RuntimeError(f"Template file not found: {self.template_path}")
        
        # Inject JSON data into template
        json_data = json.dumps(report_data, indent=2, ensure_ascii=False)
        report_html = template_content.replace('{report_data}', json_data)
        
        return report_html
    
    def _create_report_data(self, comparisons: List[ComparisonResult], 
                           dsn1: str, dsn2: str, sql_file: str, version1: str = "", version2: str = "",
                           dsn1_info: Dict = None, dsn2_info: Dict = None, snowflake_version: str = "") -> Dict:
        """Create structured data for the report"""
        # Calculate statistics
        total_queries = len(comparisons)
        identical_count = sum(1 for c in comparisons if c.is_identical)
        similar_count = sum(1 for c in comparisons if c.status == "SIMILAR")
        different_count = sum(1 for c in comparisons if c.status == "DIFFERENT")
        error_count = sum(1 for c in comparisons if c.status == "ERROR")
        avg_similarity = sum(c.similarity_score for c in comparisons) / total_queries if total_queries > 0 else 0
        
        # Create comparison data
        query_results = []
        for comparison in comparisons:
            query_data = {
                "query_index": comparison.query_index,
                "sql_query": comparison.sql_query,
                "short_sql": comparison.short_sql,
                "status": comparison.status,
                "similarity_score": comparison.similarity_score,
                "is_identical": comparison.is_identical,
                "dsn1_result": {
                    "success": comparison.dsn1_result.success,
                    "explain_plan": comparison.dsn1_result.explain_plan,
                    "error_message": comparison.dsn1_result.error_message,
                    "execution_time": comparison.dsn1_result.execution_time
                },
                "dsn2_result": {
                    "success": comparison.dsn2_result.success,
                    "explain_plan": comparison.dsn2_result.explain_plan,
                    "error_message": comparison.dsn2_result.error_message,
                    "execution_time": comparison.dsn2_result.execution_time
                },
                "snowflake_result": {
                    "success": comparison.snowflake_result.success if comparison.snowflake_result else False,
                    "explain_plan": comparison.snowflake_result.explain_plan if comparison.snowflake_result else "",
                    "error_message": comparison.snowflake_result.error_message if comparison.snowflake_result else "",
                    "execution_time": comparison.snowflake_result.execution_time if comparison.snowflake_result else 0.0
                },
                "diff_data": comparison.diff_data
            }
            query_results.append(query_data)
        
        # Default DSN info if not provided
        dsn1_info = dsn1_info or {"warehouse": "Unknown", "database": "Unknown"}
        dsn2_info = dsn2_info or {"warehouse": "Unknown", "database": "Unknown"}
        
        return {
            "meta": {
                "title": "Databend Explain Plan Comparison Report",
                "generation_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "dsn1": dsn1,
                "dsn2": dsn2,
                "dsn1_version": version1,
                "dsn2_version": version2,
                "dsn1_warehouse": dsn1_info["warehouse"],
                "dsn1_database": dsn1_info["database"],
                "dsn2_warehouse": dsn2_info["warehouse"], 
                "dsn2_database": dsn2_info["database"],
                "snowflake_version": snowflake_version,
                "sql_file": sql_file
            },
            "statistics": {
                "total_queries": total_queries,
                "identical_count": identical_count,
                "similar_count": similar_count,
                "different_count": different_count,
                "error_count": error_count,
                "avg_similarity": avg_similarity
            },
            "query_results": query_results
        }

class ExplainB:
    """Main application class for ExplainB"""
    
    def __init__(self):
        self.logger = logging.getLogger("ExplainB")
    
    @staticmethod
    def mask_dsn(dsn: str) -> str:
        """Mask username and password in DSN for display"""
        if not dsn:
            return dsn
        
        # Pattern: protocol://username:password@host/database
        import re
        pattern = r'([\w+]+://)[^:@]+:[^@]+(@.+)'
        match = re.match(pattern, dsn)
        
        if match:
            protocol = match.group(1)
            host_and_db = match.group(2)
            return f"{protocol}***:***{host_and_db}"
        
        return dsn
    
    @staticmethod
    def parse_dsn_info(dsn: str) -> Dict[str, str]:
        """Parse DSN to extract warehouse and database information"""
        if not dsn:
            return {"warehouse": "Unknown", "database": "Unknown"}
        
        import re
        # Pattern: databend://user:pass@host--warehouse.domain/database
        pattern = r'databend://[^@]+@([^/]+)/(.+)'
        match = re.match(pattern, dsn)
        
        if match:
            host_part = match.group(1)  # e.g., tnscfp003--version-test.gw.aws-us-east-2.default.databend.com
            database = match.group(2)   # e.g., tpcds_100
            
            # Extract warehouse from host (format: prefix--warehouse.domain)
            warehouse_pattern = r'[^-]+--([^.]+)'
            warehouse_match = re.search(warehouse_pattern, host_part)
            warehouse = warehouse_match.group(1) if warehouse_match else "Unknown"
            
            return {
                "warehouse": warehouse,
                "database": database
            }
        
        return {"warehouse": "Unknown", "database": "Unknown"}
        
    def run(self, args):
        """Run the explain plan comparison"""
        # Validate environment - support both BENDSQL_DSN and BEDNSQL_DSN naming
        dsn1 = os.environ.get('BENDSQL_DSN1') or os.environ.get('BEDNSQL_DSN1')
        dsn2 = os.environ.get('BENDSQL_DSN2') or os.environ.get('BEDNSQL_DSN2')
        
        if not dsn1 or not dsn2:
            raise RuntimeError("Both DSN1 and DSN2 environment variables must be set. Use either BENDSQL_DSN1/BENDSQL_DSN2 or BEDNSQL_DSN1/BEDNSQL_DSN2")
        
        # Fix bash history expansion escaping of exclamation marks
        dsn1 = dsn1.replace('\\!', '!')
        dsn2 = dsn2.replace('\\!', '!')
        
        self.logger.info(f"🚀 Starting ExplainB comparison")
        self.logger.info(f"📁 SQL File: {args.sql_file}")
        self.logger.info(f"📊 Output: {args.output}")
        self.logger.info(f"🔗 DSN1: {self.mask_dsn(dsn1)}")
        self.logger.info(f"🔗 DSN2: {self.mask_dsn(dsn2)}")
        
        # Parse SQL queries
        self.logger.info("📋 Parsing SQL queries...")
        queries = SQLParser.parse_file(args.sql_file)
        self.logger.info(f"✅ Found {len(queries)} queries")
        
        # Create executors
        executor1 = BendSQLExecutor(dsn1, "DSN1")
        executor2 = BendSQLExecutor(dsn2, "DSN2")
        
        # Get versions
        self.logger.info("🔍 Getting database versions...")
        version1 = executor1.get_version()
        version2 = executor2.get_version()
        self.logger.info(f"📦 DSN1 Version: {version1}")
        self.logger.info(f"📦 DSN2 Version: {version2}")
        
        # Only create Snowflake executor if --runbend is not specified
        snowflake_executor = None
        snowflake_version = ""
        if not args.runbend:
            snowflake_executor = SnowSQLExecutor("Snowflake")
            snowflake_version = snowflake_executor.get_version()
            self.logger.info(f"📦 Snowflake Version: {snowflake_version}")
        else:
            self.logger.info("⏭️ Skipping Snowflake (--runbend mode)")
        
        # Execute explain plans and compare
        comparisons = []
        total_queries = len(queries)
        
        for i, query in enumerate(queries, 1):
            self.logger.info(f"🔄 Processing Query {i:02d}/{total_queries:02d}")
            
            # Execute explains on both Databend instances
            result1 = executor1.execute_explain(query, timeout=args.timeout)
            result1.query_index = i
            
            result2 = executor2.execute_explain(query, timeout=args.timeout)
            result2.query_index = i
            
            # Execute explain on Snowflake (as reference) only if not in --runbend mode
            snowflake_result = None
            if not args.runbend and snowflake_executor:
                self.logger.info(f"   ❄️ Getting Snowflake reference for Query {i:02d}")
                snowflake_result = snowflake_executor.execute_explain(query, timeout=args.timeout)
                snowflake_result.query_index = i
                
                if snowflake_result.success:
                    self.logger.info(f"   ❄️ Query {i:02d}: Snowflake reference available")
                else:
                    self.logger.info(f"   ❄️ Query {i:02d}: Snowflake reference failed")
            
            # Compare results
            comparison = ExplainComparator.compare_plans(result1, result2, snowflake_result)
            comparisons.append(comparison)
            
            # Log result
            status = comparison.status
            similarity = comparison.similarity_score
            self.logger.info(f"   📝 Query {i:02d}: {status} (similarity: {similarity:.1%})")
        
        # Generate report
        self.logger.info("📊 Generating HTML report...")
        report_generator = HTMLReportGenerator()
        # Use masked DSNs for display in the report
        masked_dsn1 = self.mask_dsn(dsn1)
        masked_dsn2 = self.mask_dsn(dsn2)
        # Parse DSN info for warehouse and database
        dsn1_info = self.parse_dsn_info(dsn1)
        dsn2_info = self.parse_dsn_info(dsn2)
        html_report = report_generator.generate_report(comparisons, masked_dsn1, masked_dsn2, args.sql_file, version1, version2, dsn1_info, dsn2_info, snowflake_version)
        
        # Write report
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        # Print summary
        self._print_summary(comparisons, args.output)
    
    def _print_summary(self, comparisons: List[ComparisonResult], output_file: str):
        """Print execution summary"""
        total = len(comparisons)
        identical = sum(1 for c in comparisons if c.is_identical)
        similar = sum(1 for c in comparisons if c.status == "SIMILAR")
        different = sum(1 for c in comparisons if c.status == "DIFFERENT")
        errors = sum(1 for c in comparisons if c.status == "ERROR")
        
        avg_similarity = sum(c.similarity_score for c in comparisons) / total if total > 0 else 0
        
        print(f"\n{'='*60}")
        print("🎉 EXPLAINB COMPARISON COMPLETED")
        print(f"{'='*60}")
        print(f"📊 Total Queries:     {total}")
        print(f"✅ Identical Plans:   {identical} ({identical/total:.1%})")
        print(f"🟡 Similar Plans:     {similar} ({similar/total:.1%})")
        print(f"🔴 Different Plans:   {different} ({different/total:.1%})")
        print(f"❌ Error Queries:     {errors} ({errors/total:.1%})")
        print(f"📈 Avg Similarity:    {avg_similarity:.1%}")
        print(f"📄 Report Generated:  {os.path.abspath(output_file)}")
        print(f"{'='*60}")
        
        if errors > 0:
            print("⚠️  Some queries had errors. Check the HTML report for details.")
        
        print(f"\n🌐 Open the report: file://{os.path.abspath(output_file)}")

def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="ExplainB - Compare Databend explain plans between two versions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  BENDSQL_DSN1/BEDNSQL_DSN1    DSN for first Databend instance
  BENDSQL_DSN2/BEDNSQL_DSN2    DSN for second Databend instance

Example:
  export BENDSQL_DSN1="databend://user:pass@host1:port/db"
  export BENDSQL_DSN2="databend://user:pass@host2:port/db"
  python explainb.py --sql-file sql/tpcds.sql --output report.html
        """
    )
    
    parser.add_argument(
        "--sql-file",
        required=True,
        help="Path to SQL file containing queries to analyze"
    )
    
    parser.add_argument(
        "--output",
        default="explainb_report.html",
        help="Output HTML report file (default: explainb_report.html)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Query timeout in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--runbend",
        action="store_true",
        help="Run only Databend comparison (skip Snowflake reference)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    try:
        app = ExplainB()
        app.run(args)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()