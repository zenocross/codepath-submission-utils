#!/usr/bin/env python3
"""
Simple script to fetch and format student submissions by project
Calls the Flask API endpoint and formats the output in a readable way
"""

import sys
import requests
import argparse
from collections import defaultdict
from typing import Dict, List, Any
from datetime import datetime


def fetch_submissions(base_url: str, student: str = None, master_repo_owner: str = "codepath", start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    """
    Fetch submissions from the API endpoint
    
    Args:
        base_url: Base URL of the API (e.g., http://localhost:3000)
        student: Optional student username (if None, fetches all students)
        master_repo_owner: Master repo owner (default: codepath)
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
    
    Returns:
        API response as dictionary
    """
    if student:
        url = f"{base_url}/admin/fetch-student-submission/{student}"
    else:
        url = f"{base_url}/admin/fetch-student-submissions"
    
    params = {'master_repo_owner': master_repo_owner}
    
    # Add date filters to params if provided
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    
    print(f"🔍 Fetching submissions from: {url}")
    print(f"   Master repo owner: {master_repo_owner}")
    if student:
        print(f"   Student: {student}")
    if start_date:
        print(f"   Start date: {start_date}")
    if end_date:
        print(f"   End date: {end_date}")
    print()
    
    try:
        response = requests.get(url, params=params, timeout=1200)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching submissions: {e}")
        sys.exit(1)


def get_submission_location(submission: Dict[str, Any]) -> str:
    """Determine where the submission was made"""
    if submission.get('is_codepath_submission'):
        return "codepath repo"
    
    repo_type = submission.get('repo_type', 'unknown')
    if repo_type == 'student_fork':
        return "own fork"
    elif repo_type == 'codepath_repo':
        return "codepath repo"
    else:
        return "other"


def get_submission_url(submission: Dict[str, Any]) -> str:
    """Generate GitHub URL for the submission"""
    owner = submission.get('owner_name')
    repo = submission.get('repo_name')
    
    if submission['submission_type'] == 'COMMENT':
        issue_num = submission.get('issue_number')
        comment_id = submission.get('comment_id')
        return f"https://github.com/{owner}/{repo}/issues/{issue_num}#issuecomment-{comment_id}"
    elif submission['submission_type'] == 'PULL_REQUEST':
        pr_num = submission.get('pr_number')
        return f"https://github.com/{owner}/{repo}/pull/{pr_num}"
    
    return "N/A"


def get_submission_title(submission: Dict[str, Any]) -> str:
    """Get the title/description of the submission"""
    if submission['submission_type'] == 'COMMENT':
        issue_display = submission.get('issue_display', f"#{submission.get('issue_number')}")
        issue_title = submission.get('issue_title', 'Unknown')
        return f"{issue_display} - {issue_title}"
    elif submission['submission_type'] == 'PULL_REQUEST':
        pr_num = submission.get('pr_number')
        pr_title = submission.get('pr_title', 'Unknown')
        return f"PR #{pr_num} - {pr_title}"
    
    return "Unknown"


def filter_submissions_by_date(submissions: List[Dict[str, Any]], start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """
    Filter submissions by date range
    
    Args:
        submissions: List of submission dictionaries
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
    
    Returns:
        Filtered list of submissions
    """
    if not start_date and not end_date:
        return submissions
    
    filtered_submissions = []
    
    for submission in submissions:
        submission_date_str = submission.get('submission_date')
        if not submission_date_str:
            continue
            
        try:
            # Parse submission date (handle both ISO format and other formats)
            if 'T' in submission_date_str:
                # ISO format: 2023-12-01T10:30:00Z
                submission_date = datetime.fromisoformat(submission_date_str.replace('Z', '+00:00'))
            else:
                # Simple date format: 2023-12-01
                submission_date = datetime.strptime(submission_date_str, '%Y-%m-%d')
            
            # Check start date filter
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                if submission_date.date() < start_dt.date():
                    continue
            
            # Check end date filter
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                if submission_date.date() > end_dt.date():
                    continue
            
            filtered_submissions.append(submission)
            
        except (ValueError, TypeError) as e:
            # Skip submissions with invalid date formats
            print(f"⚠️  Warning: Invalid date format for submission: {submission_date_str}")
            continue
    
    return filtered_submissions


def get_student_date_ranges(submissions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate date ranges for each student
    
    Args:
        submissions: List of submission dictionaries
    
    Returns:
        Dictionary mapping student names to their date range info
    """
    student_dates = {}
    
    for submission in submissions:
        student = submission.get('student', 'unknown')
        submission_date_str = submission.get('submission_date')
        
        if not submission_date_str:
            continue
            
        try:
            # Parse submission date
            if 'T' in submission_date_str:
                submission_date = datetime.fromisoformat(submission_date_str.replace('Z', '+00:00'))
            else:
                submission_date = datetime.strptime(submission_date_str, '%Y-%m-%d')
            
            if student not in student_dates:
                student_dates[student] = {
                    'earliest': submission_date,
                    'latest': submission_date,
                    'count': 0
                }
            
            student_dates[student]['count'] += 1
            
            if submission_date < student_dates[student]['earliest']:
                student_dates[student]['earliest'] = submission_date
            if submission_date > student_dates[student]['latest']:
                student_dates[student]['latest'] = submission_date
                
        except (ValueError, TypeError):
            continue
    
    return student_dates


def format_submissions(data: Dict[str, Any], start_date: str = None, end_date: str = None):
    """Format and print submissions grouped by project and student"""
    
    # Debug: Print the keys in the response
    print(f"🔍 DEBUG: Response keys: {list(data.keys())}")
    
    # Handle different response formats
    submissions = None
    
    if 'report' in data and 'submissions' in data['report']:
        # All students endpoint: { "success": true, "report": { "submissions": [...] } }
        submissions = data['report']['submissions']
        print(f"📋 Found {len(submissions)} submissions in report.submissions")
    elif 'all_submissions' in data:
        # Single student endpoint: { "success": true, "all_submissions": [...] }
        submissions = data['all_submissions']
        print(f"📋 Found {len(submissions)} submissions in all_submissions")
    elif 'submissions' in data:
        # Direct submissions key
        submissions = data['submissions']
        print(f"📋 Found {len(submissions)} submissions in submissions")
    else:
        print(f"❌ No submissions found in response. Available keys: {list(data.keys())}")
        print(f"📄 Full response structure:")
        import json
        print(json.dumps(data, indent=2)[:500])  # Print first 500 chars
        return
    
    if not submissions:
        print("ℹ️  No submissions found (submissions list is empty)")
        return
    
    # Apply date filtering if specified
    if start_date or end_date:
        original_count = len(submissions)
        submissions = filter_submissions_by_date(submissions, start_date, end_date)
        filtered_count = len(submissions)
        if original_count != filtered_count:
            print(f"📅 Date filtering: {original_count} → {filtered_count} submissions")
    
    print()  # Add blank line after debug info
    
    # Group submissions by project (base repo name) and then by student
    # project_name -> student_name -> [submissions]
    by_project = defaultdict(lambda: defaultdict(list))
    
    for submission in submissions:
        # Use source_repository for forks, otherwise use repository
        repo_full = submission.get('source_repository') or submission.get('repository', 'unknown')
        
        # Extract just the repo name (after the /)
        if '/' in repo_full:
            repo_name = repo_full.split('/')[-1]
        else:
            repo_name = submission.get('repo_name', 'unknown')
        
        student = submission.get('student', 'unknown')
        by_project[repo_name][student].append(submission)
    
    # Print formatted output
    total_submissions = len(submissions)
    total_students = len(set(s.get('student') for s in submissions))
    total_projects = len(by_project)
    
    # Calculate per-student date ranges
    student_date_ranges = get_student_date_ranges(submissions)
    
    print("=" * 80)
    print("📊 STUDENT SUBMISSIONS SUMMARY")
    print("=" * 80)
    print(f"Total Projects: {total_projects}")
    print(f"Total Students: {total_students}")
    print(f"Total Submissions: {total_submissions}")
    print()
    
    # Show per-student date ranges
    if student_date_ranges:
        print("📅 STUDENT DATE RANGES")
        print("-" * 80)
        for student in sorted(student_date_ranges.keys()):
            date_info = student_date_ranges[student]
            earliest = date_info['earliest'].strftime('%Y-%m-%d')
            latest = date_info['latest'].strftime('%Y-%m-%d')
            count = date_info['count']
            
            if earliest == latest:
                print(f"👤 {student}: {earliest} ({count} submission{'s' if count != 1 else ''})")
            else:
                print(f"👤 {student}: {earliest} to {latest} ({count} submission{'s' if count != 1 else ''})")
        print()
    
    # Sort projects alphabetically
    for project_name in sorted(by_project.keys()):
        print("=" * 80)
        print(f"📦 Project: {project_name}")
        print("=" * 80)
        
        students = by_project[project_name]
        
        # Sort students alphabetically
        for student_name in sorted(students.keys()):
            print(f"\n👤 Student: {student_name}")
            print("-" * 80)
            
            student_submissions = students[student_name]
            # Sort submissions by date
            student_submissions.sort(key=lambda x: x.get('submission_date', ''))
            
            for idx, submission in enumerate(student_submissions, 1):
                title = get_submission_title(submission)
                location = get_submission_location(submission)
                url = get_submission_url(submission)
                status = "✅ VALID" if submission.get('is_valid') else "❌ INVALID"
                date = submission.get('submission_date', 'N/A')
                
                print(f"{idx}. {title}")
                print(f"   Repository: {submission.get('repository', 'N/A')}")
                print(f"   Location: {location}")
                print(f"   Status: {status}")
                print(f"   Date: {date}")
                print(f"   URL: {url}")
                
                # Show validity reasons if invalid
                if not submission.get('is_valid'):
                    reasons = submission.get('validity_reasons', [])
                    if reasons:
                        print(f"   ⚠️  Reasons: {', '.join(reasons)}")
                
                # Show addressed issues if available
                addressed = submission.get('addressed_issues', [])
                if addressed:
                    print(f"   🎯 Addresses: {', '.join(addressed)}")
                
                print()
        
        print()
    
    print("=" * 80)


def show_usage_guide():
    """Show helpful usage guide when base URL is not provided"""
    print("=" * 80)
    print("📚 Student Submissions Formatter - Usage Guide")
    print("=" * 80)
    print()
    print("This script fetches and formats student submissions from the API.")
    print()
    print("📊 Features:")
    print("  • Date filtering with --start-date and --end-date")
    print("  • Per-student date range summaries")
    print("  • Individual submission details with dates")
    print()
    print("⚠️  Required: You must specify --base-url")
    print()
    print("Common Examples:")
    print("-" * 80)
    print()
    print("1. Fetch a specific student from production:")
    print("   python format_submissions.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --student jellyfishing2346 \\")
    print("       --master-repo-owner codepath")
    print()
    print("2. Fetch all students from localhost:")
    print("   python format_submissions.py \\")
    print("       --base-url http://localhost:3000 \\")
    print("       --master-repo-owner codepath")
    print()
    print("3. Fetch from a different master repo owner:")
    print("   python format_submissions.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --master-repo-owner zenocross")
    print()
    print("4. Fetch submissions within a date range:")
    print("   python format_submissions.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --start-date 2023-12-01 \\")
    print("       --end-date 2023-12-31 \\")
    print("       --master-repo-owner codepath")
    print()
    print("5. Fetch submissions for a specific student within date range:")
    print("   python format_submissions.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --student jellyfishing2346 \\")
    print("       --start-date 2023-12-01 \\")
    print("       --end-date 2023-12-31 \\")
    print("       --master-repo-owner codepath")
    print()
    print("=" * 80)
    print()
    print("For more help, use: python format_submissions.py --help")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Format student submissions from the API endpoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch specific student from production
  python format_submissions.py --base-url https://www.zenocross.com --student jellyfishing2346 --master-repo-owner codepath
  
  # Fetch all students from localhost
  python format_submissions.py --base-url http://localhost:3000 --master-repo-owner codepath
  
  # Fetch from different master repo owner
  python format_submissions.py --base-url https://www.zenocross.com --master-repo-owner zenocross
  
  # Fetch submissions within date range
  python format_submissions.py --base-url https://www.zenocross.com --start-date 2023-12-01 --end-date 2023-12-31 --master-repo-owner codepath
  
  # Fetch specific student within date range
  python format_submissions.py --base-url https://www.zenocross.com --student jellyfishing2346 --start-date 2023-12-01 --end-date 2023-12-31 --master-repo-owner codepath
        """,
        add_help=True
    )
    
    parser.add_argument(
        '--base-url',
        help='Base URL of the API (REQUIRED - e.g., https://www.zenocross.com or http://localhost:3000)'
    )
    
    parser.add_argument(
        '--student',
        help='Specific student username (optional, fetches all if not provided)'
    )
    
    parser.add_argument(
        '--master-repo-owner',
        default='codepath',
        help='Master repository owner (default: codepath)'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date filter in YYYY-MM-DD format (optional)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date filter in YYYY-MM-DD format (optional)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if base URL is provided
    if not args.base_url:
        show_usage_guide()
        sys.exit(1)
    
    # Fetch submissions from API
    data = fetch_submissions(
        base_url=args.base_url,
        student=args.student,
        master_repo_owner=args.master_repo_owner,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # Check for API errors
    if not data.get('success', True):
        print(f"❌ API returned error: {data.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Format and display
    format_submissions(data, args.start_date, args.end_date)


if __name__ == '__main__':
    main()