#!/usr/bin/env python3
import sys
import questionary
from audio_transcriber import run_transcription_menu, run_converter_json
from vtt_transcript_cleaner import run_cleaner
from ui_style import custom_style

def display_welcome():
    banner = r"""                   
                    ✼✼✼✼✼✼                    
                   ✼✼✼✼✼✼✼✼                   
                  ✼✼✼✼✼✼✼✼✼✼                  
               ✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼               
             ✼✼✼✼     ✼✼      ✼✼✼             
          ✼✼✼✼        ✼✼        ✼✼✼✼✼         
     ✼✼✼✼✼✼           ✼✼           ✼✼✼✼✼✼     
   ✼✼✼✼✼✼✼✼           ✼✼          ✼✼✼✼✼✼✼✼✼   
  ✼✼✼✼✼✼✼✼✼✼       ✼✼✼✼✼✼✼✼       ✼✼✼✼✼✼✼✼✼   
   ✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼   
     ✼✼✼✼      ✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼      ✼✼✼✼     
      ✼✼✼        ✼✼✼✼✼✼✼✼✼✼✼✼        ✼✼       
       ✼✼✼        ✼✼✼✼✼✼✼✼✼✼        ✼✼✼       
        ✼✼✼       ✼✼✼✼✼✼✼✼✼✼       ✼✼         
         ✼✼✼     ✼✼✼      ✼✼✼     ✼✼✼         
          ✼✼✼✼✼✼✼✼          ✼✼✼✼✼✼✼✼          
          ✼✼✼✼✼✼✼           ✼✼✼✼✼✼✼✼          
         ✼✼✼✼✼✼✼✼✼          ✼✼✼✼✼✼✼✼✼         
          ✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼✼          
           ✼✼✼✼✼              ✼✼✼✼✼                   
                                              
╔═ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═══ 🎛️ ═══ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═╗
║          Welcome to the AthletiFi Transcript Toolkit!          ║
╚═ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═══ 🎛️ ═══ 🎵 ═══ 🎧 ═══ 🎙️ ═══ 🎚️ ═╝
    """
    print(banner)
    print("Use these tools to clean up transcripts, start new transcription jobs,")
    print("and convert AWS transcripts into clean text.\n")
    print("Perfect for turning meeting recordings and interviews into text")
    print("that works well with AI tools and documentation.\n")

def main_menu():
    return questionary.select(
        "👇 Please choose an option:",
        choices=[
            "🧹 Clean a VTT Transcript",
            "☁️ Transcribe Audio (with AWS Transcribe)",
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
        elif choice == "☁️ Transcribe Audio (with AWS Transcribe)":
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