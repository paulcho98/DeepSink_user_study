#!/usr/bin/env python3
"""Create video index mappings for user study"""

import os
import json

# Base directory
base_dir = "/Users/junyoung/projects/LA_Evaluations/user_study_comparisons"

# Define the methods and their directories
methods = {
    "hallo3": "user_study_comparisons/hallo3_NEW_avspeech_OG_vs_la_1",
    "hunyuan": "user_study_comparisons/hunyuan_NEW_avspeech_AR_vs_la_margin3",
    "omniavatar": "user_study_comparisons/omniavatar_NEW_avspeech_OG_vs_la"
}

def create_mapping_files():
    for method, directory in methods.items():
        full_path = os.path.join(base_dir, directory)
        print(f"Processing {method} directory: {full_path}")

        if not os.path.exists(full_path):
            print(f"Directory not found: {full_path}")
            continue

        # Get all comparison videos
        videos = []
        for file in os.listdir(full_path):
            if file.endswith("_comparison.mp4"):
                videos.append(file)

        # Sort for consistent ordering
        videos.sort()

        # Create mapping file
        mapping_file = f"{base_dir}/data/{method}_avspeech_mapping.txt"
        with open(mapping_file, 'w') as f:
            f.write(f"# {method.title()} AVSpeech Video Index Mapping\n")
            f.write("# Format: index:filename\n")
            for i, video in enumerate(videos):
                f.write(f"{i}:{video}\n")

        print(f"Created {mapping_file} with {len(videos)} videos")

if __name__ == "__main__":
    create_mapping_files()