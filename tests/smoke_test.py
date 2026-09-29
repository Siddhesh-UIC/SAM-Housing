#!/usr/bin/env python3
"""Smoke test: API up, data loaded, sam_agent grants correct. Run with containers up."""
import json
import subprocess
import urllib.request


def agent_sql(sql):
    r = subprocess.run(["docker", "exec", "sam-housing-db", "/opt/mssql-tools18/bin/sqlcmd", "-S", "localhost",
                        "-U", "sam_agent", "-P", "sam_agent123", "-d", "housing", "-C", "-b", "-h", "-1", "-W",
                        "-Q", "SET NOCOUNT ON; " + sql], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


assert json.load(urllib.request.urlopen("http://127.0.0.1:8000/health"))["status"] == "healthy"
assert len(json.load(urllib.request.urlopen("http://127.0.0.1:8000/admin/tables/housing_data"))) == 133
assert agent_sql("SELECT UnitCode FROM housing_data WHERE MobileNo1='9919819261'") == (0, "T-08/2501")
assert agent_sql("SELECT PanNo FROM housing_data")[0] != 0, "PII must be blocked"
assert agent_sql("UPDATE housing_data SET STATUS='x'")[0] != 0, "agent must not write"
assert agent_sql("EXEC raise_service_request 'NOPE', '', 'GENERAL', 't'")[1].startswith("0")
print("All smoke checks passed")
