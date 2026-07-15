"""
InjectX — Audit Package

Provides forensic-grade tracking of all decryption attempts.
Every key tried, every scheme applied, every outcome — recorded.
"""

from .trace import AuditLog, get_audit_log

__all__ = ["AuditLog", "get_audit_log"]
