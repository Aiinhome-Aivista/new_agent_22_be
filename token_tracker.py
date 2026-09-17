import threading
import logging

# Configure logger specifically for the token tracker
logger = logging.getLogger("token_tracker")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# Thread-safe counters
_total_input_tokens = 0
_total_output_tokens = 0
_lock = threading.Lock()

def add_tokens(input_tokens: int, output_tokens: int):
    """
    Safely adds tokens to the global counters and prints an info log.
    """
    global _total_input_tokens, _total_output_tokens
    with _lock:
        _total_input_tokens += input_tokens
        _total_output_tokens += output_tokens
        current_input = _total_input_tokens
        current_output = _total_output_tokens
        
    logger.info(
        f"Used {input_tokens} input, {output_tokens} output. "
        f"Cumulative: {current_input} input, {current_output} output."
    )

def get_tokens():
    """
    Returns a dictionary of the current token counts.
    """
    with _lock:
        return {
            "total_input_tokens": _total_input_tokens,
            "total_output_tokens": _total_output_tokens,
            "total_combined_tokens": _total_input_tokens + _total_output_tokens
        }

def reset_tokens():
    """
    Resets the global token counters to zero.
    """
    global _total_input_tokens, _total_output_tokens
    with _lock:
        _total_input_tokens = 0
        _total_output_tokens = 0
    logger.info("Token counters have been reset to zero.")

def print_lifecycle_summary():
    """
    Prints a highly visible, decorative summary to the terminal.
    """
    with _lock:
        in_t = _total_input_tokens
        out_t = _total_output_tokens
        comb_t = in_t + out_t

    print("\n" + "=" * 60)
    print("🎉 [LIFECYCLE COMPLETE] LLM TOKEN USAGE SUMMARY 🎉".center(60))
    print("=" * 60)
    print(f"Total Input Tokens:   {in_t:,}".center(60))
    print(f"Total Output Tokens:  {out_t:,}".center(60))
    print("-" * 60)
    print(f"Total Combined:       {comb_t:,}".center(60))
    print("=" * 60 + "\n")
