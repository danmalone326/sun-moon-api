#!/usr/bin/env python3
"""Download and verify the production ephemeris outside request handling."""
import argparse, hashlib, shutil, urllib.request
from pathlib import Path

URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp"

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=Path("de440s.bsp")); p.add_argument("--sha256")
    a=p.parse_args(); tmp=a.output.with_suffix(".download")
    with urllib.request.urlopen(URL, timeout=120) as src, tmp.open("wb") as dst: shutil.copyfileobj(src,dst)
    digest=hashlib.sha256(tmp.read_bytes()).hexdigest()
    if a.sha256 and digest.lower()!=a.sha256.lower(): tmp.unlink(); raise SystemExit(f"SHA-256 mismatch: {digest}")
    tmp.replace(a.output); print(f"Installed {a.output} ({digest})")
if __name__ == "__main__": main()

