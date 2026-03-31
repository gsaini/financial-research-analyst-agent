"""
Scheduled Reports & Email Digest Tool (Phase 4).

Manages report schedules (daily, weekly, monthly) and generates
digest content. Email sending uses SMTP if configured, otherwise
saves reports to disk.

Usage::

    from src.tools.scheduled_reports import create_schedule, generate_digest
    create_schedule("daily", ["AAPL", "MSFT"], "user@example.com")
    digest = generate_digest(["AAPL", "MSFT"])
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Schedule Management ──────────────────────────────────────

_schedules: List[Dict[str, Any]] = []


def create_schedule(
    frequency: str,
    symbols: List[str],
    email: str = "",
    report_type: str = "summary",
) -> Dict[str, Any]:
    """
    Create a report schedule.

    Args:
        frequency: "daily", "weekly", or "monthly".
        symbols: Stock tickers to include.
        email: Email address for delivery (optional).
        report_type: "summary", "detailed", or "portfolio".

    Returns:
        Dict with schedule details.
    """
    if frequency not in ("daily", "weekly", "monthly"):
        return {"error": f"Invalid frequency: {frequency}. Use daily/weekly/monthly."}

    schedule = {
        "id": f"sched_{len(_schedules) + 1}_{int(datetime.now().timestamp())}",
        "frequency": frequency,
        "symbols": [s.upper() for s in symbols],
        "email": email,
        "report_type": report_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
        "active": True,
    }
    _schedules.append(schedule)
    logger.info(f"Report schedule created: {schedule['id']}")
    return {"status": "created", "schedule": schedule}


def list_schedules() -> List[Dict[str, Any]]:
    """List all report schedules."""
    return _schedules


def delete_schedule(schedule_id: str) -> Dict[str, Any]:
    """Delete a schedule by ID."""
    global _schedules
    before = len(_schedules)
    _schedules = [s for s in _schedules if s["id"] != schedule_id]
    if len(_schedules) < before:
        return {"status": "deleted", "schedule_id": schedule_id}
    return {"status": "not_found", "schedule_id": schedule_id}


# ── Digest Generation ────────────────────────────────────────


def generate_digest(
    symbols: List[str],
    report_type: str = "summary",
) -> Dict[str, Any]:
    """
    Generate a digest report for given symbols.

    Args:
        symbols: List of stock tickers.
        report_type: "summary" or "detailed".

    Returns:
        Dict with digest content in text and HTML formats.
    """
    try:
        from src.tools.market_data import get_stock_price
        from src.tools.news_fetcher import fetch_company_news

        digest_items = []
        for symbol in symbols:
            price_data = get_stock_price(symbol)
            news = fetch_company_news(symbol)[:3]

            item = {
                "symbol": symbol,
                "price": price_data.get("current_price", 0),
                "change_pct": price_data.get("change_percent", 0),
                "volume": price_data.get("volume", 0),
                "headlines": [n.get("title", "") for n in news],
            }
            digest_items.append(item)

        # Generate text format
        text_parts = [
            f"Financial Digest — {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            "=" * 60,
            "",
        ]
        for item in digest_items:
            arrow = "▲" if item["change_pct"] > 0 else "▼" if item["change_pct"] < 0 else "→"
            text_parts.append(
                f"{item['symbol']}: ${item['price']:.2f} "
                f"{arrow} {item['change_pct']:+.2f}%"
            )
            for headline in item["headlines"][:2]:
                text_parts.append(f"  • {headline[:80]}")
            text_parts.append("")

        text_content = "\n".join(text_parts)

        # Generate HTML format
        html_parts = [
            "<html><body style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;'>",
            f"<h2 style='color: #1a1a2e;'>Financial Digest</h2>",
            f"<p style='color: #666;'>{datetime.now(timezone.utc).strftime('%B %d, %Y')}</p>",
            "<hr>",
        ]
        for item in digest_items:
            color = "#00cc66" if item["change_pct"] > 0 else "#ff4444" if item["change_pct"] < 0 else "#888"
            html_parts.append(
                f"<div style='margin: 15px 0; padding: 10px; border-left: 3px solid {color};'>"
                f"<strong>{item['symbol']}</strong> — "
                f"<span style='font-size: 1.1em;'>${item['price']:.2f}</span> "
                f"<span style='color: {color};'>{item['change_pct']:+.2f}%</span>"
            )
            if item["headlines"]:
                html_parts.append("<ul style='margin: 5px 0; padding-left: 20px;'>")
                for h in item["headlines"][:2]:
                    html_parts.append(f"<li style='font-size: 0.9em; color: #444;'>{h[:80]}</li>")
                html_parts.append("</ul>")
            html_parts.append("</div>")

        html_parts.append(
            "<hr><p style='color: #999; font-size: 0.8em;'>"
            "Generated by AI Financial Research Agent</p>"
            "</body></html>"
        )
        html_content = "\n".join(html_parts)

        return {
            "symbols": symbols,
            "report_type": report_type,
            "item_count": len(digest_items),
            "text_content": text_content,
            "html_content": html_content,
            "items": digest_items,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Digest generation failed: {e}")
        return {"error": str(e)}


# ── Email Delivery ───────────────────────────────────────────


def send_digest_email(
    to_email: str,
    digest: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Send digest via email using SMTP.

    Requires environment variables:
    - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

    Args:
        to_email: Recipient email address.
        digest: Digest dict from generate_digest().

    Returns:
        Dict with delivery status.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user:
        # Save to disk instead
        return _save_digest_to_disk(digest, to_email)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Financial Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        msg["From"] = smtp_from
        msg["To"] = to_email

        text_part = MIMEText(digest.get("text_content", ""), "plain")
        html_part = MIMEText(digest.get("html_content", ""), "html")
        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Digest email sent to {to_email}")
        return {"status": "sent", "to": to_email}

    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return _save_digest_to_disk(digest, to_email)


def _save_digest_to_disk(digest: Dict, to_email: str) -> Dict[str, Any]:
    """Fallback: save digest to disk when email is not configured."""
    try:
        from src.config import settings
        output_dir = settings.data_dir / "digests"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = output_dir / f"digest_{timestamp}.html"
        filepath.write_text(digest.get("html_content", ""))

        logger.info(f"Digest saved to {filepath} (email not configured)")
        return {
            "status": "saved_to_disk",
            "file_path": str(filepath),
            "note": "SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD to enable email.",
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}
