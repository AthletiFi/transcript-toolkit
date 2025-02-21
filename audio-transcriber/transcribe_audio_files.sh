#!/bin/bash

check_dependencies() {
    echo "Checking dependencies..."
    
    # Check if Python3 is installed
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 is required but not installed."
        echo "Please install Python 3 using: brew install python3"
        exit 1
    fi

    # Check if pip3 is installed
    if ! command -v pip3 &> /dev/null; then
        echo "Error: pip3 is required but not installed."
        echo "Please install pip3 and try again."
        exit 1
    fi

    # Check if virtual environment exists, create if it doesn't
    VENV_DIR="$HOME/.aws_transcribe_venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment for AWS Transcriber..."
        python3 -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create virtual environment."
            exit 1
        fi
    fi

    # Activate virtual environment - using '.' instead of 'source' allows it to be more portable across different shells that support POSIX.
    . "$VENV_DIR/bin/activate"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to activate virtual environment."
        exit 1
    fi

    # Check if boto3 is installed in virtual environment, install if missing
    if ! python3 -c "import boto3" &> /dev/null; then
        echo "boto3 package not found. Installing in virtual environment..."
        if pip3 install boto3; then
            echo "Successfully installed boto3"
        else
            echo "Error: Failed to install boto3. Please try manually using:"
            echo ". $VENV_DIR/bin/activate && pip3 install boto3"
            deactivate
            exit 1
        fi
    fi

    # Check if requests is installed in virtual environment, install if missing
    if ! python3 -c "import requests" &> /dev/null; then
        echo "requests package not found. Installing in virtual environment..."
        if pip3 install requests; then
            echo "Successfully installed requests"
        else
            echo "Error: Failed to install requests. Please try manually using:"
            echo ". $VENV_DIR/bin/activate && pip3 install requests"
            deactivate
            exit 1
        fi
    fi

    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        echo "Error: AWS CLI is required but not installed."
        echo "Please install AWS CLI using: brew install awscli"
        echo "Then configure it with: aws configure"
        deactivate
        exit 1
    fi

    # Check AWS CLI configuration
    if ! aws configure list | grep -q "access_key"; then
        echo "Error: AWS CLI is not configured. Please configure it using: aws configure"
        deactivate
        exit 1
    fi
}

cleanup() {
    # Deactivate virtual environment if it's active
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate
    fi
}

# Set up trap to ensure virtual environment is deactivated on exit
trap cleanup EXIT

print_welcome_message() {
    cat << "EOF"
    ╔════════════════════════════════════════════════════════════════╗
    ║                 Welcome to AWS Audio Transcriber               ║
    ╚════════════════════════════════════════════════════════════════╝

    Hey there! 👋 Ready to transcribe some audio?

    This tool uses the magic of AWS Transcribe to turn your audio files into text.

    Before we begin, make sure you have:
    ✦ AWS CLI set up and ready to go.
    ✦ Python 3 and the `boto3` package installed.

EOF
    print_menu
}

print_menu() {
    cat << "EOF"
    
    What do you want to do today?
    ┌──────────────────────────────────────────┐
    │           Available Options:             │
    └──────────────────────────────────────────┘
    1. ☁️ Transcribe from S3: Create a new transcription job from an S3 audio file or directory.
    2. 📄 Convert Local Transcript: Process a local JSON transcript file.
    3. 🆔 Convert by Job Name: Process a transcript using its AWS Transcribe job name.
    4. ⬆️ Upload and Transcribe: Upload a local audio file and transcribe it.
    5. 🚪 Exit

    Please enter your choice (1-5): 
EOF
}

create_job_name() {
    local KEY="$1"
    echo "$KEY" | tr -cs '[:alnum:]' '-' | sed 's/-*$//;s/^-*//' | sed 's/\.[^.]*$//'
}

process_single_file() {
    local S3_PATH="$1"
    local BUCKET="$2"
    local KEY="$3"

    local job_name
    job_name=$(create_job_name "$KEY")
    
    echo "----------------------------------------"
    echo "File: $KEY"
    echo "Job name will be: $job_name"
    
    while true; do
        read -p "Enter number of speakers (2-30), '0' or 'skip' to skip this file: " speaker_count </dev/tty
        if [ "$speaker_count" = "skip" ] || [ "$speaker_count" = "0" ]; then
            echo "Skipping $KEY"
            return 0
        elif [[ "$speaker_count" =~ ^[0-9]+$ ]] && [ "$speaker_count" -ge 2 ] && [ "$speaker_count" -le 30 ]; then
            break
        else
            echo "Please enter a valid number between 2 and 30, '0' or 'skip'"
        fi
    done
    
    echo "Starting transcription job with $speaker_count speakers..."
    
    aws transcribe start-transcription-job \
        --transcription-job-name "$job_name" \
        --language-code "en-US" \
        --media-format "${KEY##*.}" \
        --media "MediaFileUri=s3://${BUCKET}/${KEY}" \
        --settings "{
            \"ShowSpeakerLabels\": true,
            \"MaxSpeakerLabels\": $speaker_count,
            \"ChannelIdentification\": true
        }"
    
    if [ $? -eq 0 ]; then
        echo "Successfully started transcription job for $KEY"
        echo "You can process this job later using option 3 from the main menu."
    else
        echo "Failed to start transcription job for $KEY"
        echo "Please check your AWS credentials and permissions"
    fi
}

create_transcription_job() {
    echo "Starting new transcription job..."
    
    read -p "Enter S3 path (e.g., s3://bucket-name/path/ or s3://bucket-name/path/file.mp3 or bucket-name/path/ or bucket-name/path/file.mp3): " S3_PATH
    
    # Remove 's3://' prefix if present
    S3_PATH=${S3_PATH#s3://}

    # Remove trailing slash if present
    S3_PATH=${S3_PATH%/}

    # Validate basic format (after removing prefix)
    if [[ ! $S3_PATH =~ ^[^\/]+\/ ]]; then
        echo "Error: Invalid S3 path format. Must include a bucket name and a path."
        return 1
    fi

    # Extract bucket and key/prefix
    BUCKET=$(echo "$S3_PATH" | sed -n 's/^\([^\/]*\).*/\1/p')
    KEY=$(echo "$S3_PATH" | sed 's/^[^\/]*\///')

    # Check if the path exists
    if ! aws s3 ls "s3://${BUCKET}/${KEY}" &>/dev/null; then
        echo "Error: Path not found in S3"
        return 1
    fi

    # Check if it's a single file by looking for an audio extension
    if [[ $KEY =~ \.(m4a|mp3|mp4|wav|flac|ogg|webm)$ ]]; then
        process_single_file "$S3_PATH" "$BUCKET" "$KEY"
    else
        # It's a directory - list all audio files
        echo "Searching for audio files in: $S3_PATH"
        
        # Use AWS CLI to list files and filter for audio extensions
        files=$(aws s3 ls "s3://${BUCKET}/${KEY}/" | awk '/\.(m4a|mp3|mp4|wav|flac|ogg|webm)$/ {print $4}')
        
        if [ -z "$files" ]; then
            echo "No audio files found in the specified S3 path."
            return 1
        fi

        echo "$files" | while IFS= read -r filename; do
            # Skip if empty
            [ -z "$filename" ] && continue
            process_single_file "$S3_PATH/$filename" "$BUCKET" "${KEY:+$KEY/}$filename"
            
            # Add a small delay to avoid hitting API rate limits
            sleep 2
        done
    fi

    echo "All files processed. Returning to main menu..."
}

upload_and_transcribe() {
    echo "Upload and transcribe local audio file..."

    # Prompt for local file path
    read -p "Enter path to local audio file: " LOCAL_FILE_PATH

    # Validate file exists
    if [ ! -f "$LOCAL_FILE_PATH" ]; then
        echo "Error: File not found."
        return 1
    fi

    # Prompt for bucket name with default
    read -p "Enter S3 bucket name (default: s3://internal-audio-recordings): " BUCKET

    # Use default bucket if none provided
    if [ -z "$BUCKET" ]; then
        BUCKET="internal-audio-recordings"
    fi

    # Remove 's3://' prefix if present
    BUCKET=${BUCKET#s3://}

    FILENAME=$(basename "$LOCAL_FILE_PATH")

    echo "Uploading $FILENAME to s3://$BUCKET..."
    aws s3 cp "$LOCAL_FILE_PATH" "s3://$BUCKET/$FILENAME"

    if [ $? -eq 0 ]; then
        echo "Upload successful!"
        process_single_file "s3://$BUCKET/$FILENAME" "$BUCKET" "$FILENAME"
    else
        echo "Error uploading file to S3."
        return 1
    fi
}

print_completion_message() {
    cat << "EOF"

    Thank you for using the AWS Audio Transcriber!
    
    ┌──────────────────────────────────────────┐
    │            Process Complete!             │
    └──────────────────────────────────────────┘
    
    Returning to main menu...
EOF
}

# Main program loop
check_dependencies
print_welcome_message

while true; do
    read -p "Enter your choice: " choice
    
    case $choice in
        1)
            create_transcription_job
            print_menu
          ;;
        2)
            echo "Converting local JSON transcript file..."
            if [ ! -f "convert-aws-transcript.py" ]; then
                echo "Error: convert-aws-transcript.py not found."
            else
                python3 convert-aws-transcript.py
                print_completion_message
            fi
            print_menu
          ;;
        3)
            echo "Converting transcript using job name..."
            if [ ! -f "convert-aws-transcript-by-jobname.py" ]; then
                echo "Error: convert-aws-transcript-by-jobname.py not found."
            else
                python3 convert-aws-transcript-by-jobname.py
                print_completion_message
            fi
            print_menu
          ;;
        4)
            upload_and_transcribe
            print_completion_message
            print_menu
          ;;
        5)
            echo "Thank you for using AWS Audio Transcriber. Goodbye!"
            exit 0
          ;;
        *)
            echo "Invalid choice. Please enter 1, 2, 3, 4, or 5."
            print_menu
          ;;
    esac
done