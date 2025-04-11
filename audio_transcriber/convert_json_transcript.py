#!/usr/bin/env python3
"""
convert_json_transcript.py

This module converts AWS Transcribe JSON output into a readable transcript.
It supports two methods for obtaining the transcript data:
  1. Converting from a local JSON file.
  2. Converting by choosing an AWS Transcribe job from a specified S3 bucket.
  
The processed transcript is then displayed and saved to a file.
"""

import json
import sys
import os
import re
import time
import boto3
import urllib.parse
import requests
from botocore.exceptions import ClientError
import questionary
from ui_style import custom_style
from utils import sanitize_path

def print_welcome_message():
    welcome_text = """
╔═ 🔄 ═══ 📝 ═══ ☁️ ═══ 📊 ═══ 🔄 ═══ 📝 ═══ ☁️ ═══ 📊 ═══ 🔄 ═╗
║        Convert an AWS Transcribe JSON Transcript!        ║
╚═ 🔄 ═══ 📝 ═══ ☁️ ═══ 📊 ═══ 🔄 ═══ 📝 ═══ ☁️ ═══ 📊 ═══ 🔄 ═╝

"""
    print(welcome_text)

def get_valid_file_path():
    """
    Repeatedly prompt for a valid file path until one is provided.
    
    Returns:
        str: Valid, sanitized file path.
    """
    while True:
        file_path = questionary.text(
            "Enter the path to your AWS Transcribe JSON file:",
            style=custom_style
        ).ask()
        try:
            return sanitize_path(file_path)
        except FileNotFoundError as e:
            print(f"\nError: {e}\n")

def get_transcript_from_file():
    """
    Load transcript data from a local JSON file.
    
    Returns:
        dict: Parsed JSON data.
    """
    file_path = get_valid_file_path()
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

def get_transcript_from_bucket():
    """
    Prompt the user for an S3 bucket name (defaulting to 'internal-audio-recordings'),
    list all AWS Transcribe jobs whose MediaFileUri begins with that bucket's path,
    and let the user choose one.
    """
    # Prompt for bucket name (default if blank)
    bucket = questionary.text(
        "Enter the S3 bucket name for the audio file (leave blank for default 'internal-audio-recordings'):",
        style=custom_style
    ).ask().strip() or "internal-audio-recordings"

    transcribe_client = boto3.client('transcribe')

    # Retrieve all transcription jobs (paginated)
    all_jobs = []
    response = transcribe_client.list_transcription_jobs()
    all_jobs.extend(response.get("TranscriptionJobSummaries", []))
    while "NextToken" in response:
        response = transcribe_client.list_transcription_jobs(NextToken=response["NextToken"])
        all_jobs.extend(response.get("TranscriptionJobSummaries", []))

    # Filter jobs based on whether their MediaFileUri starts with the provided bucket
    matching_jobs = []
    for job_summary in all_jobs:
        job_name = job_summary["TranscriptionJobName"]
        job_details = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)["TranscriptionJob"]
        media_uri = job_details.get("Media", {}).get("MediaFileUri", "")
        if media_uri.startswith(f"s3://{bucket}/"):
            matching_jobs.append(job_details)

    if not matching_jobs:
        print(f"No transcription jobs found for bucket '{bucket}'.")
        retry = questionary.text(
            "Would you like to try another bucket? (y/n):",
            style=custom_style
        ).ask().lower().strip()
        if retry == 'y':
            return get_transcript_from_bucket()
        else:
            sys.exit(1)

    # Let the user select from the matching transcription jobs
    job_choices = []
    for job in matching_jobs:
        job_choices.append(f"{job['TranscriptionJobName']} - {job['TranscriptionJobStatus']}")

    selected = questionary.select(
        "Select a transcription job:",
        choices=job_choices,
        style=custom_style,
        pointer="👉 "
    ).ask()
    selected_job_name = selected.split(" - ")[0]
    final_job = transcribe_client.get_transcription_job(TranscriptionJobName=selected_job_name)["TranscriptionJob"]

    if final_job["TranscriptionJobStatus"] == "COMPLETED":
        transcript_uri = final_job["Transcript"]["TranscriptFileUri"]
        parsed_uri = urllib.parse.urlparse(transcript_uri)
        if parsed_uri.netloc == 's3.amazonaws.com':
            path_parts = parsed_uri.path.lstrip('/').split('/')
            bucket_name = path_parts[0]
            key = '/'.join(path_parts[1:])
            s3_client = boto3.client('s3')
            s3_response = s3_client.get_object(Bucket=bucket_name, Key=key)
            data = json.loads(s3_response['Body'].read().decode('utf-8'))
        else:
            req_response = requests.get(transcript_uri)
            data = req_response.json()
        return data, transcript_uri, selected_job_name  # Return data, URI, and job name
    elif final_job["TranscriptionJobStatus"] == "FAILED":
        print("Transcription job failed:", final_job.get("FailureReason", "Unknown error"))
        sys.exit(1)
    else:
        print(f"Transcription job is currently {final_job['TranscriptionJobStatus']}.")
        wait_choice = questionary.text(
            "Would you like to wait for the job to complete? (y/n):",
            style=custom_style
        ).ask().lower().strip()
        if wait_choice == "y":
            while final_job["TranscriptionJobStatus"] not in ["COMPLETED", "FAILED"]:
                time.sleep(30)
                final_job = transcribe_client.get_transcription_job(TranscriptionJobName=selected_job_name)["TranscriptionJob"]
            if final_job["TranscriptionJobStatus"] == "COMPLETED":
                transcript_uri = final_job["Transcript"]["TranscriptFileUri"]
                parsed_uri = urllib.parse.urlparse(transcript_uri)
                if parsed_uri.netloc == 's3.amazonaws.com':
                    path_parts = parsed_uri.path.lstrip('/').split('/')
                    bucket_name = path_parts[0]
                    key = '/'.join(path_parts[1:])
                    s3_client = boto3.client('s3')
                    s3_response = s3_client.get_object(Bucket=bucket_name, Key=key)
                    data = json.loads(s3_response['Body'].read().decode('utf-8'))
                else:
                    req_response = requests.get(transcript_uri)
                    data = req_response.json()
                return data, transcript_uri, selected_job_name
            else:
                print("Job failed:", final_job.get("FailureReason", "Unknown error"))
                sys.exit(1)
        else:
            sys.exit(1)

def process_transcript(data, speaker_names=None):
    """
    Process AWS Transcribe output into a readable transcript with speaker labels.

    Args:
        data (dict): AWS Transcribe output.
        speaker_names (dict): Optional mapping of speaker labels to names.

    Returns:
        str: Formatted transcript. Returns empty string if processing fails.
    """
    if not data or 'results' not in data:
        print("Error: Invalid or empty transcript data.")
        return ""

    results = data['results']
    speaker_segments = []
    num_speakers = 0
    debug_mode = False  # Set to True for additional debugging output

    # --- Determine Speaker Count and Get Segments ---
    try:
        if 'speaker_labels' in results:
            speaker_labels_data = results['speaker_labels']
            # Check if it's the list format
            if isinstance(speaker_labels_data, list) and speaker_labels_data:
                speaker_segments = speaker_labels_data[0].get('segments', [])
                # Try to get speaker count if available in this format
                num_speakers = speaker_labels_data[0].get('speakers', 0)
            # Check if it's the dictionary format (older?)
            elif isinstance(speaker_labels_data, dict):
                speaker_segments = speaker_labels_data.get('segments', [])
                num_speakers = speaker_labels_data.get('speakers_count', 0) # Legacy key?

            # If count wasn't explicit, deduce from segments
            if num_speakers == 0 and speaker_segments:
                speaker_labels_set = {segment['speaker_label'] for segment in speaker_segments if 'speaker_label' in segment}
                num_speakers = len(speaker_labels_set)

        # Fallback if speaker_labels structure is missing/empty but items exist
        if num_speakers == 0 and 'items' in results and results['items']:
             all_items = results['items']
             speaker_labels_set = {item['speaker_label'] for item in all_items if 'speaker_label' in item}
             num_speakers = len(speaker_labels_set)
             if num_speakers > 0:
                  print("Warning: Speaker labels structure missing, deduced count from items.")
                  # Try to generate basic segments from items if speaker_segments is empty
                  if not speaker_segments:
                       print("Warning: No segments found, attempting to reconstruct from items (may be less accurate).")
                       # This is complex - best effort: group consecutive items by speaker
                       temp_segments = []
                       current_seg = None
                       for item in all_items:
                           if item.get('type') == 'pronunciation' and 'speaker_label' in item:
                               if current_seg and current_seg['speaker_label'] == item['speaker_label']:
                                   current_seg['end_time'] = item['end_time']
                                   current_seg['items'].append(item)
                               else:
                                   if current_seg: temp_segments.append(current_seg)
                                   current_seg = {
                                       'speaker_label': item['speaker_label'],
                                       'start_time': item['start_time'],
                                       'end_time': item['end_time'],
                                       'items': [item] # Store items for content later
                                   }
                       if current_seg: temp_segments.append(current_seg)
                       speaker_segments = temp_segments # Use reconstructed segments
             else:
                  print("Warning: No speaker labels found anywhere. Processing as single speaker.")
                  num_speakers = 1 # Treat as single speaker

        elif num_speakers == 0:
             print("Error: Could not determine number of speakers.")
             return "" # Cannot proceed without speaker info if expected

    except (KeyError, IndexError, TypeError) as e:
        print(f"Error accessing speaker label data: {e}")
        print("Attempting to process as single speaker.")
        num_speakers = 1 # Fallback

    # --- Get Speaker Names ---
    if num_speakers > 1 and speaker_names is None:
        speaker_names = {}
        # Get unique speaker labels present in the actual segments or items
        present_speaker_labels = set()
        if speaker_segments:
             present_speaker_labels.update(seg.get('speaker_label') for seg in speaker_segments if seg.get('speaker_label'))
        elif results.get('items'):
             present_speaker_labels.update(item.get('speaker_label') for item in results['items'] if item.get('speaker_label'))

        sorted_labels = sorted(list(present_speaker_labels))

        print(f"\nDetected {len(sorted_labels)} unique speaker labels: {', '.join(sorted_labels)}")
        print("Please provide names for each speaker label for better readability.")

        for label in sorted_labels:
            while True:
                name = questionary.text(
                    f"Enter a name for speaker label '{label}':",
                    style=custom_style
                ).ask()
                if name is None: sys.exit("Operation cancelled.") # Handle ctrl+c
                name = name.strip()
                if name:
                    speaker_names[label] = name
                    break
                print("Name cannot be empty. Please try again.")

    elif num_speakers <= 1 and speaker_names is None:
        # Handle single speaker or no speaker labels case
        single_speaker_label = next((seg.get('speaker_label') for seg in speaker_segments if seg.get('speaker_label')), 'spk_0')
        speaker_names = {single_speaker_label: "Speaker"} # Default name

    # --- Process Segments ---
    transcript_parts = []
    current_speaker_name = None
    current_text_parts = []
    all_items = results.get('items', []) # Get top-level items once

    if not speaker_segments and num_speakers == 1 and all_items:
         # Special case: No segments, but items exist, treat as one speaker block
         print("Processing transcript as a single speaker block.")
         words = [item['alternatives'][0]['content']
                  for item in all_items
                  if item.get('type') == 'pronunciation' and item.get('alternatives')]
         if words:
              single_speaker_label = next(iter(speaker_names.keys()), 'spk_0') # Get the label used
              speaker_display_name = speaker_names.get(single_speaker_label, "Speaker")
              return f"{speaker_display_name}: {' '.join(words)}"
         else:
              return "" # No content

    # Map all speaker labels to their segments for easier matching
    speaker_time_ranges = {}
    for segment in speaker_segments:
        speaker_label = segment.get('speaker_label')
        if not speaker_label:
            continue
        
        start_time_str = segment.get('start_time')
        end_time_str = segment.get('end_time')
        
        if not all([start_time_str, end_time_str]):
            continue
            
        try:
            start_time = float(start_time_str)
            end_time = float(end_time_str)
            
            if speaker_label not in speaker_time_ranges:
                speaker_time_ranges[speaker_label] = []
                
            speaker_time_ranges[speaker_label].append((start_time, end_time))
        except ValueError:
            continue
    
    # Second approach: match items to speakers by time ranges
    speaker_texts = {}
    for item in all_items:
        if item.get('type') != 'pronunciation' or not item.get('alternatives'):
            continue
            
        item_start_str = item.get('start_time')
        item_end_str = item.get('end_time')
        
        if not all([item_start_str, item_end_str]):
            continue
            
        try:
            item_start = float(item_start_str)
            item_end = float(item_end_str)
            item_midpoint = (item_start + item_end) / 2
            
            # Try to find which speaker was talking at this time
            matched_speaker = None
            
            # First try speaker_label in the item if it exists
            item_speaker = item.get('speaker_label')
            if item_speaker:
                matched_speaker = item_speaker
            else:
                # Otherwise check time ranges
                for speaker, time_ranges in speaker_time_ranges.items():
                    for start, end in time_ranges:
                        # Use looser matching - only require the midpoint to be in range
                        if item_midpoint >= start and item_midpoint <= end:
                            matched_speaker = speaker
                            break
                    if matched_speaker:
                        break
            
            # If still no match, assign to closest speaker segment
            if not matched_speaker and speaker_time_ranges:
                min_distance = float('inf')
                for speaker, time_ranges in speaker_time_ranges.items():
                    for start, end in time_ranges:
                        if item_midpoint < start:
                            distance = start - item_midpoint
                        elif item_midpoint > end:
                            distance = item_midpoint - end
                        else:
                            distance = 0  # It's within range
                            
                        if distance < min_distance:
                            min_distance = distance
                            matched_speaker = speaker
            
            # If we found a speaker, add the word to their text
            if matched_speaker:
                if matched_speaker not in speaker_texts:
                    speaker_texts[matched_speaker] = []
                    
                speaker_texts[matched_speaker].append(item['alternatives'][0]['content'])
                
        except ValueError:
            continue
    
    # If we got any speaker texts, build the transcript
    if speaker_texts:
        # Order speakers by their first segment's start time
        ordered_speakers = []
        for speaker in speaker_texts.keys():
            # Find earliest segment for this speaker
            if speaker in speaker_time_ranges and speaker_time_ranges[speaker]:
                earliest_time = min(start for start, _ in speaker_time_ranges[speaker])
                ordered_speakers.append((speaker, earliest_time))
        
        # Sort by earliest start time
        ordered_speakers.sort(key=lambda x: x[1])
        
        # Build transcript
        for speaker, _ in ordered_speakers:
            speaker_name = speaker_names.get(speaker, speaker)
            speaker_text = ' '.join(speaker_texts[speaker])
            if speaker_text.strip():
                transcript_parts.append(f"\n{speaker_name}: {speaker_text}")
                
        final_transcript = ''.join(transcript_parts).strip()
        if final_transcript:
            return final_transcript
    
    # If we still don't have a transcript, fall back to the original method
    if debug_mode:
        print(f"DEBUG: {len(speaker_segments)} segments found")
        print(f"DEBUG: {len(all_items)} items found")
        print(f"DEBUG: Speaker time ranges: {speaker_time_ranges}")

    # Fallback if processing yielded nothing but there was data
    if all_items:
         print("Warning: Segment processing yielded empty transcript. Falling back to basic concatenation.")
         words = [item['alternatives'][0]['content']
                  for item in all_items
                  if item.get('type') == 'pronunciation' and item.get('alternatives')]
         if words:
              # Try to use the first speaker name if available
              first_label = next(iter(speaker_names.keys()), 'spk_0')
              speaker_display_name = speaker_names.get(first_label, "Speaker")
              return f"{speaker_display_name}: {' '.join(words)}"
         else:
              return "" # No content found at all
    else:
         print("Warning: No items found in transcript results.")
         return ""

def print_concluding_message(output_file):
    concluding_message = f"""
╔════════════════════════════════════════════════════════════════════╗
║              AWS Transcript Converter - Process Complete!          ║
╚════════════════════════════════════════════════════════════════════╝

Your transcript has been successfully processed and saved to:
{output_file}

Thank you for using the AWS Transcript Converter!
"""
    print(concluding_message)

def run_converter():
    """
    Runs the AWS Transcript Converter in interactive mode.
    Prompts the user to choose a conversion method, processes the transcript,
    displays the formatted transcript, and saves the output.
    """
    print_welcome_message()

    choice = questionary.select(
        "Choose a conversion method:",
        choices=[
            "🗃️ Convert from a JSON file on your computer",
            "☁️ Convert using an AWS Transcribe job (select by bucket)"
        ],
        style=custom_style,
        pointer="👉 "
    ).ask()

    if choice is None: # Handle ctrl+c
         sys.exit("Operation cancelled by user.")

    output_file = None
    data = None
    job_name = None # Initialize job_name

    if choice == "🗃️ Convert from a JSON file on your computer":
        data, json_file = get_transcript_from_file() # Now gets path too
        if data and json_file:
            output_dir = os.path.dirname(json_file)
            base_name = os.path.splitext(os.path.basename(json_file))[0]
            # Sanitize base_name further if needed for filenames
            safe_base_name = re.sub(r'[^\w\-_\. ]', '_', base_name)
            output_file = os.path.join(output_dir, f"{safe_base_name}_processed.txt")
    elif choice == "☁️ Convert using an AWS Transcribe job (select by bucket)":
        data, transcript_uri, job_name = get_transcript_from_bucket()
        if data and job_name:
            # Use the transcription job name for the output file
            safe_job_name = re.sub(r'[^\w\-_\. ]', '_', job_name)
            output_file = os.path.join(os.getcwd(), f"{safe_job_name}_processed.txt")
    else:
        print("Invalid choice.")
        sys.exit(1)

    if not data:
        print("Failed to load transcript data.")
        sys.exit(1)

    if not output_file:
        # Generate a default output filename if somehow it wasn't set
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(os.getcwd(), f"transcript_processed_{timestamp}.txt")
        print(f"Warning: Output file path not determined, using default: {output_file}")


    try:
        # Check if speaker labels exist before calling process_transcript
        has_speaker_labels = 'speaker_labels' in data.get('results', {}) and \
                             data['results']['speaker_labels']
        has_items_with_labels = any('speaker_label' in item for item in data.get('results', {}).get('items', []))

        if has_speaker_labels or has_items_with_labels:
            transcript = process_transcript(data)
        else:
            print("\nWarning: No speaker label information found in the transcript.")
            print("Processing as a single speaker.")
            # Simple concatenation if no speaker labels
            items = data.get('results', {}).get('items', [])
            words = [item['alternatives'][0]['content']
                     for item in items
                     if item.get('type') == 'pronunciation' and item.get('alternatives')]
            transcript = "Speaker: " + ' '.join(words) if words else ""

        # Ensure transcript is a string, not None
        if transcript is None:
            transcript = ""
            print("\nWarning: Processing resulted in empty transcript.")

    except Exception as e:
        # Catch potential errors during processing (like unexpected structure deeper in)
        print(f"\nError processing transcript: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        sys.exit(1)

    if not transcript:
         print("\nWarning: Processed transcript is empty.")
         # Ask user if they still want to save the empty file?
         save_empty = questionary.confirm(
            "Do you want to save the empty transcript file?",
            default=False,
            style=custom_style
         ).ask()
         if not save_empty:
             print("Skipping save for empty transcript.")
             sys.exit(0)

    print("\nProcessed Transcript:")
    print("=" * 50)
    print(transcript)
    print("=" * 50)

    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir: # Check if output_dir is not empty (happens if saving in cwd)
            os.makedirs(output_dir, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f: # Specify encoding
            f.write(transcript)
    except Exception as e:
        print(f"Error saving transcript to '{output_file}': {e}")
        sys.exit(1)

    print_concluding_message(output_file)

if __name__ == "__main__":
    run_converter()
