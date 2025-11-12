#!/usr/bin/env python3
"""
Create comparison videos by stitching two videos side-by-side
and randomizing the left/right order for blind testing.

Creates comparison sets:
- deepsink vs self_forcing
- deepsink vs long_live
- deepsink vs causvid
- deepsink vs rolling_forcing

For all videos in raw_videos directory.
"""

import os
import subprocess
import random
from pathlib import Path

# Configuration
RAW_VIDEOS_DIR = "/data/hyunbin/long_video/DeepSink_user_study/raw_videos"
OUTPUT_DIR = "/data/hyunbin/long_video/DeepSink_user_study/user_study_comparisons"

# Model pairs: (model1_folder, model2_folder, comparison_name)
COMPARISON_SETS = [
    ("deepsink", "self_forcing", "deepsink_vs_self_forcing"),
    ("deepsink", "long_live", "deepsink_vs_long_live"),
    ("deepsink", "causvid", "deepsink_vs_causvid"),
    ("deepsink", "rolling_forcing", "deepsink_vs_rolling_forcing"),
]

# Set random seed for reproducibility (change if you want different randomization)
random.seed(42)


def get_video_info(video_path):
    """Get video dimensions and duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        width = int(lines[0]) if lines[0] else None
        height = int(lines[1]) if lines[1] else None
        duration = float(lines[2]) if lines[2] else None
        return width, height, duration
    except Exception as e:
        print(f"  Error getting video info for {video_path}: {e}")
        return None, None, None


def create_comparison_video(video1_path, video2_path, output_path, order):
    """
    Create side-by-side comparison video using ffmpeg
    
    Args:
        video1_path: Path to first video (deepsink)
        video2_path: Path to second video (baseline)
        output_path: Output path for comparison video
        order: 'left' or 'right' - which video goes on left
    """
    # Ensure videos exist
    if not os.path.exists(video1_path):
        raise FileNotFoundError(f"Video not found: {video1_path}")
    if not os.path.exists(video2_path):
        raise FileNotFoundError(f"Video not found: {video2_path}")
    
    # Determine which video goes where
    if order == 'left':
        left_video = video1_path
        right_video = video2_path
        model_a = 'deepsink'
        model_b = 'baseline'
    else:
        left_video = video2_path
        right_video = video1_path
        model_a = 'baseline'
        model_b = 'deepsink'
    
    # Get video dimensions
    left_width, left_height, left_duration = get_video_info(left_video)
    right_width, right_height, right_duration = get_video_info(right_video)
    
    if not all([left_width, left_height, right_width, right_height]):
        raise ValueError("Could not get video dimensions")
    
    # Use the minimum duration
    duration = min([d for d in [left_duration, right_duration] if d is not None])
    
    # Scale both videos to same height (use minimum height)
    target_height = min(left_height, right_height)
    
    # Calculate scaled widths maintaining aspect ratio
    left_scaled_width = int(left_width * target_height / left_height)
    right_scaled_width = int(right_width * target_height / right_height)
    
    # Ensure widths are divisible by 2 (required by some codecs)
    left_scaled_width = (left_scaled_width // 2) * 2
    right_scaled_width = (right_scaled_width // 2) * 2
    
    # Total output width
    output_width = left_scaled_width + right_scaled_width
    
    # Build ffmpeg command
    # Use audio from left video
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output file
        '-i', left_video,
        '-i', right_video,
        '-filter_complex',
        f'[0:v]scale={left_scaled_width}:{target_height}[left];'
        f'[1:v]scale={right_scaled_width}:{target_height}[right];'
        f'[left][right]hstack=inputs=2[v]',
        '-map', '[v]',
        '-map', '0:a?',  # Use audio from first video if available
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',  # Re-encode audio to ensure compatibility
        '-b:a', '192k',
        '-shortest',  # End when shortest stream ends
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return model_a, model_b
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: ffmpeg failed: {e.stderr}")
        raise


def create_comparison_set(model1_folder, model2_folder, comparison_name, baseline_name):
    """
    Create all comparison videos for a model pair
    
    Args:
        model1_folder: Folder containing DeepSink videos
        model2_folder: Folder containing baseline videos
        comparison_name: Name for output folder
        baseline_name: Name of baseline model (for order sheet)
    """
    model1_path = os.path.join(RAW_VIDEOS_DIR, model1_folder)
    model2_path = os.path.join(RAW_VIDEOS_DIR, model2_folder)
    
    # Get all video files (should have same names)
    model1_videos = sorted([f for f in os.listdir(model1_path) if f.endswith('.mp4')])
    model2_videos = sorted([f for f in os.listdir(model2_path) if f.endswith('.mp4')])
    
    # Find common videos
    common_videos = set(model1_videos) & set(model2_videos)
    
    if not common_videos:
        print(f"⚠️ No common videos found between {model1_folder} and {model2_folder}")
        return 0, 0
    
    print(f"\n📹 Creating {len(common_videos)} comparison videos for {comparison_name}...")
    
    # Create output folder
    output_folder = os.path.join(OUTPUT_DIR, comparison_name)
    os.makedirs(output_folder, exist_ok=True)
    
    # Track order for order sheet
    order_sheet_entries = []
    success_count = 0
    fail_count = 0
    
    for video_file in sorted(common_videos):
        video1_path = os.path.join(model1_path, video_file)
        video2_path = os.path.join(model2_path, video_file)
        
        # Randomize order (50/50 chance)
        order = random.choice(['left', 'right'])
        
        # Create output filename
        basename = video_file.replace('.mp4', '')
        output_filename = f"{basename}_comparison.mp4"
        output_path = os.path.join(output_folder, output_filename)
        
        # Create comparison video
        try:
            model_a, model_b = create_comparison_video(
                video1_path, video2_path, output_path, order
            )
            
            # Map to actual model names
            if model_a == 'deepsink':
                actual_model_a = 'deepsink'
                actual_model_b = baseline_name
            else:
                actual_model_a = baseline_name
                actual_model_b = 'deepsink'
            
            # Add to order sheet
            order_sheet_entries.append({
                'filename': video_file,
                'model_a': actual_model_a,
                'model_b': actual_model_b
            })
            
            success_count += 1
            print(f"  ✓ {video_file}")
        except Exception as e:
            print(f"  ✗ {video_file}: {e}")
            fail_count += 1
    
    # Create order sheet
    order_sheet_path = os.path.join(output_folder, 'order_sheet.txt')
    with open(order_sheet_path, 'w') as f:
        f.write(f"Blind Test Order Sheet for {comparison_name}\n")
        f.write("=" * 50 + "\n")
        f.write(f"Original Method A: deepsink\n")
        f.write(f"Original Method B: {baseline_name}\n\n")
        f.write("Randomized Order (filename -> Model A = ?, Model B = ?):\n")
        f.write("-" * 50 + "\n")
        for entry in order_sheet_entries:
            f.write(f"{entry['filename']}: Model A = {entry['model_a']}, Model B = {entry['model_b']}\n")
    
    print(f"✓ Created order sheet: {order_sheet_path}")
    print(f"  Summary: {success_count} successful, {fail_count} failed")
    
    return success_count, fail_count


def main():
    print("="*80)
    print("Create Comparison Videos for User Study")
    print("="*80)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total_success = 0
    total_fail = 0
    
    # Create comparison sets
    baseline_name_map = {
        "self_forcing": "self_forcing",
        "long_live": "long_live",
        "causvid": "causvid",
        "rolling_forcing": "rolling_forcing"
    }
    
    for model1_folder, model2_folder, comparison_name in COMPARISON_SETS:
        baseline_name = baseline_name_map.get(model2_folder, model2_folder)
        
        success, fail = create_comparison_set(
            model1_folder, model2_folder, comparison_name, baseline_name
        )
        total_success += success
        total_fail += fail
    
    print("\n" + "="*80)
    print("Overall Summary")
    print("="*80)
    print(f"Total: {total_success} successful, {total_fail} failed")
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("="*80)
    
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

