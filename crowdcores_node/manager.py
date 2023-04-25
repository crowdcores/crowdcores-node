import argparse
import subprocess
import os
import time
import signal
import psutil


# os.environ["PYTHONUNBUFFERED"] = "1"
def start():
    pid = get_pid()
    if pid:
        print("CrowdCore Node is already running...")
        return

    print("Checking for Updates...")
    update()
    print("Starting CrowdCore Node...")
    script_dir = os.path.dirname(os.path.realpath(__file__))
    node_path = os.path.join(script_dir, "crowdcores_node.py")

    with open(cc_log_path(), 'w') as f:
        process = subprocess.Popen(["python3","-u",node_path], stdout=f, stderr=f)
    print("CrowdCore Node started with PID:", process.pid)

def stop():
    print("Stopping CrowdCore Node...")
    pid = get_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        print("CrowdCore Node Stopped...")
    else:
        print("CrowdCore Node is not running.")

def connect():
    if get_pid():
        print("CrowdCore Node is currently running...")
        print("Connecting to CrowdCore Node...")
    else:
        print("CrowdCore Node is not running. Any logs below are probably from a previous run.")
        print("Showing CrowdCore Node logs...")
    with open(cc_log_path(), 'r') as f:
        while True:
            line = f.readline().strip()
            if line:
                print(line)
            else:
                time.sleep(0.1)

def update():
    subprocess.call(['pip', 'install', '--upgrade', '--no-deps', 'crowdcores-node'])

def restart():
    stop()
    start()

def get_pid():
    for proc in psutil.process_iter():
        # concatenate the cmdline elements into a single string to search for crowdcores_node.py
        try:
            if 'crowdcores_node.py' in ' '.join(proc.cmdline()):
                return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, PermissionError):
            print("Possibly Access Denied to process:", proc, ". Skipping...")
    return None

def cc_log_path():
    if os.name == 'posix':  # if on unix
        return "/tmp/crowdcores_log.txt"
    else:
        return os.path.join(os.path.expanduser("~"), "Documents", "crowdcores_log.txt")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'update', 'connect'], help='Action to perform')
    args = parser.parse_args()

    if args.action == 'start':
        start()
    elif args.action == 'stop':
        stop()
    elif args.action == 'restart':
        restart()
    elif args.action == 'update':
        update()
    elif args.action == 'connect':
        connect()

if __name__ == "__main__":
    main()
