#!/usr/bin/env python3
import sys
from audio_transcriber import run_transcription_menu, run_converter_json
from vtt_transcript_cleaner import run_cleaner

def print_main_menu():
    menu = """
===========================================
        Transcript Toolkit Main Menu
===========================================
1. Clean a VTT Transcript
2. Start an AWS Transcription Job
3. Convert an AWS Transcribe JSON Transcript
4. Exit
Enter your choice (1-4): """
    return input(menu)

def main():
    while True:
        choice = print_main_menu().strip()
        if choice == '1':
            run_cleaner()
        elif choice == '2':
            run_transcription_menu()
        elif choice == '3':
            run_converter_json()
        elif choice == '4':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a valid number.\n")

if __name__ == '__main__':
    main()
