# -*- coding: UTF-8 -*-

# appModule for VLC Media Player

# V 1.1 dev
# November 2015 by Javi Dominguez (Javichi)

import appModuleHandler
import addonHandler
from NVDAObjects.IAccessible import IAccessible
import controlTypes
import api
import winUser
import ui
import tones
from time import sleep

addonHandler.initTranslation()

class AppModule(appModuleHandler.AppModule):
	
	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if obj.windowClassName == "QWidget" and obj.role == controlTypes.ROLE_BORDER:
			if obj.childCount == 3:
				obj.role = controlTypes.ROLE_STATUSBAR
			else:
				obj.role = controlTypes.ROLE_PANE
			clsList.insert(0, VLC_pane)
		elif obj.windowClassName == "QTool" and obj.role == controlTypes.ROLE_SPINBUTTON:
			clsList.insert(0, VLC_spinButton)
		elif obj.role == controlTypes.ROLE_WINDOW:
			clsList.insert(0, VLC_mainWindow)
		elif obj.windowStyle == -1764884480:
			clsList.insert(0, VLC_mediaInfo)
			
	def event_gainFocus(self, obj, nextHandler):
		if controlTypes.STATE_INVISIBLE in obj.states:
			obj = api.getForegroundObject()
			obj.setFocus()
		nextHandler()
		
	def script_conrolPaneToForeground(self, gesture):
		obj = api.getForegroundObject()
		api.setFocusObject(obj)
		tones.beep(1200, 30)
		
	__gestures = {
	"kb:NVDA+F5": "conrolPaneToForeground"
	}
	
class VLC_mainWindow(IAccessible):
	tpItemIndex = 100
	playlist = []
	playlistIndex = -1

	def composeTime(self, t="00:00"):
		"Convert time from hh:mm:ss to h hours m minutes s seconds"
		t = t.split(":")
		if len(t) == 3:
			hours, minutes, seconds = t
			try:
				hours = int(hours)
			except:
				return("")
			if hours > 1:
				cTime = _("%d hours ") % hours
			else:
				cTime = _("%d hour ") % hours
		else:
			minutes, seconds = t
			cTime = ""
		try:
			minutes = int(minutes)
			seconds = int(seconds)
		except:
			return("")
		if minutes > 0:
			if minutes > 1:
				cTime = _("%s%d minutes ") % (cTime, minutes)
			else:
				cTime = _("%s%d minute ") % (cTime, minutes)
		if seconds > 1:
			cTime = _("%s %d seconds") % (cTime, seconds)
		else:
			cTime = _("%s %d second") % (cTime, seconds)
		return (cTime)

	def isPlaying(self):
		"looks in play/pause button to see if it's playing"
		obj = api.getForegroundObject()
		if "Pause" in obj.getChild(2).getChild(3).getChild(5).description:
			return(True)
		return(False)
		
	def isChecked(self, c):
		">Looks if is checked: c=1=Shuffle and c=2=Repeat"
		obj = api.getForegroundObject()
		try:
			if controlTypes.STATE_CHECKED in obj.getChild(2).getChild(3).children[3:][-c].states:
				return(True)
		except:
			pass
		return(False)
		
	def sayElapsedTime(self):
		obj = api.getForegroundObject()
		elapsedTime = obj.getChild(1).getChild(3).name.split("/")[0]
		ui.message(self.composeTime(elapsedTime))
		
	def moveToItem(self, index):
		obj = api.getForegroundObject()
		toolPaneItems = []
		# Playback controls
		for item in obj.getChild(2).getChild(3).children[3:]:
			if controlTypes.STATE_INVISIBLE not in item.states and item.role != controlTypes.ROLE_GRIP:
				toolPaneItems.append(item)
		# Add advanced controls
		for item in obj.getChild(2).getChild(3).firstChild.children:
			if controlTypes.STATE_INVISIBLE not in item.states:
				toolPaneItems.append(item)
		# Add TV text controls
		for item in obj.getChild(2).getChild(3).getChild(1).children:
			if controlTypes.STATE_INVISIBLE not in item.states:
				toolPaneItems.append(item)
		# Add DVD controls
		for item in obj.getChild(2).getChild(3).getChild(2).children:
			if controlTypes.STATE_INVISIBLE not in item.states:
				toolPaneItems.append(item)
		# Add mute button
		if controlTypes.STATE_INVISIBLE not in obj.getChild(2).getChild(3).getChild(3).firstChild.states:
			toolPaneItems.append(obj.getChild(2).getChild(3).getChild(3).firstChild)
		if len(toolPaneItems) == 0:
			ui.message(_("There are no controls available"))
			return()
		if index >= len(toolPaneItems):
			index = 1
		if index < 1:
			index = len(toolPaneItems)-1
		ui.message(toolPaneItems[index].description)
		if toolPaneItems[index].role == controlTypes.ROLE_CHECKBOX:
			if controlTypes.STATE_CHECKED in toolPaneItems[index].states:
				ui.message(_("checked"))
			else:
				ui.message(_("not checked"))
		if controlTypes.STATE_UNAVAILABLE in toolPaneItems[index].states:
			ui.message(_("unavailable"))
		api.setNavigatorObject(toolPaneItems[index])
		api.moveMouseToNVDAObject(toolPaneItems[index])
		api.setMouseObject(toolPaneItems[index])
		self.tpItemIndex = index
		
	def script_moveToNextItem(self, gesture):
		try:
			self.moveToItem(self.tpItemIndex+1)
		except:
			gesture.send()
		
	def script_moveToPreviousItem(self, gesture):
		try:
			self.moveToItem(self.tpItemIndex-1)
		except:
			gesture.send()
		
	def script_backAndForward(self, gesture):
		gesture.send()
		self.sayElapsedTime()
		
	def script_readStatusBar(self, gesture):
		"Reads the status bar information"
		obj = api.getForegroundObject()
		if obj.getChild(1).role == controlTypes.ROLE_STATUSBAR:
			try:
				ui.message("%s " % obj.getChild(1).getChild(1).name)
				elapsedTime, totalTime = obj.getChild(1).getChild(3).name.split("/")
				elapsedTime = self.composeTime(elapsedTime)
				totalTime = self.composeTime(totalTime)
				ui.message(_("%s of %s") % (elapsedTime, totalTime))
				if self.isPlaying():
					ui.message(_(" playing"))
				if self.isChecked(2):
					ui.message(_("Repeat mode"))
				if self.isChecked(1):
					ui.message(_("Shuffle mode"))
				return()
			except:
				pass
			
	def getPlaylist(self):
		"Make a list from anchored playlist if it's showed"
		obj = api.getForegroundObject()
		obj = obj.firstChild
		while obj and obj.role != controlTypes.ROLE_SPLITBUTTON:
			obj = obj.next
		try:
			playlist = []
			for item in obj.simpleFirstChild.children:
				if (item.role == controlTypes.ROLE_TREEVIEWITEM\
				or item.role == controlTypes.ROLE_LISTITEM):
					playlist.append(item)
			return(playlist)
		except:
			return(None)
		
	def moveToPlaylistItem(self, index):
		if not self.playlist:
			self.playlist = self.getPlaylist()
			if not self.playlist:
				return(False)
			ui.message(_("%d items in playlist") % len(self.playlist))
		l = len(self.playlist)
		if index < 0:
			self.playlistIndex = 0
			tones.beep(200, 50)
		elif index >= l:
			self.playlistIndex = l-1
			tones.beep(200, 50)
		else:
			self.playlistIndex = index
		api.moveMouseToNVDAObject(self.playlist[self.playlistIndex])
		api.setNavigatorObject(self.playlist[self.playlistIndex])
		api.setMouseObject(self.playlist[self.playlistIndex])
		ui.message("%d %s" % (self.playlistIndex+1, self.playlist[self.playlistIndex].name))
		return(True)
			
	def script_nextPlaylistItem(self, gesture):
		if not self.moveToPlaylistItem(self.playlistIndex+1):
			ui.message(_("Playlist is not visible"))
		
	def script_previousPlaylistItem(self, gesture):
		if not self.moveToPlaylistItem(self.playlistIndex-1):
			ui.message(_("Playlist is not visible"))
		
	def script_doAction(self, gesture):
		obj = api.getNavigatorObject()
		try:
			obj.doAction()
			sleep(0.2)
			if obj.role == controlTypes.ROLE_CHECKBOX:
				if controlTypes.STATE_CHECKED in obj.states:
					ui.message(_("checked"))
				else:
					ui.message(_("not checked"))
			ui.message(obj.description)
		except:
			if self.mouseClick():
				types = (controlTypes.ROLE_LISTITEM, controlTypes.ROLE_TREEVIEWITEM)
				if obj.role in types:
					self.mouseClick()
			else:
				ui.message(_("This item is outside the window"))
			
	def mouseClick(self, button="left"):
		if controlTypes.STATE_INVISIBLE in api.getMouseObject().states:
			return(False)
		if button == "left":
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
			return(True)
		if button == "right":
			winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTUP,0,0,None,None)
			return(True)
			
	def script_contextMenu(self, gesture):
		types = (controlTypes.ROLE_LISTITEM, controlTypes.ROLE_TREEVIEWITEM)
		obj = api.getMouseObject()
		if "VLC" in obj.windowText and obj.role in types:
			if not self.mouseClick("right"):
				ui.message(_("This item is outside the window"))
			return()
		gesture.send()

	def script_repeat(self, gesture):
		ui.message(_("Repeat mode"))
		gesture.send()
		sleep(0.1)
		if self.isChecked(2):
			ui.message(_("Checked"))
		else:
			ui.message(_("not checked"))
			
	def script_shuffle(self, gesture):
		ui.message(_("Shuffle mode"))
		gesture.send()
		sleep(0.1)
		if self.isChecked(1):
			ui.message(_("Checked"))
		else:
			ui.message(_("not checked"))
			
	__gestures = {
		"kb:I": "readStatusBar",
		"kb:L": "repeat",
		"kb:R": "shuffle",
		"kb:Tab": "moveToNextItem",
		"kb:Shift+Tab": "moveToPreviousItem",
		"kb:Control+RightArrow": "backAndForward",
		"kb:Control+LeftArrow": "backAndForward",
		"kb:Shift+RightArrow": "backAndForward",
		"kb:Shift+LeftArrow": "backAndForward",
		"kb:Alt+RightArrow": "backAndForward",
		"kb:Alt+LeftArrow": "backAndForward",
		"kb:Alt+Control+RightArrow": "backAndForward",
		"kb:Alt+Control+LeftArrow": "backAndForward",
		"kb:enter": "doAction",
		"kb:downArrow": "nextPlaylistItem",
		"kb:upArrow": "previousPlaylistItem",
		"kb:applications": "contextMenu"
		}
		
class VLC_pane(IAccessible):
	pass
	
class VLC_spinButton(IAccessible):
	
	def event_gainFocus(self):
		ui.message(self.value)
		
	def event_valueChange(self):
		ui.message(self.value)

class VLC_mediaInfo(IAccessible):
	
	def event_gainFocus(self):
		cTypes = {
		8: _("edit"),
		9: _("button"),
		23: _("tab control")
		}
		if self.simplePrevious.role == controlTypes.ROLE_STATICTEXT:
			ui.message(self.simplePrevious.name)
		if self.name:
			ui.message(self.name)
		if self.value:
			ui.message(self.value)
		if self.description:
			ui.message(self.description)
		if self.role in cTypes:
			ui.message(cTypes[self.role])
		
	def script_nextControl(self, gesture):
		obj = api.getFocusObject()
		if obj.role == controlTypes.ROLE_EDITABLETEXT\
		and obj.simpleNext.role == controlTypes.ROLE_TABCONTROL:
			obj.parent.getChild(1).setFocus()
		else:
			gesture.send()
		
	def script_previousControl(self, gesture):
		obj = api.getFocusObject()
		if obj.role == controlTypes.ROLE_EDITABLETEXT\
		and obj.simpleNext.role == controlTypes.ROLE_TABCONTROL:
			obj.simplePrevious.simplePrevious.setFocus()
		else:
			gesture.send()
		
	__gestures = {
	"kb:Tab": "nextControl",
	"kb:Shift+Tab": "previousControl"
	}
	