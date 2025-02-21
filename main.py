#!/usr/bin/env python3
import sys
import questionary
from audio_transcriber import run_transcription_menu, run_converter_json
from vtt_transcript_cleaner import run_cleaner
from ui_style import custom_style

def display_welcome():
    banner = r"""
╔═ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═══ 🎛️ ═══ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═╗
║             Welcome to the Transcript Toolkit!            ║
╚═ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═══ 🎛️ ═══ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═╝
    """
    print(banner)
    print("A unified tool for cleaning VTT transcripts, starting AWS Transcription jobs,")
    print("and converting AWS Transcribe JSON transcripts.\n")

def main_menu():
    return questionary.select(
        "👇 Please choose an option:",
        choices=[
            "🧹 Clean a VTT Transcript",
            "☁️ Start an AWS Transcription Job",
            "🔄 Convert an AWS Transcribe JSON Transcript",
            "🚪 Exit"
        ],
        style=custom_style,
        pointer="👉 "
    ).ask()

def main():
    display_welcome()
    while True:
        choice = main_menu()
        if choice == "🧹 Clean a VTT Transcript":
            run_cleaner()
        elif choice == "☁️ Start an AWS Transcription Job":
            run_transcription_menu()
        elif choice == "🔄 Convert an AWS Transcribe JSON Transcript":
            run_converter_json()
        elif choice == "🚪 Exit":
            print("👋 Goodbye! See you next time!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please select a valid option.\n")

if __name__ == '__main__':
    main()
