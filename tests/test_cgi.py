import os, subprocess, sys
from pathlib import Path

def test_cgi_json_only_and_header():
    root=Path(__file__).parents[1]
    env=os.environ.copy(); env.update(QUERY_STRING="lat=abc&lng=0", PATH_INFO="/v2")
    result=subprocess.run([sys.executable, str(root/"cgi-bin/v2")],env=env,capture_output=True,text=True)
    assert result.returncode == 0
    header, body=result.stdout.split("\n\n",1)
    assert "Content-Type: application/json" in header
    assert body.strip().startswith('{')
    assert "Traceback" not in result.stdout

