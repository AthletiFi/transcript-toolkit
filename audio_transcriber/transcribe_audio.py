#!/usr/bin/env python3
"""
transcribe_audio.py

This module provides an interactive interface to start an AWS Transcribe job.
It lets you choose between uploading a local audio file to S3 and transcribing it, or using an existing S3 URI for transcription.
"""

import re
import time
import os
import boto3
import questionary
from botocore.exceptions import ClientError
from ui_style import custom_style

def print_welcome_message():
    welcome_text = """
╔═ 🎤 ═══ ☁️ ═══ 🔊 ═══ 📡 ═══ 🎤 ═══ ☁️ ═══ 🔊 ═══ 📡 ═══ 🎤 ═╗
║          Transcribe Audio (with AWS Transcribe)          ║
╚═ 🎤 ═══ ☁️ ═══ 🔊 ═══ 📡 ═══ 🎤 ═══ ☁️ ═══ 🔊 ═══ 📡 ═══ 🎤 ═╝

"""
    print(welcome_text)

def check_aws_configuration():
    """
    Verify that AWS credentials are configured.
    """
    session = boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise Exception("AWS credentials not found. Please configure AWS CLI.")
    return True

def create_job_name(s3_path):
    """
    Create a transcription job name based on the S3 file name.
    """
    filename = s3_path.split("/")[-1]
    base_name = filename.split(".")[0]
    job_name = re.sub(r'[^a-zA-Z0-9_-]', '-', base_name)
    if not job_name:
        job_name = "transcription-job"
    return job_name

def start_transcription_job(s3_path, speaker_count):
    """
    Start an AWS Transcribe job with the specified S3 path and speaker count.
    """
    client = boto3.client('transcribe')
    job_name = create_job_name(s3_path)
    media_format = s3_path.split('.')[-1].lower()
    try:
        response = client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_path},
            MediaFormat=media_format,
            LanguageCode='en-US',
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': speaker_count,
                'ChannelIdentification': True
            }
        )
        return response
    except client.exceptions.ConflictException:
        # Add a timestamp if job name already exists.
        job_name = f"{job_name}-{int(time.time())}"
        response = client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_path},
            MediaFormat=media_format,
            LanguageCode='en-US',
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': speaker_count,
                'ChannelIdentification': True
            }
        )
        return response
    except Exception as e:
        raise Exception(f"Failed to start transcription job: {e}")

def validate_bucket_exists(bucket_name):
    """
    Check if an S3 bucket exists and is accessible.
    """
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            raise Exception(f"Bucket '{bucket_name}' does not exist")
        elif error_code == '403':
            raise Exception(f"No permission to access bucket '{bucket_name}'")
        raise Exception(f"Error accessing bucket: {e}")
    except Exception as e:
        raise Exception(f"Bucket validation failed: {e}")

def upload_audio_file(local_file_path, bucket, object_name=None):
    """
    Upload a local audio file to the specified S3 bucket.
    """
    s3 = boto3.client('s3')
    if object_name is None:
        object_name = os.path.basename(local_file_path)
    try:
        if not os.path.isfile(local_file_path):
            raise FileNotFoundError(f"Local file '{local_file_path}' not found")
            
        print(f"Uploading {local_file_path} to bucket {bucket}...")
        s3.upload_file(local_file_path, bucket, object_name)
        s3_uri = f"s3://{bucket}/{object_name}"
        print("✓ Upload successful!")
        return s3_uri
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            raise Exception(f"Permission denied writing to bucket '{bucket}'")
        raise Exception(f"AWS upload error: {e}")
    except Exception as e:
        raise Exception(f"Upload failed: {e}")

def run_transcription_menu():
    """
    Runs the AWS Audio Transcriber module in interactive mode.
    """
    print_welcome_message()
    
    try:
        check_aws_configuration()
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    option = questionary.select(
        "Choose a transcription method:",
        choices=[
            "Upload a local audio file from computer",
            "Use S3 URI for an audio file hosted on S3"
        ],
        style=custom_style,
        pointer="👉 "
    ).ask()

    s3_path = None
    try:
        if option == "Upload a local audio file from computer":
            local_file = questionary.text(
                "Enter the local file path (e.g., /path/to/file.mp3):",
                style=custom_style
            ).ask().strip()
            
            if not os.path.isfile(local_file):
                print(f"❌ Error: File '{local_file}' not found")
                return

            bucket = questionary.text(
                "Enter the target S3 bucket name (leave blank for default 'internal-audio-recordings'):",
                style=custom_style
            ).ask().strip() or "internal-audio-recordings"

            try:
                validate_bucket_exists(bucket)
            except Exception as e:
                print(f"❌ {e}")
                return

            try:
                s3_path = upload_audio_file(local_file, bucket)
            except Exception as e:
                print(f"❌ {e}")
                return
        else:
            s3_path = questionary.text(
                "Enter the S3 URI (e.g., s3://bucket/path/to/file.mp3):",
                style=custom_style
            ).ask().strip()
            if not s3_path.startswith("s3://"):
                print("❌ Invalid S3 URI. It should start with 's3://'.")
                return

        speaker_input = questionary.text(
            "Enter number of speakers (between 2 and 30):",
            style=custom_style
        ).ask()
        try:
            speaker_count = int(speaker_input)
            if speaker_count < 2 or speaker_count > 30:
                print("Speaker count should be between 2 and 30. Defaulting to 2.")
                speaker_count = 2
        except ValueError:
            print("Invalid input for speaker count. Defaulting to 2 speakers.")
            speaker_count = 2

        print("Starting transcription job...")
        try:
            response = start_transcription_job(s3_path, speaker_count)
            job_name = response.get('TranscriptionJob', {}).get('TranscriptionJobName', 'Unknown')
            print("✓ Transcription job started successfully!")
            print("Job Name:", job_name)
        except Exception as e:
            print(f"❌ Error: {e}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == '__main__':
    run_transcription_menu()