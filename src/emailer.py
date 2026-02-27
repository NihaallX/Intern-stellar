"""
Email sender for job discovery reports.
Plain text only, engineering report style.
Sections: Big Tech → APM Track → High Signal AI → Remote/India → Rest
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from src.models import Job
from src.utils.config import get_smtp_credentials, load_settings


def format_job_entry(job: Job, rank: int) -> str:
    """
    Format a single job entry for the email.
    Plain text, no HTML.
    """
    lines = []
    
    # Header with tags
    tags = job.tags or []
    tag_str = f"  [{', '.join(tags)}]" if tags else ""
    lines.append(f"#{rank}: {job.title or 'Untitled'}{tag_str}")
    lines.append(f"    Company: {job.company or 'Unknown'}")
    lines.append(f"    Location: {job.location or 'Unknown'} {'(Remote)' if job.remote else ''}")
    score_line = f"    Score: {job.score:.1f}/100"
    if job.ai_relevance_score is not None:
        score_line += f"  |  AI Relevance: {job.ai_relevance_score:.0%}"
    lines.append(score_line)
    
    # Company enrichment (if available)
    if job.company_enrichment:
        enrich = job.company_enrichment
        enrichment_parts = []
        
        if enrich.employee_count:
            enrichment_parts.append(f"{enrich.employee_count} employees")
        if enrich.funding_stage:
            enrichment_parts.append(enrich.funding_stage)
        if enrich.is_ai_company:
            enrichment_parts.append("AI-native ✓")
        if enrich.glassdoor_rating:
            enrichment_parts.append(f"Glassdoor: {enrich.glassdoor_rating}/5")
        
        if enrichment_parts:
            lines.append(f"    Company info: {', '.join(enrichment_parts)}")
    
    # Score breakdown
    if job.score_breakdown:
        bd = job.score_breakdown
        lines.append(f"    Breakdown: Similarity={bd.similarity:.0f}, Skills={bd.skill_match:.0f}, "
                    f"Exp={bd.experience_fit:.0f}, Company={bd.company_signal:.0f}, Adj={bd.penalties:+.0f}")
    
    # Why matched
    if job.why_matched:
        lines.append("    Why matched:")
        for reason in job.why_matched:
            lines.append(f"      - {reason}")
    
    # Link
    lines.append(f"    Apply: {job.url}")
    
    return "\n".join(lines)


def _section(jobs: list[Job], tag: str) -> list[Job]:
    """Return jobs that have a given tag, sorted by score desc."""
    return sorted([j for j in jobs if tag in (j.tags or [])], key=lambda j: j.score or 0, reverse=True)


def generate_email_body(jobs: list[Job]) -> str:
    """
    Generate the full email body with tag-based sections.
    Order: Big Tech → APM Track → High Signal AI → Remote/India → All Others
    """
    lines = []
    
    # ── Header ──
    lines.append("=" * 65)
    lines.append("AI PM / ENGINEERING JOB DISCOVERY REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Total matches: {len(jobs)}")
    
    # Tag summary
    from collections import Counter
    all_tags: list[str] = []
    for j in jobs:
        all_tags.extend(j.tags or [])
    tag_counts = Counter(all_tags)
    if tag_counts:
        tag_summary = "  |  ".join(f"{t}: {c}" for t, c in tag_counts.most_common(6))
        lines.append(f"Tags: {tag_summary}")
    lines.append("=" * 65)
    lines.append("")
    
    # Track which jobs were already shown to avoid duplicates
    shown_urls: set[str] = set()
    global_rank = 1
    
    def emit_section(header: str, section_jobs: list[Job]) -> None:
        nonlocal global_rank
        new_jobs = [j for j in section_jobs if j.url not in shown_urls]
        if not new_jobs:
            return
        lines.append("┌" + "─" * 63 + "┐")
        lines.append(f"│  {header:<61}│")
        lines.append("└" + "─" * 63 + "┘")
        lines.append("")
        for job in new_jobs:
            lines.append(format_job_entry(job, global_rank))
            lines.append("")
            lines.append("  " + "-" * 45)
            lines.append("")
            shown_urls.add(job.url)
            global_rank += 1
    
    # 🏆 Big Tech (FAANG / Big AI)
    emit_section("🏆 BIG TECH  (Google · Meta · Amazon · OpenAI · Anthropic …)", _section(jobs, "Big Tech"))
    
    # 📋 APM Track
    emit_section("📋 APM TRACK  (Associate PM / Entry-level PM roles)", _section(jobs, "APM Track"))
    
    # 🤖 High Signal AI
    emit_section("🤖 HIGH SIGNAL AI  (Top-tier AI-native companies)", _section(jobs, "High Signal AI"))
    
    # 🌏 India / Remote
    india_remote = sorted(
        [j for j in jobs if j.url not in shown_urls and ("India" in (j.tags or []) or "Remote" in (j.tags or []))],
        key=lambda j: j.score or 0, reverse=True
    )
    if india_remote:
        lines.append("┌" + "─" * 63 + "┐")
        lines.append(f"│  {'🌏 INDIA / REMOTE':<61}│")
        lines.append("└" + "─" * 63 + "┘")
        lines.append("")
        for job in india_remote:
            lines.append(format_job_entry(job, global_rank))
            lines.append("")
            lines.append("  " + "-" * 45)
            lines.append("")
            shown_urls.add(job.url)
            global_rank += 1
    
    # 📌 All Other Matches
    remaining = [j for j in jobs if j.url not in shown_urls]
    if remaining:
        lines.append("┌" + "─" * 63 + "┐")
        lines.append(f"│  {'📌 ALL OTHER MATCHES':<61}│")
        lines.append("└" + "─" * 63 + "┘")
        lines.append("")
        for job in remaining:
            lines.append(format_job_entry(job, global_rank))
            lines.append("")
            lines.append("  " + "-" * 45)
            lines.append("")
            global_rank += 1
    
    # ── Footer ──
    lines.append("")
    lines.append("=" * 65)
    lines.append("END OF REPORT")
    lines.append("")
    lines.append("Automated daily AI job discovery. Run: github.com/NihaallX/Intern-stellar")
    lines.append("=" * 65)
    
    return "\n".join(lines)


def send_email(
    jobs: list[Job],
    recipient: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """
    Send the job discovery email.
    
    Args:
        jobs: List of scored and ranked jobs
        recipient: Override recipient email
        dry_run: If True, print email instead of sending
        
    Returns:
        True if successful, False otherwise
    """
    settings = load_settings()
    
    # Get recipient — env var overrides settings.yaml
    if recipient is None:
        recipient = os.environ.get("EMAIL_RECIPIENT") or settings.email.get("recipient", "")
    
    if not recipient:
        print("[EMAIL] Error: No recipient specified")
        return False
    
    # Generate email content
    body = generate_email_body(jobs)
    
    # Subject
    subject_prefix = settings.email.get("subject_prefix", "[AI PM Jobs]")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Count big-tech and APM matches for subject line
    big_tech_count = sum(1 for j in jobs if "Big Tech" in j.tags)
    apm_count = sum(1 for j in jobs if "APM Track" in j.tags)
    
    subject_parts = [f"{len(jobs)} matches"]
    if big_tech_count:
        subject_parts.append(f"{big_tech_count} Big Tech")
    if apm_count:
        subject_parts.append(f"{apm_count} APM")
    
    subject = f"{subject_prefix} {' | '.join(subject_parts)} - {date_str}"
    
    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - EMAIL PREVIEW")
        print("=" * 60)
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print("-" * 60)
        print(body)
        print("=" * 60)
        return True
    
    # Send email
    try:
        smtp_email, smtp_password = get_smtp_credentials()
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Plain text only
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        print(f"[EMAIL] Connecting to SMTP server...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
        
        print(f"[EMAIL] Successfully sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"[EMAIL] Error sending email: {e}")
        return False


if __name__ == "__main__":
    # Test with dummy data
    from src.models import ScoreBreakdown
    
    test_jobs = [
        Job(
            title="AI Engineer",
            company="AI Startup Inc",
            url="https://example.com/job1",
            source="greenhouse",
            location="Remote",
            remote=True,
            score=85.5,
            score_breakdown=ScoreBreakdown(
                similarity=35, skill_match=22, experience_fit=15,
                company_signal=10, penalties=3.5
            ),
            why_matched=["RAG experience", "FastAPI + AWS", "AI-native startup"]
        ),
        Job(
            title="GenAI Developer",
            company="TechCorp",
            url="https://example.com/job2",
            source="lever",
            location="San Francisco, CA",
            remote=False,
            score=72.0,
            score_breakdown=ScoreBreakdown(
                similarity=30, skill_match=18, experience_fit=12,
                company_signal=7, penalties=5
            ),
            why_matched=["LLM systems", "Junior role"]
        ),
    ]
    
    send_email(test_jobs, dry_run=True)
