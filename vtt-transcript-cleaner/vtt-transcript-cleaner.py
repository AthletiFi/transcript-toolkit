import re
import sys
import os
import time

def print_welcome_message():
    """Display stylized welcome message and script description."""
    welcome_text = """
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                   Welcome to VTT Transcript Cleaner!                       ║
    ╚════════════════════════════════════════════════════════════════════════════╝

    This script helps clean up VTT transcripts by removing unnecessary formatting
    and converting them to a clean text format suitable for AI analysis.

    ┌──────────────────────────────────────────┐
    │           Before You Begin:              │
    └──────────────────────────────────────────┘
    1. Ensure you have your VTT transcript file ready
    2. The script will create a new cleaned text file
    3. Original files will not be modified

    ┌──────────────────────────────────────────┐
    │            What This Script Does:        │
    └──────────────────────────────────────────┘
    ✦ Removes timestamp lines
    ✦ Removes UUID/number lines
    ✦ Removes <v> tags
    ✦ Combines continuous speaker lines
    ✦ Converts remaining formatting to plain text
    ✦ Creates a new cleaned file with "_cleaned.txt" suffix

    Let's begin cleaning your transcript!
    """
    print(welcome_text)

def print_concluding_message(output_file):
    """Display stylized conclusion message with next steps."""
    concluding_message = f"""
    ┌──────────────────────────────────────────┐
    │               Process Complete!          │
    └──────────────────────────────────────────┘
    Your transcript has been successfully cleaned and saved!
    ✦ Cleaned transcript saved to: {output_file}
    ✦ The file is now ready for AI analysis
    ✦ Original VTT file has not been modified

    ┌──────────────────────────────────────────┐
    │               Next Steps:                │
    └──────────────────────────────────────────┘
    1. Verify the cleaned transcript file
    2. Check that all dialogue is preserved
    3. Proceed with using the transcript with Claude or other AI assistants

    Thank you for using the VTT Transcript Cleaner!
    """
    print(concluding_message)

def show_progress(message):
    """Show a loading animation with message."""
    animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(10):
        sys.stdout.write(f"\r{animation[i]} {message}")
        sys.stdout.flush()
        time.sleep(0.04)
    sys.stdout.write("\r✓ " + message + "\n")
    sys.stdout.flush()

def verify_file_exists(path):
    """Verify file existence by attempting to open the file."""
    try:
        with open(path, 'r') as f:
            return True
    except (IOError, OSError):
        return False

def sanitize_path(input_path):
    """Sanitize the file path by handling special characters and spaces."""
    try:
        # Remove quotes if present
        path = input_path.strip('\'"')
        
        # Remove escape characters
        path = re.sub(r'\\(.)', r'\1', path)
        
        # Remove any trailing spaces
        path = path.rstrip()
        
        # Verify file exists
        if verify_file_exists(path):
            return path
        else:
            raise FileNotFoundError(f"File not found: {path}")
            
    except Exception as e:
        print(f"Debug: Error during path processing: {str(e)}")
        raise FileNotFoundError(f"Error processing path: {str(e)}")

def combine_speaker_lines(content):
    """
    Combine consecutive lines from the same speaker using two simple patterns:
    1. Lines without speaker names following a speaker line are continuations
    2. Consecutive lines with the same speaker name should be combined
    """
    # First pass: Combine lines that don't start with a speaker name with their previous speaker line
    lines = content.split('\n')
    combined_lines = []
    current_line = None
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_line:
                combined_lines.append(current_line)
                current_line = None
            continue
            
        # Check if line starts with a speaker (contains ':' with text before it)
        if ':' in line and line.split(':', 1)[0].strip():
            if current_line:
                combined_lines.append(current_line)
            current_line = line
        elif current_line:
            current_line += ' ' + line
        else:
            combined_lines.append(line)
    
    if current_line:
        combined_lines.append(current_line)
    
    # Second pass: Combine consecutive lines from the same speaker
    final_lines = []
    current_speaker = None
    current_text = None
    
    for line in combined_lines:
        if ':' not in line:
            if current_text:
                final_lines.append(f"{current_speaker}: {current_text}")
            final_lines.append(line)
            current_speaker = None
            current_text = None
            continue
            
        speaker, text = line.split(':', 1)
        speaker = speaker.strip()
        text = text.strip()
        
        if speaker == current_speaker:
            current_text += ' ' + text
        else:
            if current_text:
                final_lines.append(f"{current_speaker}: {current_text}")
            current_speaker = speaker
            current_text = text
    
    if current_text:
        final_lines.append(f"{current_speaker}: {current_text}")
    
    return '\n'.join(final_lines)

def clean_transcript(input_file):
    """
    Clean the VTT transcript file and convert it to plain text.
    
    Args:
        input_file (str): Path to the original VTT file.
    
    Returns:
        str: Path to the cleaned transcript file.
    """
    show_progress("Reading transcript file...")
    
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    show_progress("Cleaning timestamp lines...")
    
    # Get the filename without extension to use in the header
    filename_base = os.path.splitext(os.path.basename(input_file))[0]
    
    # Replace WEBVTT with filename and transcript
    content = content.replace("WEBVTT", f"{filename_base} transcript")
    
    # Remove timestamp lines (lines containing -->)
    content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\n', '', content)
    
    show_progress("Removing formatting tags...")
    
    # Remove the ID lines (UUID-looking strings with numbers)
    content = re.sub(r'[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}/\d+-\d+\n', '', content)
    
    # Remove <v and </v> tags
    content = content.replace('</v>', '')
    content = re.sub(r'<v\s+', '', content)
    
    # Replace remaining '>' with ':'
    content = content.replace('>', ':')
    
    show_progress("Combining consecutive speaker lines...")
    
    # Combine consecutive lines from the same speaker
    content = combine_speaker_lines(content)
    
    show_progress("Cleaning up extra spaces...")
    
    content = re.sub(r'\n\s*\n', '\n', content)
    
    output_file = input_file.replace('.vtt', '_cleaned.txt')
    if output_file == input_file:
        output_file = input_file + '_cleaned.txt'
    
    show_progress("Saving cleaned transcript...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_file

def clean_vtt_file(file_path):
    """
    Cleans a VTT transcript file and returns the path of the cleaned output file.
    
    Args:
        file_path (str): Path to the original VTT file.
    
    Returns:
        str: Path to the cleaned transcript file.
    """
    # Sanitize and validate the file path
    input_file = sanitize_path(file_path)
    
    # Clean the transcript and return the output file path
    output_file = clean_transcript(input_file)
    return output_file

def run_cleaner():
    """
    Runs the VTT cleaner in interactive mode, prompting the user for input.
    """
    print_welcome_message()
    file_path = input("\nPlease enter the path to your VTT file: ")
    try:
        output_file = clean_vtt_file(file_path)
        print("\n✨ Success! ✨")
        print_concluding_message(output_file)
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    run_cleaner()
