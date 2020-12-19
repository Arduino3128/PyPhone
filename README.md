# PyPhone  
Python Based VoIP GUI Calling App  
   
## What is PyPhone?  
  
PyPhone a fully Open Sourced Python Based GUI VoIP Calling App which enables Calling over the Internet Free of cost. PyPhone currently uses ngrok for port forwarding enabling call from anywhere around the world, with minor changes can be used as a off-grid Calling Service within LAN. It uses PyQt5 for its GUI.   
  
<a title="Open Source Initiative official SVG, Public domain, via Wikimedia Commons" href="https://commons.wikimedia.org/wiki/File:Opensource.svg"><img width="64" alt="Opensource" src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Opensource.svg/64px-Opensource.svg.png"></a>   
  

### Features Expected in Future releases:  
  
1. Multi-User call.  
2. Contact Directory.  
3. Advance Hold Feature.  
  
## How to use PyPhone?  
Since, PyPhone uses ngrok, it is required to make an account in [ngrok](https://ngrok.com/). PyPhone comes with Ngrok.  
### Steps:  
1. Make a file named "ngrok.yml" in the same level as of PyPhone.py and add the following line:  
    `authtoken: <YOUR_NGROK_AUTHTOKEN>`  
2. "config.cnf" contains the phone number of the user.  
3. Run PyPhone.py  
Also, PyPhone uses MySQL database for storing the phone numbers and requires additional setup.(This step will not be required once PyPhone's MySQL DB is setup)  
### Steps(MySQL DB):
The MySQL requires the following setup:  
  
pyphone(Database)------> data(Table) ------------> | Phoneno varchar(12)|-------------------| Port varchar(6) |  
  
`CREATE DATABASE pyphone;`  
`CREATE TABLE data(Phoneno VARCHAR(12), Port VARCHAR(6));`  
`INSERT INTO data values("<PHONE_NUMBER_AFTER_REG>","<PORTNUMBER*>")`  
  
*PORTNUMBER will be automatically filled by the PyPhone.  
  
## Gallery
![image](images/Image1.png)
![image](images/Image2.png)
![image](images/Image3.png)

### ⚠️ Disclaimer: PyPhone is still in its early phase and is in no way near to a stable release. Also, there is no guarantee of its stablity and is susceptible of crashes. PyPhone still requires proper Error Handling methods and is currently not intended to used as an stable application.

### 👋 PyPhone is fully open source and you are always welcome for any contribution.

