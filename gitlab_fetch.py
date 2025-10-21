#!/usr/bin/env python3
"""
GitLab Student Submissions Formatter
Fetches and formats student submissions directly from GitLab API
Works standalone without any backend - pure GitLab API calls
"""

import sys
import requests
import argparse
import re
from collections import defaultdict
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus
from datetime import datetime


class GitLabAPI:
    """GitLab API client"""
    
    def __init__(self, base_url: str = "https://gitlab.com", token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v4"
        self.session = requests.Session()
        
        if token:
            self.session.headers['PRIVATE-TOKEN'] = token
    
    def _get(self, endpoint: str, params: Dict = None) -> List[Dict]:
        """Make a GET request and handle pagination"""
        url = f"{self.api_base}/{endpoint}"
        all_results = []
        page = 1
        
        if params is None:
            params = {}
        
        params['per_page'] = 100
        
        while True:
            params['page'] = page
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                results = response.json()
                
                if not results:
                    break
                
                all_results.extend(results)
                
                # Check if there are more pages
                if 'x-next-page' not in response.headers or not response.headers['x-next-page']:
                    break
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching {url}: {e}")
                break
        
        return all_results
    
    def get_project_by_path(self, project_path: str) -> Optional[Dict]:
        """Get project details by path"""
        encoded_path = quote_plus(project_path)
        url = f"{self.api_base}/projects/{encoded_path}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching project: {e}")
            return None
    
    def get_project_forks(self, project_path: str) -> List[Dict]:
        """Get all forks of a project"""
        encoded_path = quote_plus(project_path)
        return self._get(f"projects/{encoded_path}/forks")
    
    def get_project_issues(self, project_id: int) -> List[Dict]:
        """Get all issues for a project"""
        return self._get(f"projects/{project_id}/issues")
    
    def get_issue_notes(self, project_id: int, issue_iid: int) -> List[Dict]:
        """Get all notes (comments) for an issue"""
        return self._get(f"projects/{project_id}/issues/{issue_iid}/notes")
    
    def get_merge_requests(self, project_id: int) -> List[Dict]:
        """Get merge requests within the same project (self-merges)"""
        params = {'target_project_id': project_id}
        return self._get(f"projects/{project_id}/merge_requests", params)


def has_media_attachments(text: str) -> tuple[bool, List[str]]:
    """
    Check if text contains image or video attachments
    Returns: (has_media, list_of_media_urls)
    """
    if not text:
        return False, []
    
    media_urls = []
    
    # Pattern for markdown images: ![alt](url) or ![alt](/uploads/path)
    markdown_pattern = r'!\[.*?\]\((.*?)\)'
    matches = re.findall(markdown_pattern, text)
    media_urls.extend(matches)
    
    # Pattern for direct URLs to images/videos
    url_pattern = r'https?://[^\s<>"]+?\.(?:png|jpg|jpeg|gif|mp4|mov|webm|avi)'
    matches = re.findall(url_pattern, text, re.IGNORECASE)
    media_urls.extend(matches)
    
    # Pattern for /uploads/ paths (GitLab internal uploads)
    upload_pattern = r'/uploads/[^\s<>")\]]+?\.(?:png|jpg|jpeg|gif|mp4|mov|webm|avi)'
    matches = re.findall(upload_pattern, text, re.IGNORECASE)
    media_urls.extend(matches)
    
    return len(media_urls) > 0, media_urls


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


def fetch_submissions(gitlab_url: str, master_project: str, student: str = None, token: str = None, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    """
    Fetch submissions directly from GitLab API
    
    Args:
        gitlab_url: GitLab instance URL (e.g., https://gitlab.com)
        master_project: Master project path (e.g., codepath-org/gitlab)
        student: Optional student username (if None, fetches all students)
        token: GitLab Personal Access Token
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
    
    Returns:
        Dictionary with submissions data
    """
    print(f"🔍 Fetching submissions from GitLab")
    print(f"   GitLab URL: {gitlab_url}")
    print(f"   Master Project: {master_project}")
    if student:
        print(f"   Student: {student}")
    if start_date:
        print(f"   Start date: {start_date}")
    if end_date:
        print(f"   End date: {end_date}")
    print()
    
    # Initialize API
    api = GitLabAPI(base_url=gitlab_url, token=token)
    
    # Verify master project exists
    master_project_data = api.get_project_by_path(master_project)
    if not master_project_data:
        print(f"❌ Master project {master_project} not found")
        sys.exit(1)
    
    # Get repository name from path
    repo_name = master_project.split('/')[-1]
    
    # Get all forks
    print(f"📦 Fetching forks...")
    forks = api.get_project_forks(master_project)
    
    if not forks:
        print(f"⚠️  No forks found for {master_project}")
        return {
            'success': True,
            'report': {
                'submissions': []
            }
        }
    
    print(f"   Found {len(forks)} forks")
    print()
    
    # Filter for specific student if requested
    if student:
        forks = [f for f in forks if f['owner']['username'].lower() == student.lower()]
        if not forks:
            print(f"⚠️  No fork found for student {student}")
            return {
                'success': True,
                'all_submissions': []
            }
    
    # Extract submissions from each fork
    all_submissions = []
    
    for idx, fork in enumerate(forks, 1):
        fork_owner = fork['owner']['username']
        fork_path = fork['path_with_namespace']
        fork_id = fork['id']
        
        print(f"[{idx}/{len(forks)}] Processing fork: {fork_path}")
        
        # Check issues and comments for media attachments
        issues = api.get_project_issues(fork_id)
        print(f"   📋 Found {len(issues)} issues")
        
        for issue in issues:
            # Check issue description for media
            desc_has_media, desc_media = has_media_attachments(issue.get('description', ''))
            
            if desc_has_media:
                all_submissions.append({
                    'student': fork_owner,
                    'repository': fork_path,
                    'repo_name': repo_name,
                    'owner_name': fork_owner,
                    'source_repository': fork_path,
                    'submission_type': 'COMMENT',  # Treat as comment for consistency
                    'submission_date': issue['created_at'],
                    'issue_number': issue['iid'],
                    'issue_title': issue['title'],
                    'issue_display': f"#{issue['iid']}",
                    'comment_id': 'description',
                    'is_valid': True,
                    'validity_reasons': [],
                    'repo_type': 'student_fork',
                    'is_codepath_submission': False,
                    'addressed_issues': []
                })
            
            # Check issue comments
            notes = api.get_issue_notes(fork_id, issue['iid'])
            
            for note in notes:
                if note.get('system'):  # Skip system notes
                    continue
                
                has_media, media_urls = has_media_attachments(note.get('body', ''))
                
                if has_media:
                    all_submissions.append({
                        'student': fork_owner,
                        'repository': fork_path,
                        'repo_name': repo_name,
                        'owner_name': fork_owner,
                        'source_repository': fork_path,
                        'submission_type': 'COMMENT',
                        'submission_date': note['created_at'],
                        'issue_number': issue['iid'],
                        'issue_title': issue['title'],
                        'issue_display': f"#{issue['iid']}",
                        'comment_id': note['id'],
                        'is_valid': True,
                        'validity_reasons': [],
                        'repo_type': 'student_fork',
                        'is_codepath_submission': False,
                        'addressed_issues': []
                    })
        
        # Check for merge requests within the fork itself
        merge_requests = api.get_merge_requests(fork_id)
        self_mrs = [mr for mr in merge_requests 
                    if mr['source_project_id'] == mr['target_project_id']]
        
        print(f"   🔀 Found {len(self_mrs)} self-merge requests")
        
        for mr in self_mrs:
            all_submissions.append({
                'student': fork_owner,
                'repository': fork_path,
                'repo_name': repo_name,
                'owner_name': fork_owner,
                'source_repository': fork_path,
                'submission_type': 'PULL_REQUEST',
                'submission_date': mr['created_at'],
                'pr_number': mr['iid'],
                'pr_title': mr['title'],
                'is_valid': True,
                'validity_reasons': [],
                'repo_type': 'student_fork',
                'is_codepath_submission': False,
                'addressed_issues': []
            })
        
        print()
    
    # Apply date filtering if specified
    if start_date or end_date:
        original_count = len(all_submissions)
        all_submissions = filter_submissions_by_date(all_submissions, start_date, end_date)
        filtered_count = len(all_submissions)
        if original_count != filtered_count:
            print(f"📅 Date filtering: {original_count} → {filtered_count} submissions")
    
    # Return in format matching original GitHub API
    if student:
        return {
            'success': True,
            'all_submissions': all_submissions
        }
    else:
        return {
            'success': True,
            'report': {
                'submissions': all_submissions
            }
        }


def get_submission_location(submission: Dict[str, Any]) -> str:
    """Determine where the submission was made"""
    if submission.get('is_codepath_submission'):
        return "master repo"
    
    repo_type = submission.get('repo_type', 'unknown')
    if repo_type == 'student_fork':
        return "own fork"
    elif repo_type == 'codepath_repo':
        return "master repo"
    else:
        return "other"


def get_submission_url(submission: Dict[str, Any]) -> str:
    """Generate GitLab URL for the submission"""
    owner = submission.get('owner_name')
    repo = submission.get('repo_name')
    repository = submission.get('repository')
    
    if submission['submission_type'] == 'COMMENT':
        issue_num = submission.get('issue_number')
        comment_id = submission.get('comment_id')
        if comment_id == 'description':
            return f"https://gitlab.com/{repository}/-/issues/{issue_num}"
        return f"https://gitlab.com/{repository}/-/issues/{issue_num}#note_{comment_id}"
    elif submission['submission_type'] == 'PULL_REQUEST':
        pr_num = submission.get('pr_number')
        return f"https://gitlab.com/{repository}/-/merge_requests/{pr_num}"
    
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
        return f"MR !{pr_num} - {pr_title}"
    
    return "Unknown"


def format_submissions(data: Dict[str, Any]):
    """Format and print submissions grouped by project and student"""
    
    # Handle different response formats
    submissions = None
    
    if 'report' in data and 'submissions' in data['report']:
        submissions = data['report']['submissions']
    elif 'all_submissions' in data:
        submissions = data['all_submissions']
    elif 'submissions' in data:
        submissions = data['submissions']
    else:
        print(f"❌ No submissions found in response")
        return
    
    if not submissions:
        print("ℹ️  No submissions found (submissions list is empty)")
        return
    
    print()
    
    # Group submissions by project (base repo name) and then by student
    by_project = defaultdict(lambda: defaultdict(list))
    
    for submission in submissions:
        repo_full = submission.get('source_repository') or submission.get('repository', 'unknown')
        
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
    print("📊 GITLAB STUDENT SUBMISSIONS SUMMARY")
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
                
                if not submission.get('is_valid'):
                    reasons = submission.get('validity_reasons', [])
                    if reasons:
                        print(f"   ⚠️  Reasons: {', '.join(reasons)}")
                
                addressed = submission.get('addressed_issues', [])
                if addressed:
                    print(f"   🎯 Addresses: {', '.join(addressed)}")
                
                print()
        
        print()
    
    print("=" * 80)


def show_usage_guide():
    """Show helpful usage guide"""
    print("=" * 80)
    print("📚 GitLab Student Submissions Formatter - Usage Guide")
    print("=" * 80)
    print()
    print("This script fetches and formats student submissions directly from GitLab.")
    print()
    print("📊 Features:")
    print("  • Date filtering with --start-date and --end-date")
    print("  • Per-student date range summaries")
    print("  • Individual submission details with dates")
    print()
    print("⚠️  Required: You must specify --master-project")
    print("💡 Recommended: Provide --token for higher rate limits")
    print()
    print("Common Examples:")
    print("-" * 80)
    print()
    print("1. Fetch all students from a project:")
    print("   python gitlab_format_submissions.py \\")
    print("       --master-project codepath-org/gitlab \\")
    print("       --token glpat-xxxxxxxxxxxxxxxxxxxx")
    print()
    print("2. Fetch a specific student:")
    print("   python gitlab_format_submissions.py \\")
    print("       --master-project codepath-org/gitlab \\")
    print("       --student zenocross \\")
    print("       --token glpat-xxxxxxxxxxxxxxxxxxxx")
    print()
    print("3. Use self-hosted GitLab:")
    print("   python gitlab_format_submissions.py \\")
    print("       --gitlab-url https://gitlab.mycompany.com \\")
    print("       --master-project myorg/myproject \\")
    print("       --token glpat-xxxxxxxxxxxxxxxxxxxx")
    print()
    print("4. Fetch submissions within a date range:")
    print("   python gitlab_format_submissions.py \\")
    print("       --master-project codepath-org/gitlab \\")
    print("       --start-date 2023-12-01 \\")
    print("       --end-date 2023-12-31 \\")
    print("       --token glpat-xxxxxxxxxxxxxxxxxxxx")
    print()
    print("5. Fetch submissions for a specific student within date range:")
    print("   python gitlab_format_submissions.py \\")
    print("       --master-project codepath-org/gitlab \\")
    print("       --student zenocross \\")
    print("       --start-date 2023-12-01 \\")
    print("       --end-date 2023-12-31 \\")
    print("       --token glpat-xxxxxxxxxxxxxxxxxxxx")
    print()
    print("=" * 80)
    print()
    print("To get a GitLab token:")
    print("  1. Go to GitLab → Settings → Access Tokens")
    print("  2. Create token with 'read_api' scope")
    print("  3. Copy the token and use with --token")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Format student submissions from GitLab (standalone, no backend)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all students
  python gitlab_format_submissions.py --master-project codepath-org/gitlab --token glpat-xxxxx
  
  # Fetch specific student
  python gitlab_format_submissions.py --master-project codepath-org/gitlab --student zenocross --token glpat-xxxxx
  
  # Use self-hosted GitLab
  python gitlab_format_submissions.py --gitlab-url https://gitlab.company.com --master-project myorg/proj --token glpat-xxxxx
  
  # Fetch submissions within date range
  python gitlab_format_submissions.py --master-project codepath-org/gitlab --start-date 2023-12-01 --end-date 2023-12-31 --token glpat-xxxxx
  
  # Fetch specific student within date range
  python gitlab_format_submissions.py --master-project codepath-org/gitlab --student zenocross --start-date 2023-12-01 --end-date 2023-12-31 --token glpat-xxxxx
        """
    )
    
    parser.add_argument(
        '--master-project',
        help='Master project path (REQUIRED - e.g., codepath-org/gitlab)'
    )
    
    parser.add_argument(
        '--student',
        help='Specific student username (optional, fetches all if not provided)'
    )
    
    parser.add_argument(
        '--token',
        help='GitLab Personal Access Token (recommended)'
    )
    
    parser.add_argument(
        '--gitlab-url',
        default='https://gitlab.com',
        help='GitLab instance URL (default: https://gitlab.com)'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date filter in YYYY-MM-DD format (optional)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date filter in YYYY-MM-DD format (optional)'
    )
    
    args = parser.parse_args()
    
    # Check if master project is provided
    if not args.master_project:
        show_usage_guide()
        sys.exit(1)
    
    # Fetch submissions directly from GitLab API
    data = fetch_submissions(
        gitlab_url=args.gitlab_url,
        master_project=args.master_project,
        student=args.student,
        token=args.token,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # Check for errors
    if not data.get('success', True):
        print(f"❌ Error: {data.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Format and display
    format_submissions(data)


if __name__ == '__main__':
    main()