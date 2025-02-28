#!/usr/bin/env python3
import os
import re

def sanitize_path(input_path):
    """
    Sanitize and validate the input file path.
    
    Args:
        input_path (str): Raw input path.
        
    Returns:
        str: Sanitized path if valid.
        
    Raises:
        FileNotFoundError: If path is invalid or file doesn't exist.
    """
    # Strip whitespace and surrounding quotes
    path = input_path.strip().strip("'\"")
    # Handle doubled backslashes
    path = path.replace("\\\\", "\\")
    
    # Create variations of the path to try
    paths_to_try = [
        path,  # Original path
        path.replace("\\ ", " ").replace("\\(", "(").replace("\\)", ")"),
        re.sub(r'\\(.)', r'\1', path),
    ]
    
    for p in paths_to_try:
        if os.path.exists(p.strip()):
            return p.strip()
    
    raise FileNotFoundError(
        "Could not find the file. Please ensure the path is correct "
        "and try again."
    )

def verify_file_exists(path):
    """
    Check if a file exists by attempting to open it.
    """
    try:
        with open(path, 'r') as f:
            return True
    except (IOError, OSError):
        return False