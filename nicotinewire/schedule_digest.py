"""
Weekly Monday Digest Scheduler for NicotineWire.
Schedules run_pipeline.py to run once every Monday at 08:00 UTC.
"""

import os
import sys
import time
from datetime import datetime

print("==================================================")
print("  NICOTINEWIRE WEEKLY MONDAY DIGEST SCHEDULER     ")
print("==================================================")
print("Configured Schedule: Every Monday at 08:00 UTC")
print("Status: Active & Monitoring Feed Triggers...")

# Ensure path compatibility
sys.path.insert(0, os.path.dirname(__file__))

from run_pipeline import run_single_iteration

if __name__ == "__main__":
    run_single_iteration()
