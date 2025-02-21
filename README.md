# AthletiFi Transcript Toolkit

The AthletiFi Transcript Toolkit provides a few handy tools to help you create, process and clean up transcripts.

## Available Utilities

- **Clean VTT transcripts:** Remove unnecessary formatting from VTT files and convert them into clean, plain text files ready for further analysis.
- **Create AWS transcription jobs:** Upload local audio files to S3 and initiate AWS Transcribe jobs (or use existing S3 URIs) with speaker identification.
- **Convert AWS Transcribe JSON Output:** Convert the JSON output from AWS Transcribe into a human-readable transcript, either by processing a local JSON file or by retrieving transcript data using an AWS Transcribe job name.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/transcript-toolkit.git
   cd transcript-toolkit
   ```

2. **Set Up a Virtual Environment (Recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   The key dependencies include:
   - `boto3` (for AWS interactions)
   - `requests` (for HTTP requests)
   - `questionary` (for interactive CLI prompts)

## Usage

Run the main menu to access all available options:

```bash
python main.py
```

## AWS Configuration

Before using the AWS transcription features, ensure that:

- **AWS CLI is installed and configured:**  

  ```bash
  aws configure
  ```
  
- **AWS Credentials are accessible:**  
  The tool uses `boto3` to interact with AWS services. Make sure your credentials are set up correctly.

## Testing & Troubleshooting

- **File Path Issues:**  
  The tools include sanitization functions to handle quoted paths and escape characters. If a file isn’t found, double-check the path and try again.
- **AWS Errors:**  
  If AWS-related operations fail, verify that your AWS credentials and permissions are properly configured.

## Future Enhancements

- **Unit Testing:**  
  Consider adding tests using frameworks like `pytest` for more robust code validation.
- **Logging:**  
  Future versions may incorporate a logging mechanism for improved debugging and monitoring.
- **Expanded CLI Options:**  
  Additional command-line arguments (e.g., via `argparse`) could enable non-interactive usage.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests to help improve the toolkit.

## License

This project is licensed under the [MIT License](LICENSE).
