# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QWidget
import mysql.connector
import json
import playsound
import requests
from modules import Initiator
import pyaudio
import threading
import socket
import re
import time
import sys

with open("ngrok.yml",'r') as NGROKFILE:
	NGROK=NGROKFILE.read()
NGROK=NGROK.split(': ')
Initiator.initiateServer(NGROK[1])

NumberDialed=""
with open("config.cnf",'r') as CONF:
	CONFDATA=CONF.read()
CONFDATA=CONFDATA.split(" | ")
PHONENO=CONFDATA[0]
print(PHONENO)
conn=mysql.connector.connect(
	host=CONFDATA[1],
	user=CONFDATA[2],
	passwd=CONFDATA[3],
	database=CONFDATA[4]
)
c=conn.cursor(buffered=True)
CALLSTAT=False
ACK=''
FIRST=True
RECEIVECALL="wait"
CONNRECV,CONNSEND='',''
MUTE,SPK=False,False
CIP=""
SOCK=""
NotPicked=True
Ringing=True
class ServerThread(QThread):
	IncommingCall=pyqtSignal(int)
	OngoingCall=pyqtSignal(int)
	CallEnded=pyqtSignal(int)
	def run(self):
		global CALLSTAT,ACK,MUTE,SPK,CIP
		IP=socket.gethostbyname(socket.gethostname())
		IP="127.0.0.1"
		PORT=6595
		SOCK=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		def runNgrok():
			Initiator.runServer(PORT)
		threading.Thread(target=runNgrok).start()
		SOCK.bind((IP,PORT))
		SOCK.listen(2)
		CHUNK_SIZE = 1024 # 512
		AUDIO_FORMAT = pyaudio.paInt16
		CHANNELS = 1
		RATE = 20000
		AUDIO = pyaudio.PyAudio()
		PLAY_STREAM = AUDIO.open(format=AUDIO_FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK_SIZE)
		RECORD_STREAM = AUDIO.open(format=AUDIO_FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)

		def CLIENTCONN(CIP,CADDR):
			print(CADDR)
			global ACK, RECEIVECALL,CALLSTAT
			def RINGTONE():
				while Ringing:
					playsound.playsound("sounds\\ringtone.mp3")
			def SEND():
				while CALLSTAT==False:
					try:
						if MUTE==False:
							DATA=RECORD_STREAM.read(1024)
							CIP.send(DATA)
					except Exception as ERROR:
						print("Error1: ", ERROR)
						CIP.close()
						self.CallEnded.emit(1)
						break
				CIP.close()
			def RECV():
				while CALLSTAT==False:
					try:
						DATA=CIP.recv(1024)
						if SPK==False:
							PLAY_STREAM.write(DATA)
					except Exception as ERROR:
						print("Error2: ", ERROR)
						CIP.close()
						self.CallEnded.emit(1)
						break
				CIP.close()
			try:
				ACK=CIP.recv(27).decode()
				print(re.match("PID\:[1-9]{10} ACK\:Complete",ACK))
				if re.match("PID\:[1-9]{10} ACK\:Complete",ACK)!=None:
					self.IncommingCall.emit(1)
					Ringing=True
					threading.Thread(target=RINGTONE).start()
					while True:
						if RECEIVECALL == "OK":
							CIP.send("ACK:Complete".encode("UTF-8"))
							Ringing=False
							self.OngoingCall.emit(1)
							CONNSEND=threading.Thread(target=SEND)
							CONNRECV=threading.Thread(target=RECV)
							CONNSEND.start()
							CONNRECV.start()
							RECEIVECALL="wait"
							break
						elif RECEIVECALL == "REJECT":
							CIP.send("ACK:Reject".encode("UTF-8"))
							Ringing=False
							RECEIVECALL="wait"
							CIP.close()
							break
						else:
							pass
				else:
					print("ABORT")
					CIP.close()
			except Exception as ERROR:
				print("Errored: ", ERROR)

		time.sleep(3)
		OPT=requests.get("http://localhost:4040/api/tunnels").text
		OPT=json.loads(OPT)
		OPT=OPT['tunnels'][0]['public_url']
		OPT=OPT.split(":")
		print(OPT)
		c.execute("update data set Port=%s where Phoneno=%s"%(OPT[2],PHONENO))
		conn.commit()
		while True:
			CIP,CADDR=SOCK.accept()
			threading.Thread(target=CLIENTCONN,args=(CIP,CADDR)).start()
		
class ClientThread(QThread):
	CallEnded=pyqtSignal(int)
	CallRinging=pyqtSignal(int)
	CallPicked=pyqtSignal(int)	
	def run(self):
		global NumberDialed,CALLSTAT,MUTE,SPK
		IP="0.tcp.in.ngrok.io"
		CHUNK_SIZE = 1024 # 512
		AUDIO_FORMAT = pyaudio.paInt16
		CHANNELS = 1
		RATE = 20000
		AUDIO = pyaudio.PyAudio()
		PLAY_STREAM = AUDIO.open(format=AUDIO_FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK_SIZE)
		RECORD_STREAM = AUDIO.open(format=AUDIO_FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)
		def CLIENTCONN(SOCK):

			def RINGBACK():
				while NotPicked:
					playsound.playsound("sounds\\ringback_tone.mp3")
			def SEND():
				while CALLSTAT==False:
					try:
						if MUTE==False:
							DATA=RECORD_STREAM.read(1024)
							SOCK.sendall(DATA)
					except Exception as ERROR:
						print("Error1: ", ERROR)
						SOCK.close()
						self.CallEnded.emit(1)
						break
			def RECV():
				while CALLSTAT==False:
					try:
						if SPK==False:
							DATA=SOCK.recv(1024)
							PLAY_STREAM.write(DATA)
					except Exception as ERROR:
						print("Error2: ", ERROR)
						SOCK.close()
						self.CallEnded.emit(1)
						break
			try:
				NotPicked=True
				threading.Thread(target=RINGBACK).start()
				SOCK.send(f"PID:{PHONENO} ACK:Complete".encode())
				RUT=SOCK.recv(12).decode()
				if RUT=="ACK:Complete":
					NotPicked=False
					self.CallPicked.emit(1)
					threading.Thread(target=SEND).start()
					threading.Thread(target=RECV).start()
				else:
					print("ABORT, No ACK Received!")
					NotPicked=False
			except Exception as ERROR:
				print("ERRORED: ", ERROR)
		def GETPORT():
			global SOCK
			print("Dialer")
			Phoneno=NumberDialed
			c.execute("Select * from data where Phoneno=%s"%Phoneno)
			GETDATA=c.fetchone()
			try:
				PORT=int(GETDATA[1])
				SOCK=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
				SOCK.connect((IP,PORT))
				CLIENTCONN(SOCK)
			except:
				pass
		GETPORT()

class Ui_MainWindow(QWidget):
	def setupUi(self, MainWindow):
		MainWindow.setObjectName("MainWindow")
		MainWindow.setWindowIcon(QtGui.QIcon("icons/phone.png"))
		MainWindow.resize(331, 560)
		MainWindow.setMinimumSize(QtCore.QSize(331, 560))
		MainWindow.setMaximumSize(QtCore.QSize(331, 560))
		MainWindow.setStyleSheet("")
		self.centralwidget = QtWidgets.QWidget(MainWindow)
		self.centralwidget.setObjectName("centralwidget")
		self.DIALER = QtWidgets.QWidget(self.centralwidget)
		self.DIALER.setGeometry(QtCore.QRect(0, 29, 331, 531))
		self.DIALER.setStyleSheet("QWidget{\n"
"    background-color: rgb(18, 18, 18);\n"
"}")
		self.DIALER.setObjectName("DIALER")
		self.KEY5 = QtWidgets.QPushButton(self.DIALER)
		self.KEY5.setGeometry(QtCore.QRect(130, 210, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY5.setFont(font)
		self.KEY5.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY5.setObjectName("KEY5")
		self.KEY4 = QtWidgets.QPushButton(self.DIALER)
		self.KEY4.setGeometry(QtCore.QRect(60, 210, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY4.setFont(font)
		self.KEY4.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY4.setObjectName("KEY4")
		self.KEY8 = QtWidgets.QPushButton(self.DIALER)
		self.KEY8.setGeometry(QtCore.QRect(130, 280, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY8.setFont(font)
		self.KEY8.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY8.setObjectName("KEY8")
		self.KEYCALL = QtWidgets.QPushButton(self.DIALER)
		self.KEYCALL.setGeometry(QtCore.QRect(90, 430, 75, 51))
		self.KEYCALL.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYCALL.setText("")
		icon = QtGui.QIcon()
		icon.addPixmap(QtGui.QPixmap("icons/telephone.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.KEYCALL.setIcon(icon)
		self.KEYCALL.setIconSize(QtCore.QSize(35, 35))
		self.KEYCALL.setObjectName("KEYCALL")
		self.KEYHASH = QtWidgets.QPushButton(self.DIALER)
		self.KEYHASH.setGeometry(QtCore.QRect(200, 350, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEYHASH.setFont(font)
		self.KEYHASH.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYHASH.setObjectName("KEYHASH")
		self.KEY2 = QtWidgets.QPushButton(self.DIALER)
		self.KEY2.setGeometry(QtCore.QRect(130, 140, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY2.setFont(font)
		self.KEY2.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY2.setObjectName("KEY2")
		self.KEY0 = QtWidgets.QPushButton(self.DIALER)
		self.KEY0.setGeometry(QtCore.QRect(130, 350, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY0.setFont(font)
		self.KEY0.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY0.setObjectName("KEY0")
		self.KEY9 = QtWidgets.QPushButton(self.DIALER)
		self.KEY9.setGeometry(QtCore.QRect(200, 280, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY9.setFont(font)
		self.KEY9.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY9.setObjectName("KEY9")
		self.KEY7 = QtWidgets.QPushButton(self.DIALER)
		self.KEY7.setGeometry(QtCore.QRect(60, 280, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY7.setFont(font)
		self.KEY7.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY7.setObjectName("KEY7")
		self.KEY6 = QtWidgets.QPushButton(self.DIALER)
		self.KEY6.setGeometry(QtCore.QRect(200, 210, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY6.setFont(font)
		self.KEY6.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY6.setObjectName("KEY6")
		self.KEY3 = QtWidgets.QPushButton(self.DIALER)
		self.KEY3.setGeometry(QtCore.QRect(200, 140, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY3.setFont(font)
		self.KEY3.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY3.setObjectName("KEY3")
		self.KEY1 = QtWidgets.QPushButton(self.DIALER)
		self.KEY1.setGeometry(QtCore.QRect(60, 140, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEY1.setFont(font)
		self.KEY1.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEY1.setObjectName("KEY1")
		self.KEYSTAR = QtWidgets.QPushButton(self.DIALER)
		self.KEYSTAR.setGeometry(QtCore.QRect(60, 350, 61, 61))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEYSTAR.setFont(font)
		self.KEYSTAR.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYSTAR.setObjectName("KEYSTAR")
		self.NumberLab = QtWidgets.QLabel(self.DIALER)
		self.NumberLab.setGeometry(QtCore.QRect(10, 40, 311, 61))
		font = QtGui.QFont()
		font.setPointSize(30)
		self.NumberLab.setFont(font)
		self.NumberLab.setStyleSheet("QLabel{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QLabel:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(31, 31, 45);\n"
"}")
		self.NumberLab.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
		self.NumberLab.setFrameShape(QtWidgets.QFrame.Box)
		self.NumberLab.setFrameShadow(QtWidgets.QFrame.Plain)
		self.NumberLab.setText("")
		self.NumberLab.setScaledContents(True)
		self.NumberLab.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
		self.NumberLab.setObjectName("NumberLab")
		self.CALLER = QtWidgets.QWidget(self.DIALER)
		self.CALLER.setGeometry(QtCore.QRect(0, 0, 0, 531))
		self.CALLER.setStyleSheet("QWidget{\n"
"    background-color: rgb(18, 18, 18);\n"
"}")
		self.CALLER.setObjectName("CALLER")
		self.KEYMUTE = QtWidgets.QPushButton(self.CALLER)
		self.KEYMUTE.setGeometry(QtCore.QRect(30, 430, 75, 51))
		self.KEYMUTE.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYMUTE.setText("")
		icon1 = QtGui.QIcon()
		icon1.addPixmap(QtGui.QPixmap("icons/mute.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.KEYMUTE.setIcon(icon1)
		self.KEYMUTE.setIconSize(QtCore.QSize(35, 35))
		self.KEYMUTE.setObjectName("KEYMUTE")
		self.KEYEND = QtWidgets.QPushButton(self.CALLER)
		self.KEYEND.setGeometry(QtCore.QRect(130, 430, 75, 51))
		self.KEYEND.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYEND.setText("")
		icon2 = QtGui.QIcon()
		icon2.addPixmap(QtGui.QPixmap("icons/telephonex.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.KEYEND.setIcon(icon2)
		self.KEYEND.setIconSize(QtCore.QSize(35, 35))
		self.KEYEND.setObjectName("KEYEND")
		self.KEYHOLD = QtWidgets.QPushButton(self.CALLER)
		self.KEYHOLD.setGeometry(QtCore.QRect(130, 360, 75, 51))
		self.KEYHOLD.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYHOLD.setText("")
		icon3 = QtGui.QIcon()
		icon3.addPixmap(QtGui.QPixmap("icons/pause-button.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.KEYHOLD.setIcon(icon3)
		self.KEYHOLD.setIconSize(QtCore.QSize(35, 35))
		self.KEYHOLD.setObjectName("KEYHOLD")
		self.KEYMIC = QtWidgets.QPushButton(self.CALLER)
		self.KEYMIC.setGeometry(QtCore.QRect(230, 430, 75, 51))
		self.KEYMIC.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYMIC.setText("")
		icon4 = QtGui.QIcon()
		icon4.addPixmap(QtGui.QPixmap("icons/mic.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.KEYMIC.setIcon(icon4)
		self.KEYMIC.setIconSize(QtCore.QSize(35, 35))
		self.KEYMIC.setObjectName("KEYMIC")
		self.InfoText = QtWidgets.QTextBrowser(self.CALLER)
		self.InfoText.setGeometry(QtCore.QRect(10, 41, 311, 281))
		self.InfoText.setStyleSheet("QTextBrowser{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QTextBrowser:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(31, 31, 45);\n"
"}")
		self.InfoText.setObjectName("InfoText")
		self.KEYCANCEL = QtWidgets.QPushButton(self.DIALER)
		self.KEYCANCEL.setGeometry(QtCore.QRect(180, 430, 61, 51))
		font = QtGui.QFont()
		font.setPointSize(25)
		self.KEYCANCEL.setFont(font)
		self.KEYCANCEL.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYCANCEL.setText("")
		icon5 = QtGui.QIcon()
		icon5.addPixmap(QtGui.QPixmap("icons/backspace.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.KEYCANCEL.setIcon(icon5)
		self.KEYCANCEL.setIconSize(QtCore.QSize(30, 30))
		self.KEYCANCEL.setObjectName("KEYCANCEL")
		self.ATTENDER = QtWidgets.QWidget(self.DIALER)
		self.ATTENDER.setGeometry(QtCore.QRect(0, 0, 0, 531))
		self.ATTENDER.setStyleSheet("QWidget{\n"
"    background-color: rgb(18, 18, 18);\n"
"}")
		self.ATTENDER.setObjectName("ATTENDER")
		self.KEYACC = QtWidgets.QPushButton(self.ATTENDER)
		self.KEYACC.setGeometry(QtCore.QRect(60, 420, 75, 51))
		self.KEYACC.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYACC.setText("")
		self.KEYACC.setIcon(icon)
		self.KEYACC.setIconSize(QtCore.QSize(35, 35))
		self.KEYACC.setObjectName("KEYACC")
		self.KEYREJ = QtWidgets.QPushButton(self.ATTENDER)
		self.KEYREJ.setGeometry(QtCore.QRect(190, 420, 75, 51))
		self.KEYREJ.setStyleSheet("QPushButton{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QPushButton:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(35, 35, 48);\n"
"}\n"
"QPushButton:pressed{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(26, 26, 36);\n"
"}")
		self.KEYREJ.setText("")
		self.KEYREJ.setIcon(icon2)
		self.KEYREJ.setIconSize(QtCore.QSize(35, 35))
		self.KEYREJ.setObjectName("KEYREJ")
		self.CallerInfo = QtWidgets.QTextBrowser(self.ATTENDER)
		self.CallerInfo.setGeometry(QtCore.QRect(10, 71, 311, 131))
		font = QtGui.QFont()
		font.setPointSize(24)
		self.CallerInfo.setFont(font)
		self.CallerInfo.setStyleSheet("QTextBrowser{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color:rgb(39, 39, 53);\n"
"}\n"
"QTextBrowser:hover{\n"
"border:2px solid;\n"
"border-radius:20px;\n"
"color: rgb(141, 141, 141);\n"
"border-color: rgb(139, 139, 139);\n"
"background-color: rgb(31, 31, 45);\n"
"}")
		self.CallerInfo.setObjectName("CallerInfo")
		self.KEYCANCEL.raise_()
		self.KEY5.raise_()
		self.KEY4.raise_()
		self.KEY8.raise_()
		self.KEYCALL.raise_()
		self.KEYHASH.raise_()
		self.KEY2.raise_()
		self.KEY0.raise_()
		self.KEY9.raise_()
		self.KEY7.raise_()
		self.KEY6.raise_()
		self.KEY3.raise_()
		self.KEY1.raise_()
		self.KEYSTAR.raise_()
		self.NumberLab.raise_()
		self.CALLER.raise_()
		self.ATTENDER.raise_()
		self.TopBar = QtWidgets.QLabel(self.centralwidget)
		self.TopBar.setGeometry(QtCore.QRect(0, 0, 331, 31))
		self.TopBar.setStyleSheet("QWidget{\n"
"background-color:rgb(50, 50, 63);\n"
"color: rgb(193, 193, 193);\n"
"}")
		self.TopBar.setText("        PyPhone")
		font = QtGui.QFont()
		font.setPointSize(9)
		self.TopBar.setFont(font)
		self.TopBar.setObjectName("TopBar")
		self.Exit = QtWidgets.QPushButton(self.centralwidget)
		self.Exit.setGeometry(QtCore.QRect(300, 0, 31, 31))
		self.Exit.setStyleSheet("QPushButton{\n"
"background-color:rgb(50, 50, 63);\n"
"border:0px;\n"
"}\n"
"QPushButton:hover{\n"
"    background-color: rgb(42, 42, 53);\n"
"}\n"
"QPushButton:pressed{\n"
"    background-color: rgb(200, 0, 0);\n"
"}")
		self.Exit.setText("")
		icon6 = QtGui.QIcon()
		icon6.addPixmap(QtGui.QPixmap("icons/cil-x.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.Exit.setIcon(icon6)
		self.Exit.setFlat(False)
		self.Exit.setObjectName("Exit")
		self.MinimizeButton = QtWidgets.QPushButton(self.centralwidget)
		self.MinimizeButton.setGeometry(QtCore.QRect(270, 0, 31, 31))
		self.MinimizeButton.setStyleSheet("QPushButton{\n"
"background-color:rgb(50, 50, 63);\n"
"border:0px;\n"
"}\n"
"QPushButton:hover{\n"
"    background-color: rgb(42, 42, 53);\n"
"}\n"
"QPushButton:pressed{\n"
"    background-color: rgb(39, 39, 49);\n"
"}")
		self.MinimizeButton.setText("")
		icon7 = QtGui.QIcon()
		icon7.addPixmap(QtGui.QPixmap("icons/cil-window-minimize.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.MinimizeButton.setIcon(icon7)
		self.MinimizeButton.setFlat(False)
		self.MinimizeButton.setObjectName("MinimizeButton")
		self.LogoInfo = QtWidgets.QPushButton(self.centralwidget)
		self.LogoInfo.setGeometry(QtCore.QRect(0, 0, 31, 31))
		self.LogoInfo.setStyleSheet("QPushButton{\n"
"background-color:rgb(50, 50, 63);\n"
"border:0px;\n"
"}\n"
"QPushButton:hover{\n"
"    background-color: rgb(42, 42, 53);\n"
"}\n"
"QPushButton:pressed{\n"
"    background-color: rgb(39, 39, 49);\n"
"}")
		self.LogoInfo.setText("")
		icon8 = QtGui.QIcon()
		icon8.addPixmap(QtGui.QPixmap("icons/phone.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.LogoInfo.setIcon(icon8)
		self.LogoInfo.setFlat(False)
		self.LogoInfo.setObjectName("LogoInfo")
		MainWindow.setCentralWidget(self.centralwidget)
		self.KEY0.clicked.connect(lambda:self.KEYPRESSED("0"))
		self.KEY1.clicked.connect(lambda:self.KEYPRESSED("1"))
		self.KEY2.clicked.connect(lambda:self.KEYPRESSED("2"))
		self.KEY3.clicked.connect(lambda:self.KEYPRESSED("3"))
		self.KEY4.clicked.connect(lambda:self.KEYPRESSED("4"))
		self.KEY5.clicked.connect(lambda:self.KEYPRESSED("5"))
		self.KEY6.clicked.connect(lambda:self.KEYPRESSED("6"))
		self.KEY7.clicked.connect(lambda:self.KEYPRESSED("7"))
		self.KEY8.clicked.connect(lambda:self.KEYPRESSED("8"))
		self.KEY9.clicked.connect(lambda:self.KEYPRESSED("9"))
		self.KEYSTAR.clicked.connect(lambda:self.KEYPRESSED("*"))
		self.KEYHASH.clicked.connect(lambda:self.KEYPRESSED("#"))
		self.KEYCANCEL.clicked.connect(lambda:self.KEYPRESSED("bksp"))
		self.KEYCALL.clicked.connect(lambda:self.CALL())
		self.KEYMIC.setCheckable(True)
		self.KEYMUTE.setCheckable(True)
		self.KEYHOLD.setCheckable(True)
		self.KEYEND.clicked.connect(lambda:self.ENDCALL())
		self.KEYMIC.clicked.connect(lambda:self.MAKEMUTE())
		self.KEYMUTE.clicked.connect(lambda:self.MAKEDEAF())
		self.KEYHOLD.clicked.connect(lambda:self.MAKEHOLD())
		
		self.MinimizeButton.clicked.connect(lambda:MainWindow.showMinimized())

		self.retranslateUi(MainWindow)
		QtCore.QMetaObject.connectSlotsByName(MainWindow)


		def moveWindow(event):
			if event.buttons() == Qt.LeftButton:
				MainWindow.move(MainWindow.pos() + event.globalPos() - self.dragPos)
				self.dragPos = event.globalPos()
			event.accept()

		def pressWindow(event):
			# MOVE WINDOW
			self.dragPos = event.globalPos()

			
			#if event.buttons() == Qt.LeftButton:
			#	self.move(self.pos() + event.globalPos() - self.dragPos)
			#	self.dragPos = event.globalPos()
			#	event.accept()

		def releasedWindow(event):
			# MOVE WINDOW
			pass
		self.TopBar.mouseMoveEvent=moveWindow
		self.TopBar.mousePressEvent=pressWindow
		self.TopBar.mouseReleaseEvent=releasedWindow

		self.Exit.clicked.connect(lambda:sys.exit())
		global FIRST,CALLSTAT,NumberDialed
		self.SERVERTHREADRUNNER=ServerThread()
		CALLSTAT=False
		if FIRST==True:
			self.SERVERTHREADRUNNER.start()
			FIRST=False
		self.SERVERTHREADRUNNER.IncommingCall.connect(lambda:self.PICKUPCALL())
		self.SERVERTHREADRUNNER.OngoingCall.connect(lambda:self.POSTPICKUPCALL())
		self.SERVERTHREADRUNNER.CallEnded.connect(lambda:self.ENDCALL())
		NumberDialed=""

	def ENDCALL(self):
		global CALLSTAT,CIP
		CALLSTAT=True
		try:
			CIP.close()
		except:
			pass
		self.setupUi(MainWindow)

	def PICKUPCALL(self):
		global CALLSTAT,RECEIVECALL,ACK
		_translate = QtCore.QCoreApplication.translate
		self.CALLER.setGeometry(QtCore.QRect(0, 0, 0, 531))
		self.ATTENDER.setGeometry(QtCore.QRect(0, 0, 331, 531))
		self.CallerInfo.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:24pt; font-weight:400; font-style:normal;\">\n"
"<p dir=\'rtl\' style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Incomming Call from</p><p>%s</p></body></html>"%ACK[4:14]))
		self.KEYACC.clicked.connect(lambda:self.PICKEDUP())
		self.KEYREJ.clicked.connect(lambda:self.NOTPICKEDUP())
	
	def MAKEHOLD(self):
		global SPK,MUTE
		if self.KEYHOLD.isChecked():
			MUTE,SPK=True,True
		else:
			MUTE,SPK=False,False

	def MAKEMUTE(self):
		global MUTE
		if self.KEYMIC.isChecked():
			MUTE=True
		else:
			MUTE=False

	def MAKEDEAF(self):
		global SPK
		if self.KEYMUTE.isChecked():
			SPK=True
		else:
			SPK=False

	def POSTPICKUPCALL(self):
		global ACK
		_translate = QtCore.QCoreApplication.translate
		self.CALLER.setGeometry(QtCore.QRect(0, 0, 331, 531))
		self.ATTENDER.setGeometry(QtCore.QRect(0, 0, 0, 531))
		self.InfoText.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:24pt; font-weight:400; font-style:normal;\">\n"
"<p dir=\'rtl\' style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">You are in a call with</p><p>%s</p></body></html>"%ACK[4:14]))

	def PICKEDUP(self):
		global RECEIVECALL
		RECEIVECALL="OK"

	def NOTPICKEDUP(self):
		global RECEIVECALL
		RECEIVECALL="REJECT"
		self.setupUi(MainWindow)

	def CALLENDED(self):
		global SOCK
		CALLSTAT=True
		SOCK.close()
		self.CLIENTTHREADRUNNER.wait()
		self.setupUi(MainWindow)

	def CALLINIT(self):
		global NumberDialed
		_translate = QtCore.QCoreApplication.translate
		self.CALLER.setGeometry(QtCore.QRect(0, 0, 331, 531))
		self.CLIENTTHREADRUNNER=ClientThread()
		self.CLIENTTHREADRUNNER.start()
		self.CLIENTTHREADRUNNER.CallEnded.connect(lambda:self.CALLENDED())
		self.InfoText.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:24pt; font-weight:400; font-style:normal;\">\n"
"<p dir=\'rtl\' style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">You are in a call with</p><p>%s</p></body></html>"%NumberDialed))


	def CALL(self):
		global NumberDialed
		MATCHSTR='[1-9][0-9]{9}'
		if re.match(MATCHSTR,NumberDialed)!=None:
			self.CALLINIT()
		else:
			print("Invalid Number")

	def KEYPRESSED(self,val):
		global NumberDialed
		if val!='bksp':
			NumberDialed+=str(val)
		else:
			NumberDialed=NumberDialed[:len(NumberDialed)-1]
		self.NumberLab.setText(NumberDialed)


	def retranslateUi(self, MainWindow):
		_translate = QtCore.QCoreApplication.translate
		MainWindow.setWindowTitle(_translate("MainWindow", "PyPhone"))
		self.KEY5.setText(_translate("MainWindow", "5"))
		self.KEY4.setText(_translate("MainWindow", "4"))
		self.KEY8.setText(_translate("MainWindow", "8"))
		self.KEYHASH.setText(_translate("MainWindow", "#"))
		self.KEY2.setText(_translate("MainWindow", "2"))
		self.KEY0.setText(_translate("MainWindow", "0"))
		self.KEY9.setText(_translate("MainWindow", "9"))
		self.KEY7.setText(_translate("MainWindow", "7"))
		self.KEY6.setText(_translate("MainWindow", "6"))
		self.KEY3.setText(_translate("MainWindow", "3"))
		self.KEY1.setText(_translate("MainWindow", "1"))
		self.KEYSTAR.setText(_translate("MainWindow", "*"))
		self.CallerInfo.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:24pt; font-weight:400; font-style:normal;\">\n"
"<p dir=\'rtl\' style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Incomming Call from</p></body></html>"))

if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	app.setStyleSheet('QMainWindow{background-color: darkgray;border: 1px solid black;}')
	MainWindow = QtWidgets.QMainWindow()
	ui = Ui_MainWindow()
	ui.setMouseTracking(True)
	MainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
	ui.setupUi(MainWindow)
	MainWindow.show()
	sys.exit(app.exec_())
