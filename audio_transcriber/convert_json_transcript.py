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
        str: Formatted transcript.
    """
    try:
        num_speakers = int(data['results']['speaker_labels']['speakers_count'])
    except KeyError:
        speaker_labels = {segment['speaker_label'] for segment in data['results']['speaker_labels']['segments']}
        num_speakers = len(speaker_labels)

    if speaker_names is None:
        speaker_names = {}
        print(f"\nDetected {num_speakers} speakers in the transcript.")
        print("Please provide names for each speaker for better readability.")
        for i in range(num_speakers):
            speaker_label = f"spk_{i}"
            while True:
                name = questionary.text(
                    f"Enter a name for speaker {i+1} (currently labeled as {speaker_label}):",
                    style=custom_style
                ).ask().strip()
                if name:
                    break
                print("Name cannot be empty. Please try again.")
            speaker_names[speaker_label] = name

    transcript_parts = []
    current_speaker = None
    current_text = []

    for segment in data['results']['speaker_labels']['segments']:
        if 'items' not in segment:
            continue
        speaker = segment['speaker_label']
        start_time = float(segment['start_time'])
        end_time = float(segment['end_time'])
        segment_items = []
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
