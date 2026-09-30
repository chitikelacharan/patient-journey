#!/usr/bin/env python3
"""
Single-Command Launcher for Med-Pulse 360
Patient Journey Bottleneck Analyzer (PNH1)
"""

import sys
import uvicorn

if __name__ == "__main__":
    print("==================================================================")
    print("       MED-PULSE 360: PATIENT JOURNEY BOTTLENECK ANALYZER        ")
    print("   Theme: HealthTech, MedAI & Diagnostics | Statement ID: PNH1   ")
    print("==================================================================")
    print("[+] Starting FastAPI ASGI server on http://127.0.0.1:8000 ...")
    print("[+] Interactive Dashboard: http://127.0.0.1:8000")
    print("[+] API Documentation:    http://127.0.0.1:8000/docs")
    print("[+] Prometheus Metrics:   http://127.0.0.1:8000/metrics")
    print("[+] Health Probe:         http://127.0.0.1:8000/health")
    print("==================================================================")

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
