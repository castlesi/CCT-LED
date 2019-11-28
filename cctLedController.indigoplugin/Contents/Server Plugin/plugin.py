#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
## Python to interface with MyQ garage doors.
## based on https://github.com/Einstein42/myq-garage

import os
import plistlib
import sys
import time
import logging
import xml.etree.ElementTree as ET

kCurDevVersCount = 0        # current version of plugin devices

################################################################################
class Plugin(indigo.PluginBase):

    ########################################
    # Main Plugin methods
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))

    def startup(self):
        # indigo.debugger()
        indigo.server.log(u"Starting Masquerade")
        self.masqueradeList = {}
        indigo.devices.subscribeToChanges()

    def shutdown(self):
        indigo.server.log(u"Shutting down Masquerade")

    def runConcurrentThread(self):
        try:
            while True:
                self.sleep(60.0)
        except self.stopThread:
            pass

    def deviceStartComm(self, device):
        instanceVers = int(device.pluginProps.get('devVersCount', 0))
        # indigo.debugger()
        newProps = device.pluginProps
        newProps["SupportsColor"] = True
        self.logger.debug(newProps)
        newProps["devVersCount"] = kCurDevVersCount
        device.replacePluginPropsOnServer(newProps)
        device.stateListOrDisplayStateIdChanged()

        self.logger.debug("Adding Device %s (%d) to device list" % (device.name, device.id))
        assert device.id not in self.masqueradeList
        self.masqueradeList[device.id] = device
        baseWarmDevice = indigo.devices[int(device.pluginProps["baseWarmDevice"])]
        self.updateWarmDevice(device, None, baseWarmDevice)
        baseCoolDevice = indigo.devices[int(device.pluginProps["baseCoolDevice"])]
        self.updateCoolDevice(device, None, baseCoolDevice)
        baseBrightDevice = indigo.devices[int(device.pluginProps["baseBrightDevice"])]
        self.updateBrightDevice(device, None, baseBrightDevice)


    def deviceStopComm(self, device):
        # indigo.debugger()
        self.logger.debug("Removing Device %s (%d) from device list" % (device.name, device.id))
        assert device.id in self.masqueradeList
        del self.masqueradeList[device.id]

    ########################################
    # Menu Methods
    ########################################

    ########################################
    # ConfigUI methods
    ########################################

    def validatePrefsConfigUi(self, valuesDict):
        self.logger.debug(u"validatePrefsConfigUi called")
        errorDict = indigo.Dict()
        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)
        return (True, valuesDict)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            try:
                self.logLevel = int(valuesDict[u"logLevel"])
            except:
                self.logLevel = logging.INFO
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))


    ################################################################################
    #
    # delegate methods for indigo.devices.subscribeToChanges()
    #
    ################################################################################

    def deviceDeleted(self, delDevice):
#        indigo.debugger()
        indigo.PluginBase.deviceDeleted(self, delDevice)
        for myDeviceId, myDevice in sorted(self.masqueradeList.iteritems()):
            baseWarmDevice = int(myDevice.pluginProps["baseWarmDevice"])
            if delDevice.id == baseWarmDevice:
                self.logger.info(u"A device (%s) that was being Masqueraded has been deleted.  Disabling %s" % (delDevice.name, myDevice.name))
                indigo.device.enable(myDevice, value=False)   #disable it
            baseCoolDevice = int(myDevice.pluginProps["baseCoolDevice"])
            if delDevice.id == baseCoolDevice:
                self.logger.info(u"A device (%s) that was being Masqueraded has been deleted.  Disabling %s" % (delDevice.name, myDevice.name))
                indigo.device.enable(myDevice, value=False)   #disable it
            baseBrightDevice = int(myDevice.pluginProps["baseBrightDevice"])
            if delDevice.id == baseBrightDevice:
                self.logger.info(u"A device (%s) that was being Masqueraded has been deleted.  Disabling %s" % (delDevice.name, myDevice.name))
                indigo.device.enable(myDevice, value=False)   #disable it


    def deviceUpdated(self, oldDevice, newDevice):
        # indigo.debugger()
        indigo.PluginBase.deviceUpdated(self, oldDevice, newDevice)

        for masqDeviceId, masqDevice in sorted(self.masqueradeList.iteritems()):
            baseDevice = int(masqDevice.pluginProps["baseWarmDevice"])
            if oldDevice.id == baseDevice:
                self.updateWarmDevice(masqDevice, oldDevice, newDevice)
            baseDevice = int(masqDevice.pluginProps["baseCoolDevice"])
            if oldDevice.id == baseDevice:
                self.updateCoolDevice(masqDevice, oldDevice, newDevice)
            baseDevice = int(masqDevice.pluginProps["baseBrightDevice"])
            if oldDevice.id == baseDevice:
                self.updateBrightDevice(masqDevice, oldDevice, newDevice)

    def updateWarmDevice(self, cctDevice, oldWarmDevice, newWarmDevice):
        # indigo.debugger()
        masqWarmState = cctDevice.pluginProps["masqWarmState"]
        if oldWarmDevice == None or oldWarmDevice.states[masqWarmState] != newWarmDevice.states[masqWarmState]:
            #indigo.debugger()
            baseWarmValue = int(newWarmDevice.states[masqWarmState])
            cctDevice.updateStateOnServer(key='whiteLevel', value=baseWarmValue)

    def updateCoolDevice(self, cctDevice, oldCoolDevice, newCoolDevice):
        # indigo.debugger()
        masqCoolState = cctDevice.pluginProps["masqCoolState"]
        if oldCoolDevice == None or oldCoolDevice.states[masqCoolState] != newCoolDevice.states[masqCoolState]:
            #indigo.debugger()
            baseCoolValue = int(newCoolDevice.states[masqCoolState])
            cctDevice.updateStateOnServer(key='whiteLevel2', value=baseCoolValue)

    def updateBrightDevice(self, cctDevice, oldBrightDevice, newBrightDevice):
        indigo.debugger()
        masqBrightState = cctDevice.pluginProps["masqBrightState"]
        if oldBrightDevice == None or oldBrightDevice.states[masqBrightState] != newBrightDevice.states[masqBrightState]:
            #indigo.debugger()
            baseBrightValue = int(newBrightDevice.states[masqBrightState])
            baseOnState = newBrightDevice.states['onOffState']
            self.logger.debug(baseBrightValue)
            cctDevice.updateStateOnServer(key='brightnessLevel', value=baseBrightValue)
            cctDevice.updateStateOnServer(key='onOffState', value=baseOnState)
            cctDevice.updateStateImageOnServer(indigo.kStateImageSel.None)


    ########################################

    def actionControlDevice(self, action, dev):
            if action.deviceAction == indigo.kDeviceAction.TurnOn:
                #indigo.debugger()
                self.logger.debug(action.actionValue)
                self.logger.debug(u"actionControlDevice: \"%s\" Turn On" % dev.name)
                indigo.device.turnOn(int(dev.pluginProps["baseBrightDevice"]))
            elif action.deviceAction == indigo.kDeviceAction.TurnOff:
                #indigo.debugger()
                self.logger.debug(action.actionValue)
                self.logger.debug(u"actionControlDevice: \"%s\" Turn Off" % dev.name)
                indigo.device.turnOff(int(dev.pluginProps["baseBrightDevice"]))
            elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
                #indigo.debugger()
                self.logger.debug(action.actionValue)
                self.logger.debug(int(dev.pluginProps["baseBrightDevice"]))
                indigo.dimmer.setBrightness(int(dev.pluginProps["baseBrightDevice"]),  action.actionValue)
            elif action.deviceAction == indigo.kDeviceAction.SetColorLevels:
                #indigo.debugger()
                self.logger.debug(action.actionValue)
                self.logger.debug(action.deviceAction)
                actionColorVals = action.actionValue
                self.logger.debug(actionColorVals)
                if 'whiteLevel' in actionColorVals.keys():
                    indigo.debugger()
                    indigo.dimmer.setBrightness(int(dev.pluginProps["baseWarmDevice"]), int(round(actionColorVals.get("whiteLevel"))))
                elif 'whiteLevel2' in actionColorVals.keys():
                    indigo.debugger()
                    indigo.dimmer.setBrightness(int(dev.pluginProps["baseCoolDevice"]), int(round(actionColorVals.get("whiteLevel2"))))
            else:
                self.logger.error(u"actionControlDevice: \"%s\" Unsupported action requested: %s" % (dev.name, str(action)))


    # doesn't do anything, just needed to force other menus to dynamically refresh

    def menuChanged(self, valuesDict, typeId, devId):
        return valuesDict

    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
        self.logger.debug("getDeviceConfigUiValues, typeID = " + typeId)
        valuesDict = indigo.Dict(pluginProps)
        errorsDict = indigo.Dict()
        self.logger.debug("getDeviceConfigUiValues, valuesDict =\n" + str(valuesDict))
        return (valuesDict, errorsDict)

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug(u"validateDeviceConfigUi, typeID = " + typeId)
        errorsDict = indigo.Dict()
        self.logger.debug("validateDeviceConfigUi, valuesDict =\n" + str(valuesDict))
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

    ########################################################################
    # This method is called to generate a list of plugin identifiers / names
    ########################################################################

    def getWarmStateList(self, filter="", valuesDict=None, typeId="", targetId=0):
        retList = []
        baseWarmDeviceId = valuesDict.get("baseWarmDevice", None)
        if not baseWarmDeviceId:
            return retList
        baseWarmDevice = indigo.devices[int(baseWarmDeviceId)]
        for stateKey, stateValue in baseWarmDevice.states.items():
            retList.append((stateKey, stateKey))
        retList.sort(key=lambda tup: tup[1])
        return retList

    def getCoolStateList(self, filter="", valuesDict=None, typeId="", targetId=0):
        indigo.debugger()
        retList = []
        baseCoolDeviceId = valuesDict.get("baseCoolDevice", None)
        if not baseCoolDeviceId:
            return retList
        baseCoolDevice = indigo.devices[int(baseCoolDeviceId)]
        for stateKey, stateValue in baseCoolDevice.states.items():
            retList.append((stateKey, stateKey))
        retList.sort(key=lambda tup: tup[1])
        return retList

    def getBrightStateList(self, filter="", valuesDict=None, typeId="", targetId=0):
        indigo.debugger()
        retList = []
        baseBrightDeviceId = valuesDict.get("baseBrightDevice", None)
        if not baseBrightDeviceId:
            return retList
        baseBrightDevice = indigo.devices[int(baseBrightDeviceId)]
        for stateKey, stateValue in baseBrightDevice.states.items():
            retList.append((stateKey, stateKey))
        retList.sort(key=lambda tup: tup[1])
        return retList