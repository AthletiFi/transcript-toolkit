# AthletiFi AWS Audio Transcription Tools

A collection of tools for transcribing audio files using AWS Transcribe service. This toolset includes scripts for processing audio files, managing transcription jobs, and converting AWS transcripts into readable formats.

## Features

- Automated audio file transcription using AWS Transcribe
- Support for multiple audio formats (MP3, WAV, M4A, FLAC, MP4, OGG, WebM)
- Speaker detection and labeling
- Conversion of AWS JSON transcripts to readable text format
- Support for both local file processing and direct AWS job management

## Prerequisites

- Python 3.x
- AWS CLI configured with appropriate permissions
- Required Python packages:
  - boto3
  - requests

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/AthletiFi/aws-audio-transcribe.git
   ```

2. Navigate to the project directory:

   ```bash
   cd aws-audio-transcribe
   ```

3. Install required Python packages:

   ```bash
   pip install boto3 requests
   ```

## Usage

### Transcribing Audio Files

Run the main transcription script:

```bash
./transcribe_audio_files.sh
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.