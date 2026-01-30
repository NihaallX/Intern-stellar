"""
Email sender for job discovery reports.
Plain text only, engineering report style.
"""

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
    
    # Header
    lines.append(f"#{rank}: {job.title}")
    lines.append(f"    Company: {job.company}")
    lines.append(f"    Location: {job.location} {'(Remote)' if job.remote else ''}")
    lines.append(f"    Score: {job.score:.1f}/100")
    
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


def generate_email_body(jobs: list[Job]) -> str:
    """
    Generate the full email body.
    """
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append("AI JOB DISCOVERY REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Total matches: {len(jobs)}")
    lines.append("=" * 60)
    lines.append("")
    
    # Jobs
    for i, job in enumerate(jobs, 1):
        lines.append(format_job_entry(job, i))
        lines.append("")
        lines.append("-" * 40)
        lines.append("")
    
    # Footer
    lines.append("")
    lines.append("=" * 60)
    lines.append("END OF REPORT")
    lines.append("")
    lines.append("This is an automated engineering report.")
    lines.append("System: AI Job Discovery v1.0")
    lines.append("=" * 60)
    
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
    
    # Get recipient
    if recipient is None:
        recipient = settings.email.get("recipient", "")
    
    if not recipient:
        print("[EMAIL] Error: No recipient specified")
        return False
    
    # Generate email content
    body = generate_email_body(jobs)
    
    # Subject
    subject_prefix = settings.email.get("subject_prefix", "[AI Jobs]")
    date_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"{subject_prefix} {len(jobs)} matches - {date_str}"
    
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
