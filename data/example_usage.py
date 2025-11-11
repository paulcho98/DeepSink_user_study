#!/usr/bin/env python3
"""
Example usage of the user study results aggregation script
"""

from aggregate_results import UserStudyAggregator
import os

def create_sample_data():
    """Create sample user responses for testing"""

    # Sample responses from 3 users
    sample_responses = [
        # User 1
        "0-1-3-1221\\n0-1-17-2112\\n1-1-8-1122\\n1-1-15-2111\\n1-1-20-1212\\n2-1-5-2221\\n2-1-12-1122\\n2-1-18-2211\\n0-1-9-1121",

        # User 2
        "0-1-3-2112\\n0-1-17-1221\\n1-1-8-2211\\n1-1-15-1222\\n1-1-20-2121\\n2-1-5-1112\\n2-1-12-2211\\n2-1-18-1122\\n0-1-9-2212",

        # User 3
        "0-1-3-1112\\n0-1-17-2221\\n1-1-8-1211\\n1-1-15-2122\\n1-1-20-1221\\n2-1-5-2112\\n2-1-12-1211\\n2-1-18-2122\\n0-1-9-1212"
    ]

    # Save sample data
    os.makedirs('sample_responses', exist_ok=True)
    for i, response in enumerate(sample_responses):
        with open(f'sample_responses/user_{i+1}.txt', 'w') as f:
            f.write(response)

    return sample_responses

def example_single_result():
    """Example: Process a single result string"""
    print("="*60)
    print("EXAMPLE 1: Single Result Processing")
    print("="*60)

    aggregator = UserStudyAggregator()

    # Single result code
    result_code = "1-1-8-1122"  # hunyuan, avspeech, video 8, answers 1122

    decoded = aggregator.decode_result_code(result_code)
    if decoded:
        print(f"Original code: {result_code}")
        print(f"Method: {decoded['method_name']}")
        print(f"Dataset: {decoded['dataset_name']}")
        print(f"Video: {decoded['video_filename']}")
        print(f"Actual methods: {decoded['actual_methods']}")
        print("Answers:")
        for question, answer in decoded['answers'].items():
            print(f"  {question}: {answer['choice']}")

    print()

def example_multiple_users():
    """Example: Process multiple users and generate analysis"""
    print("="*60)
    print("EXAMPLE 2: Multiple User Analysis")
    print("="*60)

    # Create sample data
    sample_responses = create_sample_data()

    aggregator = UserStudyAggregator()
    all_responses = []

    # Process each user's responses
    for i, response_text in enumerate(sample_responses):
        responses = aggregator.process_user_responses(response_text)
        all_responses.append(responses)
        print(f"User {i+1}: {len(responses)} comparisons")

    print(f"\\nProcessed {len(all_responses)} users total")

    # Aggregate and analyze
    aggregated = aggregator.aggregate_multiple_users(all_responses)
    stats = aggregator.calculate_statistics(aggregated)

    # Generate report
    report = aggregator.generate_report(stats)
    print("\\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)
    print(report[:1000] + "..." if len(report) > 1000 else report)

    # Save to files
    os.makedirs('analysis_output', exist_ok=True)
    with open('analysis_output/example_report.txt', 'w') as f:
        f.write(report)

    print("\\nFull report saved to: analysis_output/example_report.txt")

def example_command_line():
    """Show command line usage examples"""
    print("="*60)
    print("COMMAND LINE USAGE EXAMPLES")
    print("="*60)
    print()
    print("1. Process a single result:")
    print("   python aggregate_results.py --single_result '0-1-3-1221,0-1-17-2112,1-1-8-1122'")
    print()
    print("2. Process a single file:")
    print("   python aggregate_results.py --results_file user_responses.txt")
    print()
    print("3. Process multiple files:")
    print("   python aggregate_results.py --results_dir responses/ --csv")
    print()
    print("4. Export to CSV:")
    print("   python aggregate_results.py --results_dir responses/ --csv --output_dir analysis/")

if __name__ == "__main__":
    print("USER STUDY RESULTS AGGREGATION - EXAMPLES")
    print()

    example_single_result()
    example_multiple_users()
    example_command_line()

    print("\\n" + "="*60)
    print("READY FOR REAL DATA!")
    print("="*60)
    print("The aggregation script is ready to process real user study results.")
    print("Use the command line examples above with your actual data files.")