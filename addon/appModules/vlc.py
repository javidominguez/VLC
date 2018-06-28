# -*- coding: UTF-8 -*-

# appModule for VLC Media Player 3X
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2015-2018 Javi Dominguez <fjavids@gmail.com>

import appModuleHandler
import addonHandler
from NVDAObjects.IAccessible import IAccessible, qt
from NVDAObjects.behaviors import 	Dialog
import controlTypes
import api
import winUser
import ui
import globalVars
from speech import speakObject
import tones
from time import sleep, time
import textInfos
import re
import gui
import wx
import config
from gui import settingsDialogs
try:
	from gui import NVDASettingsDialog
	from gui.settingsDialogs import SettingsPanel
except:
	SettingsPanel = object
try:
	from qtEditableText import QTEditableText
except:
	from NVDAObjects.behaviors import EditableTextWithAutoSelectDetection as QTEditableText
from string import printable

addonHandler.initTranslation()

confspec = {
	"reportTimeWhenTrackSlips":"boolean(default=true)"
}
config.conf.spec['VLC']=confspec

class AppModule(appModuleHandler.AppModule):

	#TRANSLATORS: category for VLC input gestures
	scriptCategory = _("VLC")

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		self.tpItemIndex = 100
		self.anchoredPlaylist = False
		self.embeddedWindows = {
		#TRANSLATORS: Window or panel that contains the playlist when it is inside main window
		u'PlaylistWidgetClassWindow': _("Playlist")
		}
		if hasattr(settingsDialogs, 'SettingsPanel'):
			NVDASettingsDialog.categoryClasses.append(VLCPanel)
		else:
			self.prefsMenu = gui.mainFrame.sysTrayIcon.preferencesMenu
			#TRANSLATORS: The configuration option in NVDA Preferences menu
			self.VLCSettingsItem = self.prefsMenu.Append(wx.ID_ANY, u"VLC...", _("Change VLC appModule settings"))
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onVLCMenu, self.VLCSettingsItem)

	def terminate(self):
		try:
			if hasattr(settingsDialogs, 'SettingsPanel'):
				NVDASettingsDialog.categoryClasses.remove(VLCPanel)
			else:
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
					if obj.lastChild.role == controlTypes.ROLE_STATICTEXT:
						obj.role = controlTypes.ROLE_STATUSBAR
						clsList.insert(0, VLC_StatusBar)
					elif obj.lastChild and obj.lastChild.firstChild and obj.lastChild.firstChild.firstChild\
					and obj.lastChild.firstChild.firstChild.role == controlTypes.ROLE_MENUBUTTON:
						obj.role = controlTypes.ROLE_PANEL
						#TRANSLATORS: Title of the panel that contains the playlist when it is inside main window
						obj.name = _("Playlist")
						obj.isPresentableFocusAncestor = False
						clsList.insert(0, VLC_AnchoredPlaylist)
				else:
					obj.role = controlTypes.ROLE_LAYEREDPANE
					if obj.windowText in self.embeddedWindows:
						obj.name = self.embeddedWindows[obj.windowText]
					elif api.getForegroundObject().name and obj.windowText != api.getForegroundObject().name:
						obj.description = obj.windowText
					clsList.insert(0, VLC_pane)
			elif obj.role == controlTypes.ROLE_WINDOW:
				if obj.firstChild and obj.firstChild.role == controlTypes.ROLE_MENUBAR:
					clsList.insert(0, VLC_mainWindow)
				elif obj.windowStyle == 1442840576:
					if obj.windowText in self.embeddedWindows:
						obj.name = self.embeddedWindows[obj.windowText]
						obj.isPresentableFocusAncestor = True
					else:
						obj.description = obj.windowText
					clsList.insert(0, VLC_EmbeddedWindow)
			elif obj.windowStyle == -1764884480 and obj.isFocusable:
				try:
					container = obj.container.container.container.container
				except AttributeError:
					pass
				else:
					if container and container.name and container.role == controlTypes.ROLE_LAYEREDPANE:
						if obj.previous and obj.previous.role == controlTypes.ROLE_STATICTEXT:
							obj.name = obj.previous.name 
						clsList.insert(0, VLC_mediaInfo)
		if obj.role == controlTypes.ROLE_SPINBUTTON:
			clsList.insert(0, VLC_spinButton)
		if obj.role == controlTypes.ROLE_DIALOG and (obj.windowClassName == u'Qt5QWindowToolSaveBits' or obj.windowClassName == u'Qt5QWindowIcon'):
			clsList.insert(0, VLC_Dialog)
		if obj.role == controlTypes.ROLE_LISTITEM and obj.windowText == u'StandardPLPanelClassWindow':
			clsList.insert(0, VLC_PlaylistItem)
		if obj.role == controlTypes.ROLE_EDITABLETEXT and obj.windowClassName == u'Qt5QWindowIcon':
			# obj.typeBuffer = ""
			# obj.fakeCaret = len(obj.value)-1 if obj.value else 0
			clsList.insert(0, VLC_EditableText)
			


	def event_foreground(self, obj, nextHandler):
		appWindow = api.getForegroundObject().parent
		if appWindow.role == controlTypes.ROLE_APPLICATION:
			api.setFocusObject(appWindow)
		nextHandler()

	def event_gainFocus(self, obj, nextHandler):
		if obj.role == controlTypes.ROLE_MENUBAR and hasattr(obj.parent, "playbackControls"):
			api.setFocusObject(obj.parent)
		elif (obj.role == controlTypes.ROLE_MENUITEM and obj.parent.parent.windowClassName == u'#32768') or (obj.role == controlTypes.ROLE_POPUPMENU and obj.parent.windowClassName == u'#32768'):
			api.setFocusObject(obj)
		if controlTypes.STATE_INVISIBLE in obj.states:
			obj = api.getForegroundObject()
			obj.setFocus()
		elif obj.description and "<html>" in obj.description:
			# Removes the HTML tags that appear in the description of some objects
			while re.search("<[^(>.*<)]+>([^<]*</style>)?", obj.description): obj.description = obj.description.replace(re.search("<[^(>.*<)]+>([^<]*</style>)?", obj.description).group(), "")
		nextHandler()

	def event_becomeNavigatorObject(self, obj, nextHandler, *args, **kwargs):
		if obj.description and "<html>" in obj.description:
			# Removes the HTML tags that appear in the description of some objects
			while re.search("<[^(>.*<)]+>([^<]*</style>)?", obj.description): obj.description = obj.description.replace(re.search("<[^(>.*<)]+>([^<]*</style>)?", obj.description).group(), "")
		nextHandler()

	def script_controlPaneToForeground(self, gesture):
		obj = api.getForegroundObject()
		if hasattr(obj, "playbackControls"):
			api.setFocusObject(obj)
			obj.moveToItem(self.tpItemIndex)
			tones.beep(1200, 30)
		else:
			tones.beep(200,30)
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_controlPaneToForeground.__doc__ = _("Use it in the main window if tabulating between playback controls stopped working. It'll tries to bring the focus to the playback control pane to get it to work again.")

	def script_toggleVerbosity(self, gesture):
		if config.conf['VLC']['reportTimeWhenTrackSlips']:
			config.conf['VLC']['reportTimeWhenTrackSlips'] = False
		else:
			config.conf['VLC']['reportTimeWhenTrackSlips'] = True
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_toggleVerbosity.__doc__ = _("Toggle verbosity: if enabled, it will announce the elapsed time and volume")

	def script_leaveMenu(self, gesture):
		gesture.send()
		fg = api.getForegroundObject()
		focused = api.getFocusObject()
		# A menuitem from VLC_MainWindow that should let go the focus but keeps it
		if hasattr(fg, "playbackControls")\
		and focused.role == controlTypes.ROLE_MENUITEM\
		and controlTypes.STATE_FOCUSED not in focused.states:
			# If it is an item in a submenu
			if focused.parent.role == controlTypes.ROLE_POPUPMENU\
			and focused.parent.parent.role == controlTypes.ROLE_MENUITEM\
			and focused.simpleParent.simpleParent.role != controlTypes.ROLE_MENUBAR:
				# Return to parent menu
				api.setFocusObject(focused.simpleParent)
				focused.simpleParent.reportFocus()
			else: # Item was in main menu
				# Return to VLC_MainWindow
				api.setFocusObject(fg)
				fg.moveToItem(self.tpItemIndex)

	__gestures = {
	"kb:NVDA+F5": "controlPaneToForeground",
	"kb:escape": "leaveMenu"
	}

class VLC_Dialog(Dialog):

	def event_gainFocus(self):
		self.reportFocus()
		api.setForegroundObject(self)

class VLC_EmbeddedWindow(IAccessible):
	def event_focusEntered(self):
		if self.isPresentableFocusAncestor:
			self.reportFocus()

class VLC_application(qt.Application):
	pass

class VLC_mainWindow(IAccessible):

	#TRANSLATORS: category for VLC input gestures
	scriptCategory = _("VLC")

	def _get_playbackControls(self):
		controls = filter(lambda c: c.role not in [
		controlTypes.ROLE_GRIP, controlTypes.ROLE_BORDER, controlTypes.ROLE_LAYEREDPANE],
		self.getChild(2).getChild(3).children+\
		self.getChild(2).getChild(3).firstChild.children+\
		self.getChild(2).getChild(3).getChild(1).children+\
		list(self.getChild(2).getChild(3).getChild(2).recursiveDescendants))
		# Add mute button
		if controlTypes.STATE_INVISIBLE not in self.getChild(2).getChild(3).getChild(3).firstChild.states:
			controls.append(self.getChild(2).getChild(3).getChild(3).firstChild)
		return controls

	def _get_volumeDisplay(self):
		return self.getChild(2).getChild(3).getChild(3).getChild(1)

	def _get_playPauseButton(self):
		fg = api.getForegroundObject()
		return fg.getChild(2).getChild(3).getChild(5)

	def _get_anchoredPlaylist(self):
		try:
			# Search box in anchored playlist
			searchBox = self.getChild(2).getChild(1).getChild(2).getChild(2)
			return searchBox if searchBox.role == controlTypes.ROLE_EDITABLETEXT and controlTypes.STATE_INVISIBLE not in searchBox.states else None
		except:
			pass
		try:
			# SplitButton in anchored playlist
			splitButton = self.getChild(2).getChild(1).getChild(1).getChild(3)
			return splitButton if splitButton.role == controlTypes.ROLE_SPLITBUTTON and controlTypes.STATE_INVISIBLE not in splitButton.states else None
		except:
			pass
		return None

	def event_foreground(self):
		api.setFocusObject(self)

	def event_gainFocus(self):
		api.setForegroundObject(self)
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
				#TRANSLATORS: Expressing time, several hours, in plural. Maintain the space at the end to separate the next message that will be added.
				cTime = _("%d hours ") % hours
			else:
				#TRANSLATORS: Expressing time, one hour, in singular. Maintain the space at the end to separate the next message that will be added.
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
				#TRANSLATORS: Expressing time, several minutes, in plural. Maintain the space at the end to separate the next message that will be added.
				cTime = _("%s%d minutes ") % (cTime, minutes)
			else:
				#TRANSLATORS: Expressing time, one minute, in singular. Maintain the space at the end to separate the next message that will be added.
				cTime = _("%s%d minute ") % (cTime, minutes)
		if seconds > 1:
			#TRANSLATORS: Expressing time, several seconds, in plural.
			cTime = _("%s %d seconds") % (cTime, seconds)
		else:
			#TRANSLATORS: Expressing time, one second, in singular.
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
		toolPaneItems = filter(lambda item: controlTypes.STATE_INVISIBLE not in item.states and controlTypes.STATE_UNAVAILABLE not in item.states, self.playbackControls)
		if len(toolPaneItems) == 0:
			#TRANSLATORS: Message when there are no playback controls visible on screen, or the addon can't find them.
			ui.message(_("There are no controls available"))
			return()
		if index >= len(toolPaneItems):
			index = 0
		if index < 0:
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
					#TRANSLATORS: Message when the playlist is empty and there is no track to play
					ui.message(_("Empty"))
					return
				ui.message("%s " % self.getChild(1).getChild(1).name)
				elapsedTime, totalTime = self.getChild(1).getChild(3).name.split("/")
				elapsedTime = self.composeTime(elapsedTime)
				totalTime = self.composeTime(totalTime)
				#TRANSLATORS: elapsed time of total time
				ui.message(_("%s of %s") % (elapsedTime, totalTime))
				if self.isPlaying():
					#TRANSLATORS: When announces that a track is playing
					ui.message(_(" playing"))
				ui.message(", ".join(
				["%s %s" % (o.description, controlTypes.stateLabels[controlTypes.STATE_CHECKED]) for o in\
				filter(lambda o: o.role == controlTypes.ROLE_CHECKBOX and controlTypes.STATE_CHECKED in o.states, self.playbackControls)]))
			except:
				pass
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_readStatusBar.__doc__ =  _("Reads the information of the current playback.")

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
		if hasattr(fg, "playbackControls"):
			obj = fg.simpleNext
			while obj:
				if controlTypes.STATE_INVISIBLE not in obj.states:
					return obj
				obj = obj.simpleNext
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

	def script_pushToFront(self, gesture):
		if not self.focusDialog():
			if self.anchoredPlaylist:
				api.setNavigatorObject(self.anchoredPlaylist)
				api.moveMouseToNVDAObject(self.anchoredPlaylist)
				self.mouseClick()
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_pushToFront.__doc__ = _("Brings panels or dialogs that are displayed on the screen, but NVDA is unable to focus automatically to the fore.")

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
		"kb:enter": "doAction",
		"kb:control+tab": "pushToFront"
		}

class VLC_pane(qt.LayeredPane):

	def event_gainFocus(self):
		if self.simpleParent.role == controlTypes.ROLE_PANEL:
			# This panel often retains the focus when it receive it and it is necessary to bring it to the playback window.
			fg = api.getForegroundObject()
			if hasattr(fg, "playbackControls"):
				api.setFocusObject(fg)
				if self.appModule.anchoredPlaylist:
					self.appModule.anchoredPlaylist = False
					fg.moveToItem(self.appModule.tpItemIndex)
		elif self.name:
			ui.message(self.name)
			rGen = self.recursiveDescendants
			timeout = time()+0.10
			while True:
				if time() > timeout: break
				try:
					obj = rGen.next()
				except StopIteration:
					break
				if obj.name and obj.role == controlTypes.ROLE_STATICTEXT and controlTypes.STATE_INVISIBLE not in obj.states and obj.next.role not in [
				controlTypes.ROLE_EDITABLETEXT,
				controlTypes.ROLE_COMBOBOX,
				controlTypes.ROLE_SPINBUTTON]:
					ui.message(obj.name)

	def event_focusEntered(self):
		if self.simpleParent.role == controlTypes.ROLE_PANEL:
			# Announces the anchored playlist
			speakObject(self.simpleParent)
			self.appModule.anchoredPlaylist = True

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

class VLC_AnchoredPlaylist(IAccessible):
	pass

class VLC_PlaylistItem(IAccessible):

	def script_nextItem(self, gesture):
		self.selectItem(self.simpleNext)

	def script_previousItem(self, gesture):
		self.selectItem(self.simplePrevious)

	def selectItem(self, item):
		if item and item.role == controlTypes.ROLE_LISTITEM:
			item.scrollIntoView()
			api.setNavigatorObject(item)
			api.moveMouseToNVDAObject(item)
			x, y = winUser.getCursorPos()
			if api.getDesktopObject().objectFromPoint(x,y) == item:
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
				item.setFocus()
				api.setFocusObject(item)
				if item.name: ui.message(item.name)
			else:
				tones.beep(200,20)

	__gestures = {
	"kb:downArrow": "nextItem",
	"kb:upArrow": "previousItem"
	}

class VLC_StatusBar(IAccessible):
	pass

class VLC_EditableText(QTEditableText):

	def event_gainFocus(self):
		self.reportFocus()
		self.typeBuffer = ""
		self.fakeCaret = len(self.value)-1 if self.value else 0
		self.startSelection = -1
		self.alphanumeric = printable[:62]+u"áéíóúñ"
		self.sign = printable[62:94]

class VLCSettings(settingsDialogs.SettingsDialog):
	#TRANSLATORS: Settings dialog title
	title=_("VLC appModule settings")
	def makeSettings(self, sizer):
		#TRANSLATORS: Report time checkbox
		self.reportTimeEnabled=wx.CheckBox(self, wx.NewId(), label=_("Announce elapsed time and volume"))
		self.reportTimeEnabled.SetValue(config.conf['VLC']['reportTimeWhenTrackSlips'])
		sizer.Add(self.reportTimeEnabled,border=10,flag=wx.BOTTOM)

	def postInit(self):
		self.reportTimeEnabled.SetFocus()

	def onOk(self, evt):
		config.conf['VLC']['reportTimeWhenTrackSlips'] = self.reportTimeEnabled.GetValue()
		super(VLCSettings, self).onOk(evt)

class VLCPanel(SettingsPanel):
	#TRANSLATORS: Settings panel title
	title=_("VLC")
	def makeSettings(self, sizer):
		#TRANSLATORS: Report time checkbox
		self.reportTimeEnabled=wx.CheckBox(self, wx.NewId(), label=_("Announce elapsed time and volume"))
		self.reportTimeEnabled.SetValue(config.conf['VLC']['reportTimeWhenTrackSlips'])
		sizer.Add(self.reportTimeEnabled,border=10,flag=wx.BOTTOM)

	def onSave(self):
		config.conf['VLC']['reportTimeWhenTrackSlips'] = self.reportTimeEnabled.GetValue()

