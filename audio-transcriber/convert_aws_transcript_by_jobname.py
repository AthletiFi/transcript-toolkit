#!/usr/bin/env python3
import json
import sys
import os
import boto3
import time
from botocore.exceptions import ClientError
import urllib.parse
import requests

def print_welcome_message():
    welcome_text = """
    ╔════════════════════════════════════════════════════════════════════╗
    ║           Welcome to AWS Transcript Converter (By Job Name)          ║
    ╚════════════════════════════════════════════════════════════════════╝

    This script converts AWS Transcribe job output into a readable format.
    It will help you:
      1. Process speaker-separated transcripts directly from AWS.
      2. Name your speakers for better readability.
      3. Save the result in a clean text format.

    Please ensure you have:
      • AWS credentials configured.
      • Your transcription job name ready.

    Let's get started!
    """
    print(welcome_text)

def get_transcription_job():
    """
    Prompt the user for an AWS Transcribe job name and fetch its transcript data.

    Returns:
        tuple: (transcript_data, job_name)
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
                    transcript_data = json.loads(s3_response['Body'].read().decode('utf-8'))
                else:
                    req_response = requests.get(transcript_uri)
                    transcript_data = req_response.json()
                return transcript_data, job_name

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
                        transcript_data = json.loads(s3_response['Body'].read().decode('utf-8'))
                    else:
                        req_response = requests.get(transcript_uri)
                        transcript_data = req_response.json()
                    return transcript_data, job_name
                else:
                    print(f"Job failed: {response['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
        except ClientError as e:
            print(f"Error accessing AWS: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")

        retry = input("\nWould you like to try another job name? (y/n): ").lower().strip()
        if retry != 'y':
            sys.exit(1)

def process_transcript(transcript_data, speaker_names=None):
    """
    Process AWS Transcribe output into a readable transcript with speaker labels.

    Args:
        transcript_data (dict): AWS Transcribe output.
        speaker_names (dict): Optional mapping of speaker labels to names.

    Returns:
        tuple: (formatted transcript as str, speaker_names dictionary)
    """
    # Determine number of speakers
    try:
        num_speakers = int(transcript_data['results']['speaker_labels']['speakers_count'])
    except KeyError:
        speaker_labels = {segment['speaker_label'] for segment in transcript_data['results']['speaker_labels']['segments']}
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

    for segment in transcript_data['results']['speaker_labels']['segments']:
        # Skip segments without items
        if 'items' not in segment:
            continue

        speaker = segment['speaker_label']
        start_time = float(segment['start_time'])
        end_time = float(segment['end_time'])

        segment_items = []
        for item in transcript_data['results']['items']:
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
    return final_transcript, speaker_names

def print_concluding_message(output_file):
    concluding_message = f"""
    ╔════════════════════════════════════════════════════════════════════╗
    ║  AWS Transcript Converter (By Job Name) - Process Complete!          ║
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
    Runs the AWS Transcript Converter (By Job Name) in interactive mode.
    Prompts for a transcription job name, processes the transcript, and saves the output.
    """
    print_welcome_message()

    try:
        transcript_data, job_name = get_transcription_job()
    except Exception as e:
        print(f"Error retrieving transcription job: {e}")
        return

    try:
        transcript, speaker_names = process_transcript(transcript_data)
    except Exception as e:
        print(f"Error processing transcript: {e}")
        return

    print("\nProcessed Transcript:")
    print("=" * 50)
    print(transcript)
    print("=" * 50)

    output_file = f"{job_name}.txt"
    try:
        with open(output_file, 'w') as f:
            f.write(transcript)
    except Exception as e:
        print(f"Error saving transcript: {e}")
        return

    print_concluding_message(output_file)

if __name__ == "__main__":
    run_converter()
