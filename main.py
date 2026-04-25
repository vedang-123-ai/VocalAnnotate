#!/usr/bin/env python3
"""
VocalAnnotate - Entry Point
Run this file to start the application.
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import main

if __name__ == "__main__":
    main()
