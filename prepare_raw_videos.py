#!/usr/bin/env python3
"""
Script to copy videos from source directories to raw_videos folder
for user study preparation. Uses the matching logic from video_comparison_viewer.ipynb
to find videos by their DeepSink (Ours) numbering.
"""

import os
import re
import shutil
from pathlib import Path

# Define all directories (from notebook)
directories_30s = {
    "Causvid": "/data/jung/MovieGen_DeepSINK/causvid/128++",
    "Self-Forcing": "/data/jung/MovieGen_DeepSINK/self-forcing/128++",
    "LongLive": "/home/cvlab18/project/MovieGen_DeepSINK/longlive/128++",
    "RollingForcing": "/data/jung/MovieGen_DeepSINK/rollingforcing/128++",
    "Ours": "/data/jung/MovieGen_DeepSINK/DEEPSINK+PA/16_4+5_reuse7_Nolambda_fromNoEVYesMorph_30s"
}

directories_60s = {
    "Causvid": "/data/jung/MovieGen_DeepSINK/causvid/128++",
    "Self-Forcing": "/data/jung/MovieGen_DeepSINK/self-forcing/128++",
    "LongLive": "/home/cvlab18/project/MovieGen_DeepSINK/longlive/128++",
    "RollingForcing": "/data/jung/MovieGen_DeepSINK/rollingforcing/128++",
    "Ours": "/data/jung/MovieGen_DeepSINK/DEEPSINK+PA/16_4+5_reuse7_Nolambda_fromNoEVYesMorph_60s"
}

# Map duration names to actual subdirectory names
duration_subdirs = {
    "Causvid": {"30s": "30", "60s": "60"},
    "Self-Forcing": {"30s": "30s", "60s": "60s"},
    "LongLive": {"30s": "30s", "60s": "60s"},
    "RollingForcing": {"30s": "30s", "60s": "60s"},
    "Ours": {"30s": "30s", "60s": "60s"}
}

# Video numbers to copy
VIDEO_NUMBERS_30S = [2, 4, 7, 24, 42, 43, 46, 47, 69, 88, 109, 32, 74]
VIDEO_NUMBERS_60S = [2, 28, 43, 46, 47, 70, 53]

# Output directories
OUTPUT_BASE = "/data/hyunbin/long_video/DeepSink_user_study/raw_videos"
MODEL_MAPPING = {
    "Ours": "deepsink",
    "LongLive": "long_live",
    "Causvid": "causvid",
    "Self-Forcing": "self_forcing",
    "RollingForcing": "rolling_forcing"
}

# Which models to copy (all models for comparison)
MODELS_TO_COPY = ["Ours", "LongLive", "Self-Forcing", "RollingForcing", "Causvid"]

# Prompts file path
PROMPTS_FILE = "/data/jung/ForcingForcing/Self-Forcing/prompts/MovieGenVideoBench_extended.txt"


def extract_base_name(filename):
    """Extract base name by removing common suffixes and trailing spaces"""
    base = filename.replace('.mp4', '')
    base = re.sub(r'-lora-\d+$', '', base)
    base = re.sub(r'-\d{3}$', '', base)
    base = re.sub(r'-\d+$', '', base)
    return base.rstrip()


def find_video_files_in_subdir(base_path, model_name, duration, duration_subdirs):
    """Find video files in a specific subdirectory"""
    actual_subdir = duration_subdirs.get(model_name, {}).get(duration, duration)
    subdir_path = os.path.join(base_path, actual_subdir)
    
    file_mapping = {}  # {base_name: file_path}
    base_names = set()
    ours_number_mapping = {}  # {base_name: number} for Ours model
    
    if not os.path.exists(subdir_path):
        return file_mapping, base_names, ours_number_mapping
    
    if os.path.isdir(subdir_path):
        # For Ours, videos are in numbered subdirectories
        if model_name == "Ours":
            for item in sorted(os.listdir(subdir_path)):  # Sort to process in order
                item_path = os.path.join(subdir_path, item)
                if os.path.isdir(item_path) and item.isdigit():
                    video_number = int(item)  # Store the number
                    for file in os.listdir(item_path):
                        file_path = os.path.join(item_path, file)
                        if os.path.isfile(file_path) and file.endswith('.mp4'):
                            base = extract_base_name(file)
                            base_names.add(base)
                            if base not in file_mapping:
                                file_mapping[base] = file_path
                                ours_number_mapping[base] = video_number
        else:
            # For other models, videos are directly in the subdirectory
            for file in os.listdir(subdir_path):
                file_path = os.path.join(subdir_path, file)
                if os.path.isfile(file_path) and file.endswith('.mp4'):
                    base = extract_base_name(file)
                    base_names.add(base)
                    if base not in file_mapping:
                        file_mapping[base] = file_path
    
    return file_mapping, base_names, ours_number_mapping


def find_video_files(duration, directories_30s, directories_60s, duration_subdirs):
    """Find all video files for a specific duration"""
    directories = directories_30s if duration == "30s" else directories_60s
    all_file_mapping = {}
    base_names_by_dir = {}
    ours_number_mapping = {}  # {base_name: number} for sorting
    
    for name, base_path in directories.items():
        file_mapping, base_names, ours_numbers = find_video_files_in_subdir(
            base_path, name, duration, duration_subdirs
        )
        
        for base_name, file_path in file_mapping.items():
            if base_name not in all_file_mapping:
                all_file_mapping[base_name] = {}
            all_file_mapping[base_name][name] = file_path
        
        base_names_by_dir[name] = base_names
        
        # Store Ours numbers for sorting
        if name == "Ours":
            ours_number_mapping.update(ours_numbers)
    
    return all_file_mapping, base_names_by_dir, ours_number_mapping


def copy_videos_for_duration(duration, video_numbers, directories_30s, directories_60s, duration_subdirs):
    """Copy videos for a specific duration and list of video numbers"""
    print(f"\n{'='*80}")
    print(f"Processing {duration} videos")
    print(f"{'='*80}")
    
    # Find all video files
    print(f"Scanning directories for {duration} videos...")
    file_mapping, base_names_by_dir, ours_number_mapping = find_video_files(
        duration, directories_30s, directories_60s, duration_subdirs
    )
    
    # Create reverse mapping: number -> base_name
    number_to_base = {num: base for base, num in ours_number_mapping.items()}
    
    print(f"Found {len(ours_number_mapping)} videos with Ours numbering")
    
    # Process each video number
    success_count = 0
    fail_count = 0
    
    for video_num in video_numbers:
        if video_num not in number_to_base:
            print(f"  ✗ Video #{video_num}: Not found in Ours numbering")
            fail_count += 1
            continue
        
        base_name = number_to_base[video_num]
        
        # Check if all required models have this video
        missing_models = []
        for model_name in MODELS_TO_COPY:
            if model_name not in file_mapping.get(base_name, {}):
                missing_models.append(model_name)
        
        if missing_models:
            print(f"  ✗ Video #{video_num}: Missing models {missing_models}")
            fail_count += 1
            continue
        
        # Copy videos for each model
        for model_name in MODELS_TO_COPY:
            source_path = file_mapping[base_name][model_name]
            output_dir = os.path.join(OUTPUT_BASE, MODEL_MAPPING[model_name])
            os.makedirs(output_dir, exist_ok=True)
            
            output_filename = f"{duration}_{video_num}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                # Copy the file
                shutil.copy2(source_path, output_path)
                print(f"  ✓ Video #{video_num} ({model_name}): {output_filename}")
            except Exception as e:
                print(f"  ✗ Video #{video_num} ({model_name}): Failed to copy - {e}")
                fail_count += 1
                continue
        
        success_count += 1
    
    print(f"\n{duration} Summary: {success_count} successful, {fail_count} failed")
    return success_count, fail_count


def extract_prompts(video_numbers_30s, video_numbers_60s, prompts_file, output_file):
    """Extract prompts for the specified video numbers and save to file"""
    print(f"\n{'='*80}")
    print("Extracting Prompts")
    print(f"{'='*80}")
    
    # Read all prompts
    if not os.path.exists(prompts_file):
        print(f"✗ Prompts file not found: {prompts_file}")
        return False
    
    with open(prompts_file, 'r', encoding='utf-8') as f:
        all_prompts = [line.strip() for line in f.readlines()]
    
    print(f"Loaded {len(all_prompts)} prompts from file")
    
    # Get all unique video numbers
    all_video_numbers = sorted(set(video_numbers_30s + video_numbers_60s))
    
    # Extract prompts for our video numbers
    prompts_matched = []
    missing_prompts = []
    
    for video_num in all_video_numbers:
        if video_num < len(all_prompts):
            prompt = all_prompts[video_num]
            # Determine which durations this video appears in
            durations = []
            if video_num in video_numbers_30s:
                durations.append("30s")
            if video_num in video_numbers_60s:
                durations.append("60s")
            
            prompts_matched.append({
                'number': video_num,
                'durations': durations,
                'prompt': prompt
            })
        else:
            missing_prompts.append(video_num)
    
    if missing_prompts:
        print(f"⚠️ Missing prompts for video numbers: {missing_prompts}")
    
    # Write to output file
    output_path = os.path.join(OUTPUT_BASE, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("Video Number to Prompt Mapping\n")
        f.write("=" * 80 + "\n")
        f.write("Format: Video Number | Durations | Prompt\n")
        f.write("=" * 80 + "\n\n")
        
        for item in prompts_matched:
            durations_str = ", ".join(item['durations'])
            f.write(f"Video #{item['number']} | {durations_str} | {item['prompt']}\n\n")
    
    print(f"✓ Saved {len(prompts_matched)} prompts to: {output_path}")
    return True


def main():
    print("="*80)
    print("Prepare Raw Videos for User Study")
    print("="*80)
    
    # Create output base directory
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    
    # Process 30s videos
    success_30s, fail_30s = copy_videos_for_duration(
        "30s", VIDEO_NUMBERS_30S, directories_30s, directories_60s, duration_subdirs
    )
    
    # Process 60s videos
    success_60s, fail_60s = copy_videos_for_duration(
        "60s", VIDEO_NUMBERS_60S, directories_30s, directories_60s, duration_subdirs
    )
    
    # Extract prompts
    extract_prompts(VIDEO_NUMBERS_30S, VIDEO_NUMBERS_60S, PROMPTS_FILE, "prompts_matched.txt")
    
    print("\n" + "="*80)
    print("Overall Summary")
    print("="*80)
    print(f"30s: {success_30s} successful, {fail_30s} failed")
    print(f"60s: {success_60s} successful, {fail_60s} failed")
    print(f"Total: {success_30s + success_60s} successful, {fail_30s + fail_60s} failed")
    print(f"\nOutput directory: {OUTPUT_BASE}")
    print("="*80)
    
    return 0 if (fail_30s + fail_60s) == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

