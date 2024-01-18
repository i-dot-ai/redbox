"""Swaps the stdlib sqlite3 lib with the pysqlite3 package"""
import sys

__import__("pysqlite3")

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
