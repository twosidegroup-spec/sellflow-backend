"""Payment intelligence: normalized events, decisions, matching and audit.

Migrated from System A (`social-commerce-os/app/payment/*`) and adapted to
System B's canonical architecture: SQLAlchemy models, JWT/device credentials
and the SellFlow API conventions. The behaviour (provider detection,
normalization, confidence scoring, anomaly detection, duplicate handling,
order matching and decision audit) is preserved. The transaction id written
to the `payments` ledger is now the real provider TrxID instead of System A's
synthetic `PAYMENT-INTELLIGENCE-{order_id}` value.
"""
