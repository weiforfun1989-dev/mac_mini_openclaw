"""
Auto-task-creation handler - Every user request creates a job automatically
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jobs import create_job

# Track which messages we've already processed (in-memory for session)
processed_messages = set()

def should_create_task(message_text):
    """
    Determine if a user message should create a task.
    Returns True if it's a request/work item, False if it's casual conversation.
    """
    if not message_text:
        return False
    
    text = message_text.strip().lower()
    
    # Skip short greetings and casual phrases
    casual_phrases = [
        'hello', 'hi', 'hey', 'yo', 
        'thanks', 'thank you', 'thx',
        'ok', 'okay', 'sure', 'got it',
        'bye', 'goodbye', 'see ya',
        'lol', 'haha', 'nice', 'cool',
        'yes', 'no', 'maybe'
    ]
    
    # If just a casual phrase, don't create task
    if text in casual_phrases or len(text) < 10:
        return False
    
    # Check for task indicators
    task_indicators = [
        'can you', 'could you', 'please', 
        'create', 'add', 'build', 'make', 'implement',
        'fix', 'update', 'change', 'modify',
        'research', 'find', 'look up',
        'design', 'plan', 'write',
        'check', 'verify', 'test',
        'help me', 'i need', 'i want'
    ]
    
    has_indicator = any(indicator in text for indicator in task_indicators)
    
    # Question marks often indicate requests
    is_question = '?' in message_text
    
    # Commands/directives
    is_command = text.startswith(('create ', 'add ', 'build ', 'fix ', 'update '))
    
    return has_indicator or is_question or is_command or len(text) > 50

def extract_task_description(message_text):
    """Extract a clean task description from user message."""
    text = message_text.strip()
    
    # Remove common prefixes
    prefixes = [
        (r'^(can you|could you|please|hey\s+,?|hi\s+,?|hello\s+,?)\s*', re.IGNORECASE),
        (r'^(i need|i want|help me)\s+(to\s+)?', re.IGNORECASE),
    ]
    
    for pattern, flags in prefixes:
        text = re.sub(pattern, '', text, flags=flags)
    
    # Capitalize first letter
    text = text[0].upper() + text[1:] if text else text
    
    # Limit length
    if len(text) > 200:
        text = text[:197] + '...'
    
    return text

def handle_user_message(message_text, message_id=None):
    """
    Handle incoming user message - create task if appropriate.
    Returns (job_id, description) if task created, None otherwise.
    """
    # Deduplicate by message content hash
    msg_hash = hash(message_text) if message_text else None
    if msg_hash in processed_messages:
        return None
    processed_messages.add(msg_hash)
    
    # Check if this should be a task
    if not should_create_task(message_text):
        return None
    
    # Extract description
    description = extract_task_description(message_text)
    
    # Create the job
    try:
        job_id = create_job(
            description=description,
            assigned_to="Mac",
            priority="medium",
            from_user=True  # Requires Mac confirmation
        )
        return (job_id, description)
    except Exception as e:
        print(f"Error creating auto-task: {e}")
        return None

# Example/test
if __name__ == "__main__":
    # Test cases
    test_messages = [
        "Hello",  # No task
        "Can you create a dashboard?",  # Task
        "Build me an API endpoint",  # Task
        "Thanks!",  # No task
        "Research the best Python frameworks for async work",  # Task
    ]
    
    for msg in test_messages:
        result = handle_user_message(msg)
        indicator = "✅ TASK" if result else "❌ SKIP"
        print(f"{indicator}: {msg[:50]}...")
