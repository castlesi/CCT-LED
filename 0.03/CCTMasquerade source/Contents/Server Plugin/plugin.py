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
        if instanceVers >= kCurDevVersCount:
            self.logger.debug(device.name + u": Device Version is up to date")
        elif instanceVers < kCurDevVersCount:
            newProps = device.pluginProps

            newProps["devVersCount"] = kCurDevVersCount
            device.replacePluginPropsOnServer(newProps)
            device.stateListOrDisplayStateIdChanged()
            self.logger.debug(u"Updated " + device.name + " to version " + str(kCurDevVersCount))
        else:
            self.logger.error(u"Unknown device version: " + str(instanceVers) + " for device " + device.name)

        self.logger.debug("Adding Device %s (%d) to device list" % (device.name, device.id))
        assert device.id not in self.masqueradeList
        self.masqueradeList[device.id] = device
        baseDevice = indigo.devices[int(device.pluginProps["baseDevice"])]
        self.updateDevice(device, None, baseDevice)


    def deviceStopComm(self, device):
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
        indigo.PluginBase.deviceDeleted(self, delDevice)

        for myDeviceId, myDevice in sorted(self.masqueradeList.iteritems()):
            baseDevice = int(myDevice.pluginProps["baseDevice"])
            if delDevice.id == baseDevice:
                self.logger.info(u"A device (%s) that was being Masqueraded has been deleted.  Disabling %s" % (delDevice.name, myDevice.name))
                indigo.device.enable(myDevice, value=False)   #disable it


    def deviceUpdated(self, oldDevice, newDevice):
        indigo.PluginBase.deviceUpdated(self, oldDevice, newDevice)

        for masqDeviceId, masqDevice in sorted(self.masqueradeList.iteritems()):
            baseDevice = int(masqDevice.pluginProps["baseDevice"])
            if oldDevice.id == baseDevice:
                self.updateDevice(masqDevice, oldDevice, newDevice)


    def updateDevice(self, masqDevice, oldDevice, newDevice):


            masqState = masqDevice.pluginProps["masqState"]
            if oldDevice == None or oldDevice.states[masqState] != newDevice.states[masqState]:
                baseValue = int(newDevice.states[masqState])
  #              self.logger.debug(u"updateDevice masqDimmer: %s (%d) --> %s (%d)" % (newDevice.name, baseValue, masqDevice.name, scaledValue))
                masqDevice.updateStateOnServer(key='brightnessLevel', value = baseValue)



    ########################################

    def actionControlDevice(self, action, dev):

            if action.deviceAction == indigo.kDeviceAction.TurnOn:
                self.logger.debug(u"actionControlDevice: \"%s\" Turn On" % dev.name)
 #               props = { dev.pluginProps["masqValueField"] : dev.pluginProps["highLimitState"] }
                indigo.device.turnOn(int(dev.pluginProps["baseDevice"]))

            elif action.deviceAction == indigo.kDeviceAction.TurnOff:
                self.logger.debug(u"actionControlDevice: \"%s\" Turn Off" % dev.name)
  #              props = { dev.pluginProps["masqValueField"]: dev.pluginProps["lowLimitState"] }
                indigo.device.turnOff(int(dev.pluginProps["baseDevice"]))

            elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
  #              self.logger.debug(u"actionControlDevice: \"%s\" Set Brightness to %d (scaled = %s)" % (dev.name, action.actionValue, scaledValueString))
                self.logger.debug(action.actionValue)
                self.logger.debug(int(dev.pluginProps["baseDevice"]))
  #              props = { dev.pluginProps["masqValueField"] : scaledValueString }
                indigo.dimmer.setBrightness(int(dev.pluginProps["baseDevice"]),  action.actionValue)

            else:
                self.logger.error(u"actionControlDevice: \"%s\" Unsupported action requested: %s" % (dev.name, str(action)))


    ########################################################################
    # This method is called to generate a list of plugin identifiers / names
    ########################################################################


    def getStateList(self, filter="", valuesDict=None, typeId="", targetId=0):

        retList = []
        baseDeviceId = valuesDict.get("baseDevice", None)
        if not baseDeviceId:
            return retList

        baseDevice = indigo.devices[int(baseDeviceId)]

        for stateKey, stateValue in baseDevice.states.items():
            retList.append((stateKey, stateKey))
        retList.sort(key=lambda tup: tup[1])
        return retList



    # doesn't do anything, just needed to force other menus to dynamically refresh

    def menuChanged(self, valuesDict, typeId, devId):
        return valuesDict


    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
        self.logger.debug("getDeviceConfigUiValues, typeID = " + typeId)
        valuesDict = indigo.Dict(pluginProps)
        errorsDict = indigo.Dict()

#        self.logger.debug("getDeviceConfigUiValues, valuesDict =\n" + str(valuesDict))

        return (valuesDict, errorsDict)

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug(u"validateDeviceConfigUi, typeID = " + typeId)
        errorsDict = indigo.Dict()

#        self.logger.debug("validateDeviceConfigUi, valuesDict =\n" + str(valuesDict))

        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)
