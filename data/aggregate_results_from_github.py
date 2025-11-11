#!/usr/bin/env python3
"""
GitHub Issues Results Aggregation Script

This script fetches user study results from GitHub issues and provides comprehensive analysis
by aggregating all open issues from the research_survey_result_collect repository.

Usage:
    python aggregate_results_from_github.py --token YOUR_GITHUB_TOKEN
    python aggregate_results_from_github.py --token YOUR_GITHUB_TOKEN --output_dir analysis/
"""

import os
import argparse
import json
import requests
import re
from aggregate_results import UserStudyAggregator

class GitHubIssuesAggregator(UserStudyAggregator):
    def __init__(self, github_token, base_dir=None):
        super().__init__(base_dir)
        self.github_token = github_token
        self.repo_owner = "deep-overflow"
        self.repo_name = "InterGenEval_user_study"

    def fetch_github_issues(self):
        """Fetch all open issues from GitHub repository"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        params = {
            'state': 'open',
            'per_page': 100  # GitHub max per page
        }

        all_issues = []
        page = 1

        while True:
            params['page'] = page
            print(f"Fetching page {page} of issues...")

            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Error fetching issues: {response.status_code} - {response.text}")
                break

            issues = response.json()

            if not issues:  # No more issues
                break

            # Filter out pull requests (GitHub treats PRs as issues)
            issues = [issue for issue in issues if 'pull_request' not in issue]
            all_issues.extend(issues)

            print(f"  Found {len(issues)} issues on page {page}")
            page += 1

            # GitHub pagination check
            if len(issues) < params['per_page']:
                break

        print(f"Total issues fetched: {len(all_issues)}")
        return all_issues

    def extract_results_from_issue(self, issue):
        """Extract results code from GitHub issue body"""
        body = issue.get('body', '')

        print(f"  Debug: Issue body preview: {body[:200]}...")

        # Try multiple patterns for extracting results
        # Pattern 1: Markdown code blocks with ```
        code_block_pattern = r'```\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, body, re.DOTALL)

        if matches:
            print(f"  Found {len(matches)} code blocks")
            results_code = matches[0].strip()
        else:
            # Pattern 2: Look for lines that match our format directly
            lines = body.split('\n')
            result_lines = []
            for line in lines:
                line = line.strip()
                if re.match(r'^\d+-\d+-\d+-\d{4}$', line):
                    result_lines.append(line)

            if result_lines:
                print(f"  Found {len(result_lines)} result lines without code blocks")
                results_code = '\n'.join(result_lines)
            else:
                print(f"  No results code found in issue #{issue['number']}: {issue['title']}")
                return None

        # Handle both actual newlines and \n strings
        if '\\n' in results_code:
            # Replace literal \n with actual newlines
            results_code = results_code.replace('\\n', '\n')

        # Validate format (should be lines like "1-1-8-1122")
        lines = [line.strip() for line in results_code.split('\n') if line.strip()]
        valid_lines = []

        for line in lines:
            # Check if line matches pattern: method-dataset-videoIndex-answers
            if re.match(r'^\d+-\d+-\d+-\d{4}$', line):
                valid_lines.append(line)
            else:
                print(f"  Invalid result format: {line}")

        if not valid_lines:
            print(f"  No valid results found in issue #{issue['number']}")
            return None

        print(f"  Extracted {len(valid_lines)} valid result lines")
        return '\n'.join(valid_lines)

    def process_user_responses(self, responses_text):
        """Process all responses from a user (GitHub version with proper newline handling)"""
        responses = []
        lines = responses_text.strip().split('\n')  # Use actual newlines, not escaped

        for line in lines:
            line = line.strip()
            if line:
                decoded = self.decode_result_code(line)
                if decoded:
                    responses.append(decoded)

        return responses

    def process_github_issues(self):
        """Process all GitHub issues to extract and aggregate results"""
        print("Fetching GitHub issues...")
        issues = self.fetch_github_issues()

        if not issues:
            print("No issues found in repository")
            return []

        all_responses = []

        for i, issue in enumerate(issues, 1):
            print(f"Processing issue {i}/{len(issues)}: #{issue['number']} - {issue['title']}")

            results_code = self.extract_results_from_issue(issue)
            if results_code:
                responses = self.process_user_responses(results_code)
                if responses:
                    all_responses.append(responses)
                    print(f"  ✅ Extracted {len(responses)} comparisons")
                else:
                    print(f"  ❌ Failed to process results")
            else:
                print(f"  ⚠️ No valid results found")

        print(f"\nSuccessfully processed {len(all_responses)} users from {len(issues)} issues")
        return all_responses

def main():
    parser = argparse.ArgumentParser(description="Aggregate user study results from GitHub issues")
    parser.add_argument('--token', default='None', help='GitHub personal access token')
    parser.add_argument('--output_dir', default='github_analysis_output', help='Output directory for reports')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print("GITHUB ISSUES RESULTS AGGREGATION")
    print("=" * 60)
    print(f"Repository: j0seo/research_survey_result_collect")
    print(f"Output directory: {args.output_dir}")
    print()

    # Initialize aggregator
    aggregator = GitHubIssuesAggregator(args.token)

    # Process GitHub issues
    all_responses = aggregator.process_github_issues()

    if not all_responses:
        print("No valid responses found in GitHub issues")
        return

    # Aggregate and analyze
    print(f"\nAggregating responses from {len(all_responses)} users...")
    aggregated = aggregator.aggregate_multiple_users(all_responses)
    stats = aggregator.calculate_statistics(aggregated)

    # Generate report
    report_file = os.path.join(args.output_dir, 'github_study_report.txt')
    report = aggregator.generate_report(stats, report_file)
    print("\n" + "="*50)
    print("ANALYSIS COMPLETE")
    print("="*50)
    print(report)

    # Always export CSV for easy analysis
    csv_file = os.path.join(args.output_dir, 'github_study_results.csv')
    aggregator.export_to_csv(stats, csv_file)

    print(f"\nFiles generated:")
    print(f"  📊 Report: {report_file}")
    print(f"  📈 CSV: {csv_file}")

if __name__ == "__main__":
    main()