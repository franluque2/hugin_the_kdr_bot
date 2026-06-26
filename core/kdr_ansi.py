def ansi_format(text, color="37", format="0"):
    return f"\u001b[{format};{color}m{text}\u001b[0m"

def gray(text): return ansi_format(text, "30")
def red(text, b=False): return ansi_format(text, "31", "1" if b else "0")
def green(text, b=False): return ansi_format(text, "32", "1" if b else "0")
def yellow(text, b=False): return ansi_format(text, "33", "1" if b else "0")
def blue(text, b=False): return ansi_format(text, "34", "1" if b else "0")
def pink(text, b=False): return ansi_format(text, "35", "1" if b else "0")
def purple(text, b=False): return ansi_format(text, "35", "1" if b else "0")
def cyan(text, b=False): return ansi_format(text, "36", "1" if b else "0")
def white(text, b=False): return ansi_format(text, "37", "1" if b else "0")

def wrap_ansi(text):
    return f"```ansi\n{text}```"
