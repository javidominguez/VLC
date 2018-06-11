# -*- coding: UTF-8 -*-

# appModule for VLC Media Player 3X
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2015-2018 Javi Dominguez <fjavids@gmail.com>

import appModuleHandler
import addonHandler
from NVDAObjects.IAccessible import IAccessible, qt
from NVDAObjects.behaviors import Dialog
import controlTypes
import api
import winUser
import ui
from speech import speakObject
import tones
from time import sleep
import gui
import wx
import config
from gui import settingsDialogs

addonHandler.initTranslation()

confspec = {
	"reportTimeWhenTrackSlips":"boolean(default=true)"
}
config.conf.spec['VLC']=confspec

class AppModule(appModuleHandler.AppModule):

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		self.tpItemIndex = 100
		self.prefsMenu = gui.mainFrame.sysTrayIcon.menu.GetMenuItems()[0].GetSubMenu()
		#TRANSLATORS: The configuration option in NVDA Preferences menu
		self.VLCSettingsItem = self.prefsMenu.Append(wx.ID_ANY, _(u"VLC settings..."), _(u"Change VLC appModule settings"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onVLCMenu, self.VLCSettingsItem)

	def terminate(self):
		try:
			self.prefsMenu.RemoveItem(self.VLCSettingsItem)
		except:
			pass

	def onVLCMenu(self, evt):
		gui.mainFrame._popupSettingsDialog(VLCSettings)

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if obj.role == controlTypes.ROLE_APPLICATION:
			clsList.insert(0, VLC_application)
		if obj.windowClassName == u'Qt5QWindowIcon':
			if obj.role == controlTypes.ROLE_BORDER or obj.role == controlTypes.ROLE_PANE:
				if obj.childCount == 3:
					obj.role = controlTypes.ROLE_STATUSBAR
				else:
					obj.role = controlTypes.ROLE_PANE
				clsList.insert(0, VLC_pane)
			elif obj.role == controlTypes.ROLE_SPINBUTTON:
				clsList.insert(0, VLC_spinButton)
			elif obj.role == controlTypes.ROLE_WINDOW and obj.firstChild.role == controlTypes.ROLE_MENUBAR:
				clsList.insert(0, VLC_mainWindow)
			elif obj.windowStyle == -1764884480 and obj.isFocusable:
				try:
					container = obj.container.container.container.container
				except AttributeError:
					pass
				else:
					if container and container.name and container.role == controlTypes.ROLE_PANE:
						if obj.previous.role == controlTypes.ROLE_STATICTEXT:
							obj.name = obj.previous.name 
						clsList.insert(0, VLC_mediaInfo)
		if obj.role == controlTypes.ROLE_DIALOG:
			clsList.insert(0, VLC_Dialog)

	def event_foreground(self, obj, nextHandler):
		appWindow = api.getForegroundObject().parent
		if appWindow.role == controlTypes.ROLE_APPLICATION:
			api.setFocusObject(appWindow)
		nextHandler()

	def event_gainFocus(self, obj, nextHandler):
		if controlTypes.STATE_INVISIBLE in obj.states:
			obj = api.getForegroundObject()
			obj.setFocus()
		nextHandler()

	def script_controlPaneToForeground(self, gesture):
		obj = api.getForegroundObject()
		api.setFocusObject(obj)
		tones.beep(1200, 30)

	def script_toggleVerbosity(self, gesture):
		if config.conf['VLC']['reportTimeWhenTrackSlips']:
			config.conf['VLC']['reportTimeWhenTrackSlips'] = False
		else:
			config.conf['VLC']['reportTimeWhenTrackSlips'] = True
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_toggleVerbosity.__doc__ = _("Toggle verbosity: if enabled, it will announce the elapsed time when you slide the track")

	__gestures = {
	"kb:NVDA+F5": "controlPaneToForeground",
	"kb:F2":"toggleVerbosity"
	}

class VLC_Dialog(Dialog):
	pass

class VLC_application(qt.Application):
	pass

class VLC_mainWindow(IAccessible):

	def _get_playbackControls(self):
		controls =\
		self.getChild(2).getChild(3).children[3:]+\
		self.getChild(2).getChild(3).firstChild.children+\
		self.getChild(2).getChild(3).getChild(1).children+\
		list(self.getChild(2).getChild(3).getChild(2).recursiveDescendants)
		# Add mute button
		if controlTypes.STATE_INVISIBLE not in self.getChild(2).getChild(3).getChild(3).firstChild.states:
			controls.append(self.getChild(2).getChild(3).getChild(3).firstChild)
			return controls

	def _get_volumeDisplay(self):
		return self.getChild(2).getChild(3).getChild(3).getChild(1)

	def _get_playPauseButton(self):
		fg = api.getForegroundObject()
		return fg.getChild(2).getChild(3).getChild(5)

	def event_foreground(self):
		api.setFocusObject(self)

	def event_gainFocus(self):
		self.description = ""
		if not self.focusDialog():
			self.moveToItem(self.appModule.tpItemIndex)

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
		# Translators: As seen in the button Play/Pause of the interface
		if _("Pause") in self.playPauseButton.description:
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
		toolPaneItems = filter(lambda item: controlTypes.STATE_INVISIBLE not in item.states and controlTypes.STATE_UNAVAILABLE not in item.states and item.role != controlTypes.ROLE_GRIP  and item.role != controlTypes.ROLE_BORDER, self.playbackControls)
		if len(toolPaneItems) == 0:
			ui.message(_("There are no controls available"))
			return()
		if index >= len(toolPaneItems):
			index = 1
		if index < 1:
			index = len(toolPaneItems)-1
		speakObject(toolPaneItems[index])
		api.setNavigatorObject(toolPaneItems[index])
		api.setMouseObject(toolPaneItems[index])
		self.appModule.tpItemIndex = index

	def script_moveToNextItem(self, gesture):
		try:
			self.moveToItem(self.appModule.tpItemIndex+1)
		except IOError:
			gesture.send()

	def script_moveToPreviousItem(self, gesture):
		try:
			self.moveToItem(self.appModule.tpItemIndex-1)
		except:
			gesture.send()

	def script_backAndForward(self, gesture):
		gesture.send()
		if config.conf['VLC']['reportTimeWhenTrackSlips']: self.sayElapsedTime()

	def script_readStatusBar(self, gesture):
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
				ui.message(", ".join(
				["%s %s" % (o.description, controlTypes.stateLabels[controlTypes.STATE_CHECKED]) for o in\
				filter(lambda o: o.role == controlTypes.ROLE_CHECKBOX and controlTypes.STATE_CHECKED in o.states, self.playbackControls)]))
			except:
				pass
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_readStatusBar.__doc__ =  _("Reads the status bar information")

	def script_doAction(self, gesture):
		obj = api.getNavigatorObject()
		if obj not in self.playbackControls:
			gesture.send()
			return
		try:
			obj.doAction()
			for state in obj.states:
				ui.message(controlTypes.stateLabels[state])
			if obj.role == controlTypes.ROLE_CHECKBOX and controlTypes.STATE_CHECKED not in obj.states:
				ui.message(_("unchecked"))
		except:
			api.moveMouseToNVDAObject(obj)
			x, y = winUser.getCursorPos()
			if api.getDesktopObject().objectFromPoint(x,y) == obj:
				self.mouseClick()
			else:
				tones.beep(200, 50)
		self.focusDialog()

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

	def getDialog(self):
		fg = api.getForegroundObject()
		obj = fg.simpleNext
		if obj:
			return obj if obj.role == controlTypes.ROLE_DIALOG and controlTypes.STATE_INVISIBLE not in obj.states else None
		return None

	def focusDialog(self):
		dlg = self.getDialog()
		if not dlg: return False
		if not dlg.setFocus():
			api.moveMouseToNVDAObject(dlg)
			self.mouseClick()
		return True

	def script_repeat(self, gesture):
		ui.message(_("Repeat mode"))
		gesture.send()
		sleep(0.1)
		if self.isChecked(2):
			ui.message(controlTypes.stateLabels[controlTypes.STATE_CHECKED])
		else:
			ui.message(_("unchecked"))

	def script_shuffle(self, gesture):
		ui.message(_("Shuffle mode"))
		gesture.send()
		sleep(0.1)
		if self.isChecked(1):
			ui.message(controlTypes.stateLabels[controlTypes.STATE_CHECKED])
		else:
			ui.message(_("unchecked"))

	def script_sayVolume(self, gesture):
		gesture.send()
		if self.volumeDisplay.value and config.conf['VLC']['reportTimeWhenTrackSlips']: ui.message(_("Volume %s") % self.volumeDisplay.value)

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

class VLCSettings(settingsDialogs.SettingsDialog):
	#TRANSLATORS: Settings dialog title
	title=_(u"VLC appModule settings")
	def makeSettings(self, sizer):
		#TRANSLATORS: Report time checkbox
		self.reportTimeEnabled=wx.CheckBox(self, wx.NewId(), label=_(u"Report time when track slips"))
		self.reportTimeEnabled.SetValue(config.conf['VLC']['reportTimeWhenTrackSlips'])
		sizer.Add(self.reportTimeEnabled,border=10,flag=wx.BOTTOM)

	def postInit(self):
		self.reportTimeEnabled.SetFocus()

	def onOk(self, evt):
		config.conf['VLC']['reportTimeWhenTrackSlips'] = self.reportTimeEnabled.GetValue()
		# applyConfig()
		super(VLCSettings, self).onOk(evt)
