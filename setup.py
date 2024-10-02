import subprocess
import time

def run_script():
    command = ["python", "ledgerer.py"]
    
    try:
        print("Subprocess: Ledgered Started")
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Script output:\n", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Script failed with error:", e.stderr)
        # Optionally, log the error to a file for further inspection
        with open("error_log.txt", "a") as log_file:
            log_file.write(f"Error: {e.stderr}\n")

def main():
    while True:
        run_script()
        time.sleep(300)  
        print("3 mins ended, restarting the process.")

if __name__ == "__main__":
    main()
