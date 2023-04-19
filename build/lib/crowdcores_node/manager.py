import argparse
import subprocess
import os
import time
import signal


node_out_put_file="/tmp/crowdcores_log.txt"

#os.environ["PYTHONUNBUFFERED"] = "1"
def start():
    pid = get_pid()
    if pid:
        print("CrowdCore Node is already running...")
        return;
 

    print("Checking for Updates...")
    update()
    print("Starting CrowdCore Node...")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    node_path = os.path.join(script_dir,"crowdcores_node.py")

    with open(node_out_put_file, 'w') as f:
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
    print("Connecting to CrowdCore Node...")
    with open(node_out_put_file, 'r') as f:
        while True:
            line = f.readline().strip()
            if line:
                print(line)
            else:
                time.sleep(0.1)


def update():
    subprocess.call(['pip', 'install', '--upgrade','--no-deps', 'crowdcores-node'])
##print("Connecting to service...")
##pid = get_pid()
##if not pid:
##    print("Service is not running.")
##    return
##process = subprocess.Popen(["tail", "-f", f"/proc/{pid}/fd/1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
##for line in iter(process.stdout.readline, b''):
##    print(line.decode("utf-8").strip())
     

  ##for line in iter(process.stdout.readline, b''):
  ##    print("got a line");
  ##    print(line.decode("utf-8").strip())

def get_pid():
    process = subprocess.Popen(["pgrep", "-f", "crowdcores_node.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pid, error = process.communicate()
    if not pid:
        return None
    pid = pid.decode("utf-8").strip()
    return int(pid)

##  def get_pid():
##      process = subprocess.Popen(["pgrep", "-f", "my_script.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
##      pid, error = process.communicate()
##      if not pid:
##          return None
##      pid = pid.decode("utf-8").strip()
##      pids = pid.split('\n')
##      return int(pids[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'update','connect'], help='Action to perform')
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
