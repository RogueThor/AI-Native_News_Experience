"""
agents/model_config.py — Central model selection for all Groq-powered agents.

Strategy:
  - QUALITY_MODEL: For user-facing tasks (reporter, briefing, translation, story arc, chat).
    Uses llama-3.3-70b-versatile when quota available; fall back to 8b when exhausted.
  - BULK_MODEL: For high-volume background tasks (batch classification).
    Always uses llama-3.1-8b-instant to preserve 70b daily quota.

Groq Free Tier Limits:
  - llama-3.1-8b-instant: 6,000 TPM / 500,000 TPD
  - llama-3.3-70b-versatile: 6,000 TPM / 100,000 TPD  ← exhausts quickly with 190+ articles/run

To switch all agents when 70b quota is exhausted, just change QUALITY_MODEL below.
"""

# High-volume background classification — never use 70b here
BULK_MODEL = "llama-3.1-8b-instant"

# User-facing quality tasks — switch to 8b if 70b quota exhausted
QUALITY_MODEL = "llama-3.1-8b-instant"  # Temporarily using 8b — switch back to 70b tomorrow
# QUALITY_MODEL = "llama-3.3-70b-versatile"  # Uncomment when 70b quota resets
