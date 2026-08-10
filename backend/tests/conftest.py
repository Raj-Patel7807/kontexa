"""Shared pytest configuration for backend tests."""

import os

# Test collection imports settings, so isolate it from the shell's DEBUG value.
os.environ["DEBUG"] = "false"
