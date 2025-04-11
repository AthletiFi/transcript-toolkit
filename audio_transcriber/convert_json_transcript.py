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
        num_speakers = 1 

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
    
    if choice == "🗃️ Convert from a JSON file on your computer":
        data = get_transcript_from_file()
        # Retrieve the file path again (or store it from the initial prompt)
        json_file = get_valid_file_path()
        output_dir = os.path.dirname(json_file)
        base_name = os.path.splitext(os.path.basename(json_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_processed.txt")
    else:
        data, transcript_uri, job_name = get_transcript_from_bucket()
        # Use the transcription job name for the output file
        output_file = os.path.join(os.getcwd(), f"{job_name}_processed.txt")
    
    try:
        transcript = process_transcript(data)
    except Exception as e:
        print(f"Error processing transcript: {e}")
        sys.exit(1)
    
    print("\nProcessed Transcript:")
    print("=" * 50)
    print(transcript)
    print("=" * 50)
    
    try:
        with open(output_file, 'w') as f:
            f.write(transcript)
    except Exception as e:
        print(f"Error saving transcript: {e}")
        sys.exit(1)
    
    print_concluding_message(output_file)

if __name__ == "__main__":
    run_converter()
