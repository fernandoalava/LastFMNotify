#!/usr/bin/env python

import ConfigParser
import os
import sys
import threading
import signal
from time import sleep,time
from md5 import md5
import urllib
import logging

logging.basicConfig(filename="/tmp/lastfmnotify.log", level = logging.INFO )


class NotifyNowPlaying():
	def __init__(self,user,password):
		self.user = user
		self.password = password
		self.client = "xms"
		self.version = "1.0"
		self.unixtimestamp = time().__int__()
		
	def GenToken(self):
		self.auth = md5(md5(str(self.password)).hexdigest() + str(self.unixtimestamp)).hexdigest()
	
	def Handshake(self):
		self.GenToken()
		response = urllib.urlopen("http://post.audioscrobbler.com/?hs=true&p=1.2&c=%s&v=%s&u=%s&t=%s&a=%s"%(self.client,self.version,self.user,self.unixtimestamp,self.auth))
		r = str(response.read()).split("\n")
		if r[0]=="OK":
			self.SessionId = r[1]
			self.UrlNotification = r[2]
			self.UrlSubmit = r[3]
			debug("Handshake OK")
			return True
		debug("Handshake Error")
		return False
	
	def SendNotification(self,artist,track,album,sec,track_number,mb_trackid=""):
		params={}
		params['s'] = self.SessionId
		params['a'] = artist
		params['t'] = track
		params['b'] = album
		params['l'] = sec
		params['n'] = track
		params['m'] = mb_trackid
	
		params = urllib.urlencode(params)
		response = urllib.urlopen(self.UrlNotification,params)
		r = str(response.read()).split("\n")
		if r[0]=="OK":
			debug("Notification sent")
			return True
		debug("Error while sending song data")
		return False






try:
	from qt import *
except:
	os.popen( "kdialog --sorry 'PyQt (Qt bindings for Python) is required for this script.'" )
	raise


# Replace with real name
debug_prefix = "[LastFMNotification]"



class Notification( QCustomEvent ):
	__super_init = QCustomEvent.__init__
	def __init__( self, str ):
		self.__super_init(QCustomEvent.User + 1)
		self.string = str

class LastFMNotification( QApplication ):
	""" The main application, also sets up the Qt event loop """
	
	
	def __init__( self, args ):
		QApplication.__init__( self, args )
		debug( "Started." )

		# Start separate thread for reading data from stdin
		self.stdinReader = threading.Thread( target = self.readStdin )
		self.stdinReader.start()

		self.User = os.popen("dcop amarok script readConfig 'ScrobblerUsername'").read().strip()
		self.Password = os.popen("dcop amarok script readConfig 'ScrobblerPassword'").read().strip()

		logging.debug("Notifier Starting...")
		self.objN = NotifyNowPlaying(self.User,self.Password)

############################################################################
# Stdin-Reader Thread
############################################################################

	def readStdin( self ):
		""" Reads incoming notifications from stdin """

		while True:
			# Read data from stdin. Will block until data arrives.
			line = sys.stdin.readline()

			if line:
				qApp.postEvent( self, Notification(line) )
			else:
				break


############################################################################
# Notification Handling
############################################################################

	def customEvent( self, notification ):
		""" Handles notifications """

		string = str(notification.string)
		debug( "Received notification: %s " % string )

		if string.find( "trackChange" ) == 0:
			self.trackChange()

# Notification callbacks. Implement these functions to react to specific notification
# events from Amarok:

	def SendNotify(self):
		artist = str(os.popen("dcop amarok player artist").read().strip())
		track = str(os.popen("dcop amarok player title").read().strip())
		album = str(os.popen("dcop amarok player album").read().strip())
		sec = str(os.popen("dcop amarok player trackTotalTime").read().strip())
		pista = str(os.popen("dcop amarok player track").read().strip())
		

		self.objN.Handshake()
		os.system("dcop amarok playlist shortStatusMessage 'Sending notification to Last.FM'")
		if self.objN.SendNotification(artist,track,album,sec,pista):
			sleep(3)
			os.system("dcop amarok playlist shortStatusMessage '%s-%s sent'"%(artist,track))
			return True
		os.system("dcop amarok playlist shortStatusMessage 'An error occurred while sending %s-%s'"%(artist,track))
		return None
		
		
	def engineStatePlay( self ):
		self.SendNotify()

	def engineStateIdle( self ):
		""" Called when Engine state changes to Idle """
		pass

	def engineStatePause( self ):
		""" Called when Engine state changes to Pause """
		pass

	def engineStateEmpty( self ):
		""" Called when Engine state changes to Empty """
		pass

	def trackChange( self ):
		self.SendNotify()


############################################################################

def debug( message ):
	""" Prints debug message to stdout """

	logging.debug(message)

def main( ):
	app = LastFMNotification( sys.argv )

	app.exec_loop()

def onStop(signum, stackframe):
	""" Called when script is stopped by user """
	
	sys.exit(0)

if __name__ == "__main__":
	mainapp = threading.Thread(target=main)
	mainapp.start()
	signal.signal(15, onStop)
	# necessary for signal catching
	while 0: sleep(120)
