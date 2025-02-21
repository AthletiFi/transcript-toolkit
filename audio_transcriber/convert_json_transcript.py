#!/usr/bin/env python3
"""
convert_json_transcript.py

This module converts AWS Transcribe JSON output into a readable transcript.
It supports two methods for obtaining the transcript data:
  1. Converting from a local JSON file.
  2. Converting by providing an AWS Transcribe job name (retrieves transcript from AWS).

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

def print_welcome_message():
    welcome_text = """
╔════════════════════════════════════════════════════════════════════╗
║                   Welcome to AWS Transcript Converter                ║
╚════════════════════════════════════════════════════════════════════╝

This tool converts AWS Transcribe JSON output into a readable transcript.
You can choose to:
  1. Convert from a local JSON file.
  2. Convert by providing an AWS Transcribe job name.

Let's get started!
"""
    print(welcome_text)

def sanitize_path(input_path):
    """
    Sanitize and validate the input file path.
    Handles both escaped paths and quoted paths.
    
    Args:
        input_path (str): Raw input path.
        
    Returns:
        str: Sanitized path if valid.
        
    Raises:
        FileNotFoundError: If path is invalid or file doesn't exist.
    """
    # Strip whitespace and surrounding quotes
    path = input_path.strip().strip("'\"")
    # Handle doubled backslashes that can occur from shell input
    path = path.replace("\\\\", "\\")
    
    # Create variations of the path to try
    paths_to_try = [
        path,  # Original path
        path.replace("\\ ", " ").replace("\\(", "(").replace("\\)", ")"),  # Unescaped spaces and parentheses
        re.sub(r'\\(.)', r'\1', path),  # Unescape all special characters
    ]
    
    # Try each variation
    paths_tried = set()
    for p in paths_to_try:
        p = p.strip()
        if p in paths_tried:
            continue
        paths_tried.add(p)
        if os.path.exists(p):
            return p
    
    raise FileNotFoundError(
        f"Could not find the file. You can specify the path either:\n"
        f"1. With escaped special characters: /path/to/my\\ file\\(1\\).json\n"
        f"2. In quotes: '/path/to/my file (1).json'"
    )

def get_valid_file_path():
    """
    Repeatedly prompt for a valid file path until one is provided.
    
    Returns:
        str: Valid, sanitized file path.
    """
    print("\n┌─ File Input ───────────────────────────────────────────────────┐")
    print("│ You can enter the path either:                                  │")
    print("│ • With escaped spaces: /path/to/my\\ file\\(1\\).json            │")
    print("│ • In quotes: '/path/to/my file (1).json'                          │")
    print("└──────────────────────────────────────────────────────────────────┘")
    
    while True:
        try:
            file_path = input("\nPlease enter the path to your AWS Transcribe JSON file: ")
            return sanitize_path(file_path)
        except FileNotFoundError as e:
            print(f"\nError: {e}")
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            raise

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

def get_transcript_from_job():
    """
    Prompt the user for an AWS Transcribe job name and retrieve its transcript data.
    
    Returns:
        dict: Transcript data retrieved from AWS.
    """
    while True:
        job_name = input("\nPlease enter your AWS Transcribe job name: ").strip()
        if not job_name:
            print("Job name cannot be empty. Please try again.")
            continue

        try:
            transcribe_client = boto3.client('transcribe')
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            status = response['TranscriptionJob']['TranscriptionJobStatus']

            if status == 'COMPLETED':
                transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                parsed_uri = urllib.parse.urlparse(transcript_uri)
                if parsed_uri.netloc == 's3.amazonaws.com':
                    path_parts = parsed_uri.path.lstrip('/').split('/')
                    bucket = path_parts[0]
                    key = '/'.join(path_parts[1:])
                    s3_client = boto3.client('s3')
                    s3_response = s3_client.get_object(Bucket=bucket, Key=key)
                    data = json.loads(s3_response['Body'].read().decode('utf-8'))
                else:
                    req_response = requests.get(transcript_uri)
                    data = req_response.json()
                return data
            elif status == 'FAILED':
                print(f"Transcription job failed: {response['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
            else:
                print(f"Transcription job is currently {status}.")

            wait_choice = input("Would you like to wait for the job to complete? (y/n): ").lower().strip()
            if wait_choice == 'y' and status != 'FAILED':
                print("Waiting for job to complete...", end='', flush=True)
                while status not in ['COMPLETED', 'FAILED']:
                    time.sleep(30)
                    print(".", end='', flush=True)
                    response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                    status = response['TranscriptionJob']['TranscriptionJobStatus']
                print("\n")
                if status == 'COMPLETED':
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    parsed_uri = urllib.parse.urlparse(transcript_uri)
                    if parsed_uri.netloc == 's3.amazonaws.com':
                        path_parts = parsed_uri.path.lstrip('/').split('/')
                        bucket = path_parts[0]
                        key = '/'.join(path_parts[1:])
                        s3_client = boto3.client('s3')
                        s3_response = s3_client.get_object(Bucket=bucket, Key=key)
                        data = json.loads(s3_response['Body'].read().decode('utf-8'))
                    else:
                        req_response = requests.get(transcript_uri)
                        data = req_response.json()
                    return data
                else:
                    print(f"Job failed: {response['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
        except ClientError as e:
            print(f"Error accessing AWS: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")

        retry = input("Would you like to try another job name? (y/n): ").lower().strip()
        if retry != 'y':
            sys.exit(1)

def process_transcript(data, speaker_names=None):
    """
    Process AWS Transcribe output into a readable transcript with speaker labels.
    
    This function expects the data to include 'speaker_labels' and 'items' in the results.
    
    Args:
        data (dict): AWS Transcribe output.
        speaker_names (dict): Optional mapping of speaker labels to names.
    
    Returns:
        str: Formatted transcript.
    """
    # Determine number of speakers
    try:
        num_speakers = int(data['results']['speaker_labels']['speakers_count'])
    except KeyError:
        speaker_labels = {segment['speaker_label'] for segment in data['results']['speaker_labels']['segments']}
        num_speakers = len(speaker_labels)

    if speaker_names is None:
        speaker_names = {}
        print(f"\n┌─ Speaker Names ─────────────────────────────────────────────────┐")
        print(f"│ Detected {num_speakers} speakers in the transcript.              │")
        print("│ Please provide names for each speaker for better readability.      │")
        print("└────────────────────────────────────────────────────────────────────┘")
        for i in range(num_speakers):
            speaker_label = f"spk_{i}"
            while True:
                name = input(f"\nPlease enter a name for speaker {i+1} (currently labeled as {speaker_label}): ").strip()
                if name:
                    break
                print("Name cannot be empty. Please try again.")
            speaker_names[speaker_label] = name

    transcript_parts = []
    current_speaker = None
    current_text = []

    # Process segments based on speaker labels
    for segment in data['results']['speaker_labels']['segments']:
        # Skip segments without items (if applicable)
        if 'items' not in segment:
            continue
        speaker = segment['speaker_label']
        start_time = float(segment['start_time'])
        end_time = float(segment['end_time'])
        segment_items = []
        # Gather words from items that fall within the segment's time range
        for item in data['results'].get('items', []):
            if 'start_time' not in item or 'end_time' not in item:
                continue
            item_start = float(item['start_time'])
            item_end = float(item['end_time'])
            if item_start >= start_time and item_end <= end_time:
                segment_items.append(item['alternatives'][0]['content'])
        if current_speaker is not None and current_speaker != speaker:
            speaker_name = speaker_names.get(current_speaker, current_speaker)
            transcript_parts.append(f"\n{speaker_name}: {' '.join(current_text)}")
            current_text = []
        current_speaker = speaker
        current_text.extend(segment_items)

    if current_text:
        speaker_name = speaker_names.get(current_speaker, current_speaker)
        transcript_parts.append(f"\n{speaker_name}: {' '.join(current_text)}")

    final_transcript = ''.join(transcript_parts).strip()
    return final_transcript

def print_concluding_message(output_file):
    concluding_message = f"""
╔════════════════════════════════════════════════════════════════════╗
║              AWS Transcript Converter - Process Complete!          ║
╚════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────┐
│ Your transcript has been successfully processed and saved to:     │
│ {output_file}
└──────────────────────────────────────────────────────────────────┘

Thank you for using the AWS Transcript Converter!
"""
    print(concluding_message)

def run_converter():
    """
    Runs the unified AWS Transcript Converter in interactive mode.
    Prompts the user to choose the method for obtaining the transcript,
    processes it, displays the formatted transcript, and saves the output.
    """
    print_welcome_message()
    print("How would you like to convert the transcript?")
    print("1. Convert using a local JSON file")
    print("2. Convert using an AWS Transcribe job name")
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == '1':
        data = get_transcript_from_file()
    elif choice == '2':
        data = get_transcript_from_job()
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)
    
    try:
        transcript = process_transcript(data)
    except Exception as e:
        print(f"Error processing transcript: {e}")
        sys.exit(1)
    
    print("\nProcessed Transcript:")
    print("=" * 50)
    print(transcript)
    print("=" * 50)
    
    # Determine an output file name based on input method
    if choice == '1':
        # Use the input file's base name for local JSON
        json_file = get_valid_file_path()
        output_dir = os.path.dirname(json_file)
        base_name = os.path.splitext(os.path.basename(json_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_processed.txt")
    else:
        # Use the job name (if available) or default
        output_file = "converted_transcript.txt"
    
    try:
        with open(output_file, 'w') as f:
            f.write(transcript)
    except Exception as e:
        print(f"Error saving transcript: {e}")
        sys.exit(1)
    
    print_concluding_message(output_file)

if __name__ == "__main__":
    run_converter()
