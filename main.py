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


def fetch_submissions(base_url: str, student: str = None, master_repo_owner: str = "codepath", 
                      start_date: str = None, end_date: str = None, ignore_invalids: bool = False,
                      providers: List[str] = None, include_master_submissions: bool = False,
                      report_owner_submissions: bool = False, include_closed: bool = False,
                      github_token: str = None, gitlab_token: str = None,
                      repository: str = None) -> Dict[str, Any]:
    """
    Fetch submissions from the API endpoint
    
    Args:
        base_url: Base URL of the API (e.g., http://localhost:3000)
        student: Optional student username (if None, fetches all students)
        master_repo_owner: Master repo owner (default: codepath)
        start_date: Optional start date filter (YYYY-MM-DD or ISO format)
        end_date: Optional end date filter (YYYY-MM-DD or ISO format)
        ignore_invalids: Ignore/exclude invalid submissions (default: False, includes invalid)
        providers: List of provider types to filter by (e.g., ['github', 'gitlab'])
        include_master_submissions: Fetch submissions from owner/master repositories via API (default: False)
        report_owner_submissions: Include list of users who made submissions to owner/master repos (default: False)
        include_closed: Include closed issues and pull requests (default: False)
        github_token: GitHub API token (overrides env var)
        gitlab_token: GitLab API token (overrides env var)
        repository: Filter by specific repository (full path like 'codepath/ios101-prework')
    
    Returns:
        API response as dictionary
    """
    if student:
        url = f"{base_url}/admin/fetch-student-submission/{student}"
    else:
        url = f"{base_url}/admin/fetch-student-submissions"
    
    params = {'master_repo_owner': master_repo_owner}
    
    # Add ignore_invalids parameter (now matches parameter name)
    params['ignore_invalids'] = 'true' if ignore_invalids else 'false'
    
    # Add include_master_submissions parameter
    params['include_master_submissions'] = 'true' if include_master_submissions else 'false'
    
    # Add report_owner_submissions parameter
    params['report_owner_submissions'] = 'true' if report_owner_submissions else 'false'
    
    # Add include_closed parameter
    params['include_closed'] = 'true' if include_closed else 'false'
    
    # Add API tokens if provided
    if github_token:
        params['github_token'] = github_token
    if gitlab_token:
        params['gitlab_token'] = gitlab_token
    
    # Add repository filter if provided
    if repository:
        params['repository'] = repository
    
    # Add date filters to params if provided (backend will handle filtering)
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    
    # Add provider filters if specified
    if providers:
        # Backend accepts comma-separated or multiple provider params
        params['providers'] = ','.join(providers)
    
    # Add student filter if specified
    if student:
        params['student'] = student
    
    print(f"🔍 Fetching submissions from: {url}")
    print(f"   Master repo owner: {master_repo_owner}")
    if student:
        print(f"   Student: {student}")
    if start_date:
        print(f"   Start date: {start_date}")
    if end_date:
        print(f"   End date: {end_date}")
    if providers:
        print(f"   Providers: {', '.join(providers)}")
    if include_master_submissions:
        print(f"   Include master submissions: enabled")
    if report_owner_submissions:
        print(f"   Report owner submissions: enabled")
    if include_closed:
        print(f"   Include closed: enabled")
    if ignore_invalids:
        print(f"   Ignore invalids: enabled")
    if github_token:
        print(f"   GitHub token: provided")
    if gitlab_token:
        print(f"   GitLab token: provided")
    if repository:
        print(f"   Repository: {repository}")
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


def format_submission_date(date_str: str) -> str:
    """
    Format submission date to a consistent, readable format
    Converts ISO format (2025-11-27T23:33:11+00:00) or RFC 2822 format to a standard format
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Formatted date string (e.g., "Mon, 24 Nov 2025 12:24:46 GMT")
    """
    if not date_str or date_str == 'N/A':
        return 'N/A'
    
    try:
        # Try parsing as ISO format first
        if 'T' in date_str:
            # ISO format: 2025-11-27T23:33:11+00:00
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Try RFC 2822 format: Mon, 24 Nov 2025 12:24:46 GMT
            from email.utils import parsedate_to_datetime
            date_obj = parsedate_to_datetime(date_str)
        
        # Format to RFC 2822 format (like email dates)
        from email.utils import format_datetime
        return format_datetime(date_obj)
    except Exception:
        # If parsing fails, return original
        return date_str


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


def save_owner_submission_users(data: Dict[str, Any], filename: str = "master_submissions.txt"):
    """
    Save list of users who made submissions to owner/master repositories to a text file
    Format: username,provider (e.g., chandanshyam,github)
    
    Args:
        data: API response data
        filename: Output filename (default: master_submissions.txt)
    """
    # Extract owner submission users from the response
    owner_submission_users = None
    
    if 'report' in data and 'owner_submission_users' in data['report']:
        owner_submission_users = data['report']['owner_submission_users']
    elif 'owner_submission_users' in data:
        owner_submission_users = data['owner_submission_users']
    
    if not owner_submission_users:
        print("ℹ️  No owner submission users data found in response")
        return
    
    try:
        with open(filename, 'w') as f:
            # Check if the data includes provider information
            if owner_submission_users and isinstance(owner_submission_users[0], dict):
                # Format: [{"username": "user1", "provider": "github"}, ...]
                for entry in sorted(owner_submission_users, key=lambda x: (x.get('username', ''), x.get('provider', ''))):
                    username = entry.get('username', 'unknown')
                    provider = entry.get('provider', 'unknown')
                    f.write(f"{username},{provider}\n")
            else:
                # Legacy format: ["user1", "user2", ...] - assume github
                for user in sorted(owner_submission_users):
                    f.write(f"{user},github\n")
        
        print(f"✅ Saved {len(owner_submission_users)} owner submission users to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving owner submission users to file: {e}")
        return False


def read_master_submissions_file(filename: str = "master_submissions.txt") -> List[tuple]:
    """
    Read master_submissions.txt and return list of (username, provider) tuples
    
    Args:
        filename: Input filename (default: master_submissions.txt)
    
    Returns:
        List of (username, provider) tuples
    """
    users = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                if len(parts) >= 2:
                    username = parts[0].strip()
                    provider = parts[1].strip()
                    users.append((username, provider))
                elif len(parts) == 1:
                    # Legacy format without provider
                    username = parts[0].strip()
                    users.append((username, 'github'))
        
        return users
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return []
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return []


def process_master_submissions_batch(base_url: str, master_repo_owner: str, filename: str = "master_submissions.txt",
                                     start_date: str = None, end_date: str = None, ignore_invalids: bool = False,
                                     include_master_submissions: bool = False, include_closed: bool = False,
                                     github_token: str = None, gitlab_token: str = None,
                                     repository: str = None):
    """
    Process each user in master_submissions.txt file
    
    Args:
        base_url: Base URL of the API
        master_repo_owner: Master repo owner
        filename: Input filename with user list
        start_date: Optional start date filter
        end_date: Optional end date filter
        ignore_invalids: Ignore/exclude invalid submissions
        include_master_submissions: Fetch submissions from master repos
        include_closed: Include closed issues and pull requests
        github_token: GitHub API token
        gitlab_token: GitLab API token
        repository: Filter by specific repository (full path like 'codepath/ios101-prework')
    """
    users = read_master_submissions_file(filename)
    
    if not users:
        print(f"⚠️  No users found in {filename}")
        return
    
    print(f"\n{'='*80}")
    print(f"📋 Processing {len(users)} users from {filename}")
    print(f"{'='*80}\n")
    
    for idx, (username, provider) in enumerate(users, 1):
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(users)}] Processing: {username} ({provider})")
        print(f"{'='*80}\n")
        
        try:
            # Fetch submissions for this specific user and provider
            data = fetch_submissions(
                base_url=base_url,
                student=username,
                master_repo_owner=master_repo_owner,
                start_date=start_date,
                end_date=end_date,
                ignore_invalids=ignore_invalids,
                providers=[provider],
                include_master_submissions=include_master_submissions,
                report_owner_submissions=False,  # Don't generate new master_submissions.txt for each user
                include_closed=include_closed,
                github_token=github_token,
                gitlab_token=gitlab_token,
                repository=repository
            )
            
            # Check for API errors
            if not data.get('success', True):
                print(f"❌ API returned error for {username}: {data.get('error', 'Unknown error')}")
                continue
            
            # Format and display
            format_submissions(data)
            
        except Exception as e:
            print(f"❌ Error processing {username}: {e}")
            continue
    
    print(f"\n{'='*80}")
    print(f"✅ Completed processing {len(users)} users")
    print(f"{'='*80}\n")


def format_submissions(data: Dict[str, Any]):
    """Format and print submissions grouped by project and student"""
    
    # Debug: Print the keys in the response
    print(f"🔍 DEBUG: Response keys: {list(data.keys())}")
    
    # Check if owner submission users data is available and save to file FIRST
    # (before checking for submissions, in case there are no submissions but we have owner users)
    if 'report' in data and 'owner_submission_users' in data['report']:
        save_owner_submission_users(data)
    elif 'owner_submission_users' in data:
        save_owner_submission_users(data)
    
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
        print(f"ℹ️  No submissions found in response. Available keys: {list(data.keys())}")
        # Don't print the full response structure if we successfully saved owner submission users
        has_owner_users = ('report' in data and 'owner_submission_users' in data['report']) or 'owner_submission_users' in data
        if not has_owner_users:
            print(f"📄 Full response structure:")
            import json
            print(json.dumps(data, indent=2)[:500])  # Print first 500 chars
        return
    
    if not submissions:
        print("ℹ️  No submissions found (submissions list is empty)")
        return
    
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
                date = format_submission_date(submission.get('submission_date', 'N/A'))
                
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
    print("  • Provider filtering (GitHub/GitLab) with --providers")
    print("  • Repository/project filtering with --repository (e.g., codepath/ios101-prework)")
    print("  • Include/exclude invalid submissions")
    print("  • Fetch submissions from master repos (codepath/puter) with --include-master-submissions")
    print("  • Save owner submission users to master_submissions.txt with --report-owner-submissions")
    print("  • Batch process each user with interactive prompt or --batch-process flag")
    print("  • Per-student date range summaries")
    print("  • Individual submission details with dates")
    print()
    print("⚠️  Required: You must specify --base-url")
    print()
    print("Common Examples:")
    print("-" * 80)
    print()
    print("1. Fetch a specific student from production:")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --student jellyfishing2346 \\")
    print("       --master-repo-owner codepath")
    print()
    print("2. Fetch all students with master repo submissions (GitHub PRs to codepath/puter):")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --master-repo-owner codepath \\")
    print("       --include-master-submissions")
    print()
    print("3. Fetch submissions within a date range:")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --start-date 2023-12-01 \\")
    print("       --end-date 2023-12-31 \\")
    print("       --master-repo-owner codepath")
    print()
    print("4. Filter by provider (GitHub only):")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --providers github \\")
    print("       --master-repo-owner codepath")
    print()
    print("5. Exclude invalid submissions:")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --exclude-invalid \\")
    print("       --master-repo-owner codepath")
    print()
    print("6. Filter by specific repository/project:")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --repository codepath/ios101-prework \\")
    print("       --master-repo-owner codepath")
    print()
    print("7. Generate list of users who submitted to master repos and process them:")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --master-repo-owner codepath \\")
    print("       --include-master-submissions \\")
    print("       --report-owner-submissions")
    print("   (Creates master_submissions.txt, then prompts to process each user)")
    print()
    print("8. Batch process without prompting:")
    print("   python main.py \\")
    print("       --base-url https://www.zenocross.com \\")
    print("       --master-repo-owner codepath \\")
    print("       --report-owner-submissions \\")
    print("       --batch-process")
    print()
    print("=" * 80)
    print()
    print("For more help, use: python main.py --help")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Format student submissions from the API endpoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch specific student from production
  python main.py --base-url https://www.zenocross.com --student jellyfishing2346 --master-repo-owner codepath
  
  # Fetch all students with master repo submissions (GitHub PRs to codepath/puter)
  python main.py --base-url https://www.zenocross.com --master-repo-owner codepath --include-master-submissions
  
  # Fetch from different master repo owner
  python main.py --base-url https://www.zenocross.com --master-repo-owner zenocross
  
  # Fetch submissions within date range
  python main.py --base-url https://www.zenocross.com --start-date 2023-12-01 --end-date 2023-12-31 --master-repo-owner codepath
  
  # Filter by GitHub only and exclude invalid
  python main.py --base-url https://www.zenocross.com --providers github --exclude-invalid --master-repo-owner codepath
  
  # Filter by specific repository/project
  python main.py --base-url https://www.zenocross.com --repository codepath/ios101-prework --master-repo-owner codepath
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
        help='Start date filter in YYYY-MM-DD or ISO format (optional)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date filter in YYYY-MM-DD or ISO format (optional)'
    )
    
    parser.add_argument(
        '--ignore-invalids',
        action='store_true',
        dest='ignore_invalids',
        help='Ignore/exclude invalid submissions (default: false, includes invalid)'
    )
    
    parser.add_argument(
        '--providers',
        nargs='+',
        choices=['github', 'gitlab'],
        help='Filter by provider type(s) (e.g., --providers github gitlab)'
    )
    
    parser.add_argument(
        '--include-master-submissions',
        action='store_true',
        dest='include_master_submissions',
        help='Fetch submissions from master/owner repositories via API (GitHub PRs to codepath/puter, etc.)'
    )
    
    parser.add_argument(
        '--report-owner-submissions',
        action='store_true',
        help='Include a list of all users who made submissions to owner/master repositories at the bottom of the report'
    )
    
    parser.add_argument(
        '--batch-process',
        action='store_true',
        help='Automatically process each user from master_submissions.txt without prompting'
    )
    
    parser.add_argument(
        '--include-closed',
        action='store_true',
        help='Include closed issues and pull requests (default: false, only open issues/PRs)'
    )
    
    parser.add_argument(
        '--github-token',
        help='GitHub API token (overrides GITHUB_TOKEN environment variable)'
    )
    
    parser.add_argument(
        '--gitlab-token',
        help='GitLab API token (overrides GITLAB_TOKEN environment variable)'
    )
    
    parser.add_argument(
        '--repository',
        help='Filter by specific repository (full path like "codepath/ios101-prework")'
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
        end_date=args.end_date,
        ignore_invalids=args.ignore_invalids,
        providers=args.providers,
        include_master_submissions=args.include_master_submissions,
        report_owner_submissions=args.report_owner_submissions,
        include_closed=args.include_closed,
        github_token=args.github_token,
        gitlab_token=args.gitlab_token,
        repository=args.repository
    )
    
    # Check for API errors
    if not data.get('success', True):
        print(f"❌ API returned error: {data.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Format and display (date filtering now done by backend)
    format_submissions(data)
    
    # Check if master_submissions.txt was created and prompt for batch processing
    import os
    if args.report_owner_submissions and os.path.exists('master_submissions.txt'):
        # Check if file has content
        users = read_master_submissions_file('master_submissions.txt')
        
        if users:
            should_process = args.batch_process
            
            if not args.batch_process:
                # Prompt user
                print(f"\n{'='*80}")
                print(f"📋 Found {len(users)} users in master_submissions.txt")
                print(f"{'='*80}")
                response = input("\nDo you want to process each user individually? (yes/no): ").strip().lower()
                should_process = response in ['yes', 'y']
            
            if should_process:
                # When processing users from master_submissions.txt, always include master submissions
                # since these users were identified as having submitted to master repos
                process_master_submissions_batch(
                    base_url=args.base_url,
                    master_repo_owner=args.master_repo_owner,
                    filename='master_submissions.txt',
                    start_date=args.start_date,
                    end_date=args.end_date,
                    ignore_invalids=args.ignore_invalids,
                    include_master_submissions=True,  # Always True for batch processing
                    include_closed=args.include_closed,
                    github_token=args.github_token,
                    gitlab_token=args.gitlab_token,
                    repository=args.repository
                )
            else:
                print("\n✅ Skipping batch processing. You can process users later by running with --batch-process flag.")
        else:
            print("\n⚠️  master_submissions.txt is empty, nothing to process.")


if __name__ == '__main__':
    main()