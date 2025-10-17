# CodePath Submission Formatting Util

A Python utility script that fetches and formats student submissions from a Flask API endpoint, organizing them by project and student with detailed submission information.

## Description

This script queries a Flask API to retrieve GitHub-based student submissions (comments and pull requests) and displays them in a formatted, easy-to-read report. It groups submissions by project and student, showing submission validity, location (own fork vs codepath repo), and direct GitHub URLs.

## Features

- 📊 Fetch submissions for all students or a specific student
- 🔍 Organized view by project and student
- ✅ Displays submission validity status with reasons
- 🔗 Direct GitHub links to comments and pull requests
- 📍 Shows submission location (own fork vs codepath repo)
- 📅 Submissions sorted by date

## Requirements

- Python 3.6+
- `requests` library

Install dependencies:
```bash
pip install requests
```

## Usage

### Basic Syntax

```bash
python main.py --master-repo-owner OWNER [OPTIONS]
```

### Required Arguments

- `--master-repo-owner`: The GitHub owner of the master repository (required)

### Optional Arguments

- `--base-url`: Base URL of the API (default: `http://localhost:3000`)
- `--student`: Specific student username to fetch (if omitted, fetches all students)

### Examples

**Fetch all students for codepath master repo:**
```bash
python main.py --master-repo-owner codepath
```

**Fetch specific student:**
```bash
python main.py --student zenocross --master-repo-owner codepath
```

**Use custom API URL:**
```bash
python main.py --base-url https://www.zenocross.com --master-repo-owner codepath
```

**Fetch all students from codepath repo:**
```bash
python main.py --master-repo-owner codepath
```

## Output Format

The script displays:
- Summary statistics (total projects, students, submissions)
- Submissions grouped by project and student
- For each submission:
  - Title/description
  - Location (own fork, codepath repo, or other)
  - Validity status (✅ VALID or ❌ INVALID)
  - Direct GitHub URL
  - Invalid reasons (if applicable)

### Sample Output

```
🔍 Fetching submissions from: http://localhost:3000/admin/fetch-student-submissions
   Master repo owner: zenocross

================================================================================
📊 STUDENT SUBMISSIONS SUMMARY
================================================================================
Total Projects: 2
Total Students: 5
Total Submissions: 12

================================================================================
Project: ios-app
================================================================================

👤 Student: john-doe
--------------------------------------------------------------------------------
1. WK1 - Week 1 Assignment
   Location: own fork
   Status: ✅ VALID
   URL: https://github.com/john-doe/ios-app/issues/1#issuecomment-123456

...
```

## API Endpoints

The script calls the following API endpoints:

- **All students**: `GET /admin/fetch-student-submissions?master_repo_owner=OWNER`
- **Specific student**: `GET /admin/fetch-student-submission/{student}?master_repo_owner=OWNER`

## Error Handling

- Network errors and timeouts (60s) are caught and reported
- API errors are displayed with error messages
- Invalid responses return helpful error messages

## License

MIT

