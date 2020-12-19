#ngrok Initiator.py
import subprocess
def runServer(Port):
    subprocess.run(".\\modules\\ngrok.exe tcp %s --region=in"%Port,shell=True)
def initiateServer(authToken):
    subprocess.run(".\\modules\\ngrok.exe authtoken %s"%authToken,shell=True)