# -*- coding: UTF-8 -*-
import xbmc
import xbmcgui
import json
import time
import top
import os
from datetime import datetime, timedelta
import _strptime
import buggalo
import util
import traceback
import scutils

class MyPlayer(xbmc.Player):

    def __init__(self, *args, **kwargs):
        try:
            self.log("[SC] player 1")
            self.estimateFinishTime = '00:00:00'
            self.realFinishTime = '00:00:00'
            self.itemDuration = '00:00:00'
            self.win = xbmcgui.Window(10000)
        except Exception:
            self.log("SC Chyba MyPlayer: %s" % str(traceback.format_exc()))

    @staticmethod
    def executeJSON(request):
        # =================================================================
        # Execute JSON-RPC Command
        # Args:
        # request: Dictionary with JSON-RPC Commands
        # Found code in xbmc-addon-service-watchedlist
        # =================================================================
        rpccmd = json.dumps(request)  # create string from dict
        json_query = xbmc.executeJSONRPC(rpccmd)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        return json_response

    @staticmethod
    def get_sec(time_str):
        # nasty bug appears only for 2nd and more attempts during session
        # workaround from: http://forum.kodi.tv/showthread.php?tid=112916
        try:
            t = datetime.strptime(time_str, "%H:%M:%S")
        except TypeError:
            t = datetime(*(time.strptime(time_str, "%H:%M:%S")[0:6]))
        return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    @staticmethod
    def log(text):
        xbmc.log(str([text]), xbmc.LOGDEBUG)
        
    def setWatched(self):
        if self.itemType == u'episode':
            metaReq = {"jsonrpc": "2.0",
                       "method": "VideoLibrary.SetEpisodeDetails",
                       "params": {"episodeid": self.itemDBID,
                                  "playcount": 1},
                       "id": 1}
            self.executeJSON(metaReq)
        elif self.itemType == u'movie':
            metaReq = {"jsonrpc": "2.0",
                       "method": "VideoLibrary.SetMovieDetails",
                       "params": {"movieid": self.itemDBID,
                                  "playcount": 1},
                       "id": 1}
            self.executeJSON(metaReq)

    def createResumePoint(self, seconds, total):
        try:
            pomer = seconds / total
            if pomer < 0.05:
                return
            self.pomSlovnik.update({self.itemDBID: seconds})
        except Exception:
            buggalo.onExceptionRaised({'seconds: ': seconds})
        return

    def onPlayBackStarted(self):
        self.log("[SC] Zacalo sa prehravat")
        mojPlugin = self.win.getProperty(top.__scriptid__)
        if top.__scriptid__ not in mojPlugin:
            util.debug("[SC] Nieje to moj plugin ... ")
            #return;
        util.debug("[SC] JE to moj plugin ... %s" % str(mojPlugin))
        self.win.clearProperty(top.__scriptid__)
        try:
            if not self.isPlayingVideo():
                return
            
            while True:
                scutils.KODISCLib.sleep(1000)
                if xbmc.abortRequested:
                    return
                self.itemDuration = xbmc.getInfoLabel(
                    'Player.TimeRemaining(hh:mm:ss)')
                if (self.itemDuration != '') and (self.itemDuration != '00:00:00'):
                    self.itemDuration = self.get_sec(self.itemDuration)
                    break
            # plánovaný čas dokončení 100 % přehrání
            self.estimateFinishTime = xbmc.getInfoLabel(
                'Player.FinishTime(hh:mm:ss)')
            season = xbmc.getInfoLabel('VideoPlayer.Season')
            episode = xbmc.getInfoLabel('VideoPlayer.Episode')
            showtitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
            year = xbmc.getInfoLabel('VideoPlayer.Year')
            title = xbmc.getInfoLabel('VideoPlayer.Title')
            imdb = xbmc.getInfoLabel("VideoPlayer.IMDBNumber") #"ListItem.IMDBNumber")
            if 0 and imdb is None:
                imdb = xbmc.getInfoLabel("ListItem.Property(IMDBNumber)")

            res = self.executeJSON({'jsonrpc': '2.0', 'method': 'Player.GetItem', 
                'params': {'playerid': 1}, 'id': 1})
            if res:
                _filename = None
                try:
                    _filename = os.path.basename(self.getPlayingFile())
                except:
                    util.debug("[SC] onPlayBackStarted() - Exception trying to get playing filename, player suddenly stopped.")
                    return
                util.debug("[SC] Zacalo sa prehravat: imdb: %s dur: %s est: %s fi: [%s] | %sx%s - title: %s (year: %s) showtitle: %s" % (str(imdb), self.itemDuration, self.estimateFinishTime, _filename, str(season), str(episode), str(title), str(year), str(showtitle)))
                if 'item' in res and 'id' not in res['item']:
                    util.debug("[SC] prehravanie mimo kniznice")
        except Exception:
            self.log("SC Chyba MyPlayer: %s" % str(traceback.format_exc()))
            pass

    def onPlayBackEnded(self):
        self.log("[SC] Skoncilo sa prehravat")
        return
        self.setWatched()

    def onPlayBackStopped(self):
        self.log("[SC] Stoplo sa prehravanie")
        return
        try:
            # Player.TimeRemaining  - už zde nemá hodnotu
            # Player.FinishTime - kdy přehrávání skutečně zkončilo
            timeDifference = 55555
            timeRatio = 55555
            self.realFinishTime = xbmc.getInfoLabel(
                'Player.FinishTime(hh:mm:ss)')
            timeDifference = self.get_sec(self.estimateFinishTime) - \
                self.get_sec(self.realFinishTime)
            timeRatio = timeDifference.seconds / \
                float((self.itemDuration).seconds)
            # upravit podmínku na 0.05 tj. zbývá shlédnout 5%
            if abs(timeRatio) < 0.1:
                self.setWatched()
            else:
                self.createResumePoint((1 - timeRatio) * float((self.itemDuration).seconds),
                                       float((self.itemDuration).seconds))
        except Exception:
            pass
            buggalo.onExceptionRaised({'self.itemDuration: ': self.itemDuration,
                                       'self.estimateFinishTime: ': self.estimateFinishTime,
                                       'self.realFinishTime: ': self.realFinishTime,
                                       'timeDifference: ': timeDifference,
                                       'timeRatio: ': timeRatio, })

    def waitForChange(self):
        scutils.KODISCLib.sleep(2000)
        while True:
            pom = xbmc.getInfoLabel('Player.FinishTime(hh:mm:ss)')
            if pom != self.estimateFinishTime:
                self.estimateFinishTime = pom
                break
            scutils.KODISCLib.sleep(100)

    def onPlayBackResumed(self):
        self.log("[SC] Znova sa prehrava")
        return;
        self.waitForChange()

    def onPlayBackSpeedChanged(self, speed):
        self.log("[SC] Zmennila sa rychlost prehravania %s" % speed)
        return
        self.waitForChange()

    def onPlayBackSeek(self, time, seekOffset):
        self.log("[SC] Seekujem %s %s" % (time, seekOffset))
        return
        self.waitForChange()
    
    def onPlayBackPaused(self):
        self.log("[SC] Pauza")
        return
        