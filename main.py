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


def fetch_submissions(base_url: str, student: str = None, master_repo_owner: str = "codepath") -> Dict[str, Any]:
    """
    Fetch submissions from the API endpoint
    
    Args:
        base_url: Base URL of the API (e.g., http://localhost:3000)
        student: Optional student username (if None, fetches all students)
        master_repo_owner: Master repo owner (default: codepath)
    
    Returns:
        API response as dictionary
    """
    if student:
        url = f"{base_url}/admin/fetch-student-submission/{student}"
    else:
        url = f"{base_url}/admin/fetch-student-submissions"
    
    params = {'master_repo_owner': master_repo_owner}
    
    print(f"🔍 Fetching submissions from: {url}")
    print(f"   Master repo owner: {master_repo_owner}")
    if student:
        print(f"   Student: {student}")
    print()
    
    try:
        response = requests.get(url, params=params, timeout=60)
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


def format_submissions(data: Dict[str, Any]):
    """Format and print submissions grouped by project and student"""
    
    # Handle different response formats
    # All students endpoint: { "success": true, "report": { "submissions": [...] } }
    # Single student endpoint: { "success": true, "all_submissions": [...] }
    if 'report' in data:
        # All students endpoint
        submissions = data['report'].get('submissions', [])
    elif 'all_submissions' in data:
        # Single student endpoint
        submissions = data['all_submissions']
    elif 'submissions' in data:
        # Direct submissions key
        submissions = data['submissions']
    else:
        print("❌ No submissions found in response")
        return
    
    if not submissions:
        print("ℹ️  No submissions found")
        return
    
    # Group submissions by project (base repo name) and then by student
    # project_name -> student_name -> [submissions]
    by_project = defaultdict(lambda: defaultdict(list))
    
    for submission in submissions:
        repo_name = submission.get('repo_name', 'unknown')
        student = submission.get('student', 'unknown')
        by_project[repo_name][student].append(submission)
    
    # Print formatted output
    total_submissions = len(submissions)
    total_students = len(set(s.get('student') for s in submissions))
    total_projects = len(by_project)
    
    print("=" * 80)
    print("📊 STUDENT SUBMISSIONS SUMMARY")
    print("=" * 80)
    print(f"Total Projects: {total_projects}")
    print(f"Total Students: {total_students}")
    print(f"Total Submissions: {total_submissions}")
    print()
    
    # Sort projects alphabetically
    for project_name in sorted(by_project.keys()):
        print("=" * 80)
        print(f"Project: {project_name}")
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
                
                print(f"{idx}. {title}")
                print(f"   Location: {location}")
                print(f"   Status: {status}")
                print(f"   URL: {url}")
                
                # Show validity reasons if invalid
                if not submission.get('is_valid'):
                    reasons = submission.get('validity_reasons', [])
                    if reasons:
                        print(f"   Reasons: {', '.join(reasons)}")
                print()
        
        print()
    
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Format student submissions from the API endpoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all students for zenocross master repo
  python format_submissions.py --master-repo-owner zenocross
  
  # Fetch specific student
  python format_submissions.py --student zenoxcross --master-repo-owner zenocross
  
  # Use custom API URL
  python format_submissions.py --base-url http://example.com:3000 --master-repo-owner codepath
        """
    )
    
    parser.add_argument(
        '--base-url',
        default='http://localhost:3000',
        help='Base URL of the API (default: http://localhost:3000)'
    )
    
    parser.add_argument(
        '--student',
        help='Specific student username (optional, fetches all if not provided)'
    )
    
    parser.add_argument(
        '--master-repo-owner',
        required=True,
        help='Master repository owner (required)'
    )
    
    args = parser.parse_args()
    
    # Fetch submissions from API
    data = fetch_submissions(
        base_url=args.base_url,
        student=args.student,
        master_repo_owner=args.master_repo_owner
    )
    
    # Check for API errors
    if not data.get('success', True):
        print(f"❌ API returned error: {data.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Format and display
    format_submissions(data)


if __name__ == '__main__':
    main()

