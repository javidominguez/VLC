# -*- coding: UTF-8 -*-

# appModule for VLC Media Player 3X
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2015-2018 Javi Dominguez <fjavids@gmail.com>

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
			try:
				if obj.simplePrevious.role == controlTypes.ROLE_STATICTEXT:
					obj.name = obj.simplePrevious.name 
				clsList.insert(0, VLC_mediaInfo)
			except AttributeError:
				pass
		elif obj.role == controlTypes.ROLE_SPLITBUTTON\
		or (obj.role == controlTypes.ROLE_GRIP and obj.childCount == 0):
			obj.role = controlTypes.ROLE_PANE
			clsList.insert(0, VLC_pane)

	def event_gainFocus(self, obj, nextHandler):
		if controlTypes.STATE_INVISIBLE in obj.states:
			obj = api.getForegroundObject()
			obj.setFocus()
		nextHandler()

	def script_controlPaneToForeground(self, gesture):
		obj = api.getForegroundObject()
		api.setFocusObject(obj)
		tones.beep(1200, 30)

	__gestures = {
	"kb:NVDA+F5": "controlPaneToForeground"
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
			except ValueError:
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
		except ValueError:
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
		return cTime

	def isPlaying(self):
		"looks in play/pause button to see if it's playing"
		obj = api.getForegroundObject()
		# Translators: As seen in the button Play/Pause of the interface
		if _("Pause") in obj.getChild(2).getChild(3).getChild(5).description:
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
		elapsedTime = self.getChild(1).getChild(3).name.split("/")[0]
		ui.message(self.composeTime(elapsedTime))

	def moveToItem(self, index):
		toolPaneItems = filter(lambda item: controlTypes.STATE_INVISIBLE not in item.states and item.role != controlTypes.ROLE_GRIP  and item.role != controlTypes.ROLE_BORDER,
		self.getChild(2).getChild(3).children[3:]+\
		self.getChild(2).getChild(3).firstChild.children+\
		self.getChild(2).getChild(3).getChild(1).children+\
		list(self.getChild(2).getChild(3).getChild(2).recursiveDescendants))
		# Add mute button
		if controlTypes.STATE_INVISIBLE not in self.getChild(2).getChild(3).getChild(3).firstChild.states:
			toolPaneItems.append(self.getChild(2).getChild(3).getChild(3).firstChild)
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
		except IOError:
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
		if self.getChild(1).role == controlTypes.ROLE_STATUSBAR:
			try:
				if not self.getChild(1).getChild(1).name:
					ui.message(_("Empty"))
					return
				ui.message("%s " % self.getChild(1).getChild(1).name)
				elapsedTime, totalTime = self.getChild(1).getChild(3).name.split("/")
				elapsedTime = self.composeTime(elapsedTime)
				totalTime = self.composeTime(totalTime)
				ui.message(_("%s of %s") % (elapsedTime, totalTime))
				if self.isPlaying():
					ui.message(_(" playing"))
				if self.isChecked(2):
					ui.message(_("Repeat mode"))
				if self.isChecked(1):
					ui.message(_("Shuffle mode"))
			except:
				pass

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

	def script_sayVolume(self, gesture):
		gesture.send()
		ui.message(_("Volume %s") % self.children[2].children[3].children[3].children[1].value)

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
		"kb:RightArrow": "backAndForward",
		"kb:LeftArrow": "backAndForward",
		"kb:upArrow": "sayVolume",
		"kb:downArrow": "sayVolume",
	"kb:Control+upArrow": "sayVolume",
		"kb:Control+downArrow": "sayVolume",
		"kb:enter": "doAction"
		}

class VLC_pane(IAccessible):
	pass

class VLC_spinButton(IAccessible):

	def event_gainFocus(self):
		ui.message(self.value)

	def event_valueChange(self):
		ui.message(self.value)

class VLC_mediaInfo(IAccessible):

	def script_nextControl(self, gesture):
		if self.role == controlTypes.ROLE_EDITABLETEXT\
		and not self.next:
			self.parent.getChild(1).doAction()
		else:
			gesture.send()

	def script_previousControl(self, gesture):
		if self.role == controlTypes.ROLE_EDITABLETEXT\
		and not self.next:
			self.simplePrevious.simplePrevious.doAction()
		else:
			gesture.send()

	__gestures = {
	"kb:Tab": "nextControl",
	"kb:Shift+Tab": "previousControl"
	}
