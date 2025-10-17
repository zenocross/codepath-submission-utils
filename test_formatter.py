#!/usr/bin/env python3
"""
Test script to verify the formatter works with the webhook data
"""

import json
import sys
from pathlib import Path

# Import the format function from the main script
# Assuming format_submissions.py is in the same directory
try:
    from main import format_submissions
except ImportError:
    print("❌ Could not import format_submissions.py")
    print("Make sure format_submissions.py is in the same directory")
    sys.exit(1)


def test_with_json_file(json_file: str):
    """Test the formatter with a JSON file"""
    print(f"📄 Loading test data from: {json_file}\n")
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {json_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in file: {e}")
        sys.exit(1)
    
    # Run the formatter
    format_submissions(data)


def test_with_inline_data():
    """Test with inline data (useful for quick testing)"""
    data = {
        "success": True,
        "student": "jellyfishing2346",
        "all_submissions": [
            {
                "submission_type": "COMMENT",
                "comment_id": 3344360717,
                "is_valid": True,
                "issue_display": "GS #1",
                "issue_number": 1,
                "issue_title": "Getting Started #1 - Start a chat",
                "owner_name": "codepath",
                "repo_name": "chatbox",
                "repository": "codepath/chatbox",
                "student": "jellyfishing2346",
                "submission_date": "2025-09-28T22:45:28Z",
                "validity_reasons": ["Has attachment"]
            },
            {
                "submission_type": "PULL_REQUEST",
                "is_valid": False,
                "pr_number": 8,
                "pr_title": "added text file recording",
                "owner_name": "jellyfishing2346",
                "repo_name": "puter",
                "repository": "jellyfishing2346/puter",
                "source_repository": "codepath/puter",
                "student": "jellyfishing2346",
                "submission_date": "2025-10-13T14:10:42",
                "validity_reasons": ["Missing attachment", "No issue references"]
            }
        ]
    }
    
    print("📝 Testing with inline data\n")
    format_submissions(data)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Test with provided JSON file
        test_with_json_file(sys.argv[1])
    else:
        # Test with inline data
        print("Usage: python test_formatter.py [json_file]")
        print("Testing with inline data...\n")
        test_with_inline_data()