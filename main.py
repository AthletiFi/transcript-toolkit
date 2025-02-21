#!/usr/bin/env python3
import sys

# Import functions from our modules.
# If you haven't renamed the directories, you might need to rename them to use underscores:
# e.g., "audio_transcriber" instead of "audio-transcriber" and "vtt_transcript_cleaner" instead of "vtt-transcript-cleaner"
from audio_transcriber import transcribe_audio, convert_json_transcript, convert_json_transcript_by_jobname
from vtt_transcript_cleaner import vtt_transcript_cleaner

def print_main_menu():
    menu = """
===========================================
        Transcript Toolkit Main Menu
===========================================
1. Clean a VTT Transcript
2. Start an AWS Transcription Job
3. Convert AWS Transcribe JSON Transcript
4. Convert AWS Transcript by Job Name
5. Exit
Enter your choice (1-5): """
    return input(menu)

def main():
    while True:
        choice = print_main_menu().strip()
        if choice == '1':
            # Run VTT Transcript Cleaner
            vtt_transcript_cleaner.run_cleaner()
        elif choice == '2':
            # Run the AWS Transcription Job module
            transcribe_audio.run_transcription_menu()
        elif choice == '3':
            # Run the AWS JSON Transcript Converter
            convert_json_transcript.run_converter()
        elif choice == '4':
            # Run the AWS Transcript Converter by Job Name
            convert_json_transcript_by_jobname.run_converter()
        elif choice == '5':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number between 1 and 5.\n")

if __name__ == '__main__':
    main()
