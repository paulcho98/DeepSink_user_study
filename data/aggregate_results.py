#!/usr/bin/env python3
"""
User Study Results Aggregation Script

This script processes user study result files for comparison video studies
and provides comprehensive analysis by decoding the blind test results using order sheets.

Usage:
    python aggregate_results.py --results_file user_responses.json
    python aggregate_results.py --results_dir responses/
"""

import os
import argparse
import json
import pandas as pd
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
import glob

class UserStudyAggregator:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.study_config = self.load_study_config()
        self.order_sheets = self.load_order_sheets()

        # Comparison mappings based on study_config.json
        self.comparison_mappings = self.generate_comparison_mappings()

    def load_study_config(self):
        """Load study configuration"""
        config_path = os.path.join(self.base_dir, "study_config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: study_config.json not found at {config_path}")
            return None

    def generate_comparison_mappings(self):
        """Generate comparison mappings from study config"""
        if not self.study_config:
            return {}
        
        mappings = {}
        for comparison_set in self.study_config.get('comparison_sets', []):
            name = comparison_set['name']
            # Extract method names from comparison name
            methods = name.split('_vs_')
            if len(methods) == 2:
                mappings[name] = {
                    'order_file': comparison_set.get('order_file', ''),
                    'method_a': methods[0],
                    'method_b': methods[1],
                    'video_folder': comparison_set.get('video_folder', '')
                }
        
        return mappings

    def load_order_sheets(self):
        """Load all order sheets for decoding blind test results"""
        order_sheets = {}

        if not self.study_config:
            return order_sheets

        for comparison_set in self.study_config.get('comparison_sets', []):
            order_file_path = comparison_set.get('order_file', '')
            if order_file_path:
                # Convert relative path to absolute path
                full_path = os.path.join(os.path.dirname(self.base_dir), order_file_path)
                if os.path.exists(full_path):
                    order_sheets[comparison_set['name']] = self.parse_order_sheet(full_path)
                else:
                    print(f"Warning: Order sheet not found: {full_path}")

        return order_sheets

    def parse_order_sheet(self, file_path):
        """Parse order sheet to get video filename to order mapping"""
        order_mapping = {}

        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if ':' in line and 'Model A =' in line:
                    # Extract filename and order info
                    parts = line.split(': Model A = ')
                    if len(parts) == 2:
                        filename = parts[0].strip()
                        order_info = parts[1].strip()

                        # Parse "method1, Model B = method2"
                        if ', Model B = ' in order_info:
                            model_a, model_b = order_info.split(', Model B = ')
                            order_mapping[filename] = {
                                'model_a': model_a.strip(),
                                'model_b': model_b.strip()
                            }

        except Exception as e:
            print(f"Error parsing order sheet {file_path}: {e}")

        return order_mapping

    def decode_response(self, comparison_name, video_filename, choice):
        """Decode a single response using order sheets"""
        if comparison_name not in self.order_sheets:
            return None, None, "No order sheet found"

        # Remove .mp4 extension if present
        video_key = video_filename.replace('.mp4', '')
        
        # Try different filename formats
        possible_keys = [
            video_key,
            video_filename,
            f"{video_key}_comparison.mp4",
            video_key.replace('_comparison', '')
        ]

        order_info = None
        for key in possible_keys:
            if key in self.order_sheets[comparison_name]:
                order_info = self.order_sheets[comparison_name][key]
                break

        if not order_info:
            return None, None, f"Video {video_filename} not found in order sheet"

        # Decode choice
        if choice == 'A':
            chosen_method = order_info['model_a']
            other_method = order_info['model_b']
        elif choice == 'B':
            chosen_method = order_info['model_b']
            other_method = order_info['model_a']
        else:
            return None, None, f"Invalid choice: {choice}"

        return chosen_method, other_method, "success"

    def process_single_result_file(self, file_path):
        """Process a single result file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

        participant_id = data.get('participantId', 'unknown')
        responses = data.get('responses', {})
        
        decoded_responses = []
        
        for comparison_name, video_responses in responses.items():
            for video_filename, choice in video_responses.items():
                chosen_method, other_method, status = self.decode_response(
                    comparison_name, video_filename, choice
                )
                
                decoded_responses.append({
                    'participant_id': participant_id,
                    'comparison_name': comparison_name,
                    'video_filename': video_filename,
                    'choice': choice,
                    'chosen_method': chosen_method,
                    'other_method': other_method,
                    'decode_status': status
                })

        return decoded_responses

    def process_results_directory(self, results_dir):
        """Process all result files in a directory"""
        all_responses = []
        
        # Find all JSON files
        json_files = glob.glob(os.path.join(results_dir, "*.json"))
        
        if not json_files:
            print(f"No JSON files found in {results_dir}")
            return all_responses

        for file_path in json_files:
            print(f"Processing {file_path}...")
            responses = self.process_single_result_file(file_path)
            if responses:
                all_responses.extend(responses)

        return all_responses

    def aggregate_results(self, responses):
        """Aggregate responses and generate statistics"""
        if not responses:
            print("No responses to aggregate")
            return {}

        df = pd.DataFrame(responses)
        
        # Filter out failed decodes
        successful_df = df[df['decode_status'] == 'success'].copy()
        
        if successful_df.empty:
            print("No successfully decoded responses")
            return {}

        results = {
            'summary': {
                'total_responses': len(df),
                'successful_decodes': len(successful_df),
                'failed_decodes': len(df) - len(successful_df),
                'unique_participants': df['participant_id'].nunique(),
                'comparison_sets': df['comparison_name'].unique().tolist()
            },
            'method_preferences': {},
            'comparison_results': {},
            'detailed_results': successful_df.to_dict('records')
        }

        # Method preferences (overall win rates)
        method_wins = Counter(successful_df['chosen_method'])
        total_comparisons = len(successful_df)
        
        for method, wins in method_wins.items():
            results['method_preferences'][method] = {
                'wins': wins,
                'total_comparisons': total_comparisons,
                'win_rate': wins / total_comparisons if total_comparisons > 0 else 0
            }

        # Pairwise comparison results
        for comparison_name in successful_df['comparison_name'].unique():
            comp_df = successful_df[successful_df['comparison_name'] == comparison_name]
            
            if comparison_name in self.comparison_mappings:
                method_a = self.comparison_mappings[comparison_name]['method_a']
                method_b = self.comparison_mappings[comparison_name]['method_b']
                
                method_a_wins = len(comp_df[comp_df['chosen_method'] == method_a])
                method_b_wins = len(comp_df[comp_df['chosen_method'] == method_b])
                total = method_a_wins + method_b_wins
                
                results['comparison_results'][comparison_name] = {
                    'method_a': method_a,
                    'method_b': method_b,
                    'method_a_wins': method_a_wins,
                    'method_b_wins': method_b_wins,
                    'total_comparisons': total,
                    'method_a_win_rate': method_a_wins / total if total > 0 else 0,
                    'method_b_win_rate': method_b_wins / total if total > 0 else 0
                }

        return results

    def generate_report(self, results, output_file=None):
        """Generate a comprehensive report"""
        if not results:
            print("No results to report")
            return

        report = []
        report.append("=" * 80)
        report.append("USER STUDY RESULTS REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        summary = results['summary']
        report.append("SUMMARY:")
        report.append(f"  Total responses: {summary['total_responses']}")
        report.append(f"  Successfully decoded: {summary['successful_decodes']}")
        report.append(f"  Failed decodes: {summary['failed_decodes']}")
        report.append(f"  Unique participants: {summary['unique_participants']}")
        report.append(f"  Comparison sets: {len(summary['comparison_sets'])}")
        report.append("")

        # Method preferences
        if results['method_preferences']:
            report.append("OVERALL METHOD PREFERENCES:")
            for method, stats in sorted(results['method_preferences'].items(), 
                                      key=lambda x: x[1]['win_rate'], reverse=True):
                report.append(f"  {method}: {stats['wins']}/{stats['total_comparisons']} "
                            f"({stats['win_rate']:.1%} win rate)")
            report.append("")

        # Pairwise comparisons
        if results['comparison_results']:
            report.append("PAIRWISE COMPARISON RESULTS:")
            for comp_name, stats in results['comparison_results'].items():
                report.append(f"  {comp_name}:")
                report.append(f"    {stats['method_a']}: {stats['method_a_wins']} wins "
                            f"({stats['method_a_win_rate']:.1%})")
                report.append(f"    {stats['method_b']}: {stats['method_b_wins']} wins "
                            f"({stats['method_b_win_rate']:.1%})")
                report.append(f"    Total: {stats['total_comparisons']} comparisons")
                report.append("")

        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"Report saved to {output_file}")
        else:
            print(report_text)

        return report_text

def main():
    parser = argparse.ArgumentParser(description='Aggregate user study results')
    parser.add_argument('--results_file', help='Single results file to process')
    parser.add_argument('--results_dir', help='Directory containing result files')
    parser.add_argument('--output_dir', default='analysis_output', 
                       help='Output directory for results')
    
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize aggregator
    aggregator = UserStudyAggregator()

    responses = []
    
    if args.results_file:
        # Process single file
        print(f"Processing single file: {args.results_file}")
        file_responses = aggregator.process_single_result_file(args.results_file)
        if file_responses:
            responses.extend(file_responses)
    elif args.results_dir:
        # Process directory
        print(f"Processing directory: {args.results_dir}")
        responses = aggregator.process_results_directory(args.results_dir)
    else:
        print("Please specify either --results_file or --results_dir")
        return

    if not responses:
        print("No responses processed")
        return

    # Aggregate results
    print("Aggregating results...")
    results = aggregator.aggregate_results(responses)

    # Generate report
    output_file = os.path.join(args.output_dir, 'aggregated_results.txt')
    aggregator.generate_report(results, output_file)

    # Save detailed results as JSON
    json_output = os.path.join(args.output_dir, 'detailed_results.json')
    with open(json_output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Detailed results saved to {json_output}")

    # Save responses DataFrame as CSV
    if responses:
        csv_output = os.path.join(args.output_dir, 'all_responses.csv')
        pd.DataFrame(responses).to_csv(csv_output, index=False)
        print(f"All responses saved to {csv_output}")

if __name__ == '__main__':
    main()