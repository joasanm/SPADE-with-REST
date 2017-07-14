#!flask/bin/python
from flask import Flask, abort, request
import spade
import sys
import time
import requests
import json


#-----------------------------------------------------------------------
#!!!-----------------GLOBAL VARIABLES--------------------------------!!!
#-----------------------------------------------------------------------


spadeHost = ""
restHost = ""
zone = ""

#region list representated as dictionaries with the name of region, host and representant agent
region_list = []

#time that can wait a client connection are defined in the timeout variable
timeout=10

#variable with the Rest system to use
app = Flask(__name__)


#-----------------------------------------------------------------------
#!!!----------------HOSPITAL REPRESENTANTS---------------------------!!!
#-----------------------------------------------------------------------


class regionRepr(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("regionRepresentant")
        sd.setOwnership("zone")
        sd.addProperty("description", "region representant")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(self.getAID())
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

class restRequest(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        msg = self._receive(block=True)
        aid = msg.getSender().getName()
        rmh = ""
        for i in region_list:
            if i["aid"] == aid:
                rmh = i["remoteHost"]
        content = msg.getContent().split("-")
        result = ""
        try:
            r = requests.get("http://"+rmh+"/patients", data = content[1], timeout = 3)
            result = content[0] + "-" + r.text
        except requests.exceptions.RequestException as e:
            print self.myAgent.getAID().getName() + ": ERROR, connection refused"
            print e
            result = content[0] + "-[]"
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("region")
        msg2.addReceiver(spade.AID.aid(aid, ["xmpp://"+aid]))
        msg2.setContent("requestInformation-" + result)
        self.myAgent.send(msg2)

rr = restRequest()

def startRestRequest(sender):
    rr = restRequest()
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative(sender)
    t = spade.Behaviour.MessageTemplate(template)
    rest.addBehaviour(rr, t)
    print "restRequest Behaviour started"

class reprActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "have_donant":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2])
        elif content[0] == "getPatientsList":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2])
            startRestRequest(aid)
        elif content[0] == "requestInformation":
            msg2.setPerformative("response")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2])
        self.myAgent.send(msg2)

#class sendList(spade.Behaviour.Behaviour):
    #def _process(self):
        #msg = self._receive(block=True)
        #msg2 = spade.ACLMessage.ACLMessage()
        #msg2.setPerformative("response")
        #msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
        #msg2.setContent(msg.getContent())
        #self.myAgent.send(msg2)
        #print "enviar lista"

class AMS(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        a = self.myAgent.getAID()
        aad = spade.AMS.AmsAgentDescription()
        aad.setAID(a)
        aad.setOwnership = "zone"
        result = self.myAgent.modifyAgent(aad)
        if not result:
            print a.getName() + ": WARNING, AMS not updated"


#-----------------------------------------------------------------------
#!!!----------------------ZONE REPRESENTANT--------------------------!!!
#-----------------------------------------------------------------------


class zone(spade.Agent.Agent):
    def _setup(self):
        self.rec = 0
        self.hSender = ""
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("zoneCoordinator")
        sd.setOwnership("zone")
        sd.addProperty("description", "communication with regions & country representant")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(self.getAID())
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

class patientsList(spade.Behaviour.TimeOutBehaviour):
    def onStart(self):
        print "esperando hospitales"

    def timeOut(self):
        print "espera terminada"
        patients = []
        pid = ""
        for x in range(self.myAgent.rec):
            msg = self._receive(False)
            if msg:
                content = msg.getContent().split("-")
                pid = content[0]
                patients += json.loads(content[1])
        self.myAgent.rec = 0
        self.myAgent.hSender = ""
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("complete")
        msg2.setContent(pid + "-" + json.dumps(patients))
        msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
        self.myAgent.send(msg2)

pl = patientsList(4)

def startPatientsList():
    pl = patientsList(4)
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative("response")
    t = spade.Behaviour.MessageTemplate(template)
    rg.addBehaviour(pl, t)
    print "patientsList Behaviour started"

class regionDonant(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        aid = msg.getSender().getName()
        self.myAgent.hsender = aid
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("region")
        msg2.setContent("getPatientsList-" + msg.getContent())
        for i in hospital_list:
            if i["aid"] != aid:
                msg2.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
                self.myAgent.rec += 1
        self.myAgent.send(msg2)
        startPatientsList()


#-----------------------------------------------------------------------
#!!!--------------------------REST AGENT-----------------------------!!!
#-----------------------------------------------------------------------


#agent that resolve request from Rest and comunicates with other agents from the platform 
class RestAgent(spade.Agent.Agent):
    def _setup(self):
        self.petitions = {}
        self.id = 0
        aid = self.getAID()
        print aid.getName() + ": starting"

class petitionCompleted(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        pid = int(content[0])
        self.myAgent.petitions[pid][4] = content[1]
        self.myAgent.petitions[pid][0] = 2

#behaviour with the action that Rest agent can do, depending on the request to resolve
class RestBehav(spade.Behaviour.Behaviour):
    def _process(self):
        if len(self.myAgent.petitions)==0:
            time.sleep(1)
        else:
            for k in self.myAgent.petitions.keys():
                if self.myAgent.petitions[k][0]==0:
                    self.myAgent.petitions[k][0] = 1
                    if self.myAgent.petitions[k][1]=="GET":
                        dad = spade.DF.DfAgentDescription()
                        search=self.myAgent.searchService(dad)
                        self.myAgent.petitions[k][2] = search
                        self.myAgent.petitions[k][0] = 2
                    elif self.myAgent.petitions[k][1]=="GET2":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][2], ["xmpp://"+self.myAgent.petitions[k][2]]))
                        msg.setContent("have_donant-" + str(k) + "-" + self.myAgent.petitions[k][3])
                        self.myAgent.send(msg)

RestBehaviour = RestBehav()

def startRestBehaviour():
    RestBehaviour = RestBehav()
    rest.addBehaviour(RestBehaviour, None)
    print "Rest Behaviour started"

def stopRestBehaviour():
    rest.removeBehaviour(RestBehaviour)
    print "Rest Behaviour stopped"

#GET & OPTIONS request route, linked to funcion information
#if the request is GET, call Rest agent to inform about agent services platform
#request form: [request state, request used, empty string for information to send]
#if the request is OPTIONS, inform about the valid requests to use on this Rest API
@app.route('/', methods=['GET', 'OPTIONS'])
def informacion():
    if request.method=='GET':
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, "GET", ""]
        endtime=time.time()+timeout
        remaining=endtime-time.time()  
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            serv=""
            for a in rest.petitions[idp][2]:
                serv+=str(a)
            del rest.petitions[idp]
            return serv
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)
    else:
        return """-GET / -> return services list of the platform
-GET /average-> return average temperature in Celsius from diferents city agent sensors
-OPTIONS / -> return list of possible requests from the platform
"""

#GET request route, linked to funcion consult
#Call Rest agent to get information about the local temperature from some local zones,
#representated by agents, and get its average
#request form: [request state, request used, empty string for information to send]
@app.route('/<string:region>/donor', methods=['GET'])        #COMPLETAR
def consult(region):
    a = ""
    print request.remote_addr
    for i in region_list:
        if i["region"] == region:
            a = i["aid"]
    if len(a) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0,"GET2", a, request.data, ""]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][4]
            del rest.petitions[idp]
            return str(res)
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)


#-----------------------------------------------------------------------
#!!!----------------------------MAIN---------------------------------!!!
#-----------------------------------------------------------------------


if __name__ == "__main__":

    remoteHosts = []
    regions = []
    arg = ""
    for x in range(1,len(sys.argv)):
        if sys.argv[x] == "-s":
            arg = "spadeHost"
        elif sys.argv[x] == "-r":
            arg = "restHost"
        elif sys.argv[x] == "-u":
            arg = "remoteHost"
        elif sys.argv[x] == "-rg":
            arg = "region"
        elif sys.argv[x] == "-zn":
            arg = "zone"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "restHost" and restHost == "":
                restHost = sys.argv[x]
            elif arg == "remoteHost":
                remoteHosts.append(sys.argv[x])
            elif arg == "region":
                regions.append(sys.argv[x].lower())
            elif arg == "zone" and zone == "":
                zone = sys.argv[x].lower()

    if spadeHost == "" or restHost == "" or len(remoteHosts) == 0 or len(regions) == 0 or zone == "":
        print "Require next arguments: -s Spade_host -r rest_host -zn zone -u [remote_hosts] -rg [regions]"
        sys.exit(0)
    if len(regions) != len(remoteHosts):
        print "The number of remote hosts and regions must be equal"
        sys.exit(0)

    for i in range(len(remoteHosts)):
        h = {}
        h["remoteHost"] = remoteHosts[i]
        h["region"] = regions[i]
        region_list.append(h)

    print "Spade host: " + spadeHost
    print "Rest host: " + restHost
    for i in region_list:
        print "Region: " + i["region"] + " -> " + i["remoteHost"] 

    for i in region_list:
        i["agent"] = regionRepr(i["region"]+"@"+spadeHost, "secret")
        i["aid"] = i["agent"].getAID().getName()
        i["agent"].addBehaviour(AMS(), None)

        aclt = spade.Behaviour.ACLTemplate()
        aclt.setPerformative("region")
        t = spade.Behaviour.MessageTemplate(aclt)
        i["agent"].addBehaviour(reprActions(), t)

        i["agent"].start()

    zn = zone("zone@"+spadeHost, "secret")
    zn.addBehaviour(AMS(), None)

    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("zone")
    t = spade.Behaviour.MessageTemplate(aclt)
    zn.addBehaviour(regionDonant(), t)

    zn.start()

    rest = RestAgent("rest@"+spadeHost, "secret")
    rest.start()
    rest.addBehaviour(RestBehaviour, None)

    aclt2 = spade.Behaviour.ACLTemplate()
    aclt2.setPerformative("complete")
    t2 = spade.Behaviour.MessageTemplate(aclt2)
    rest.addBehaviour(petitionCompleted(), t2)

    #execute Rest system
    r = restHost.split(":")
    app.run(host = r[0], port = r[1])

    for i in region_list:
        i["agent"].stop()

    zn.stop()
    rest.stop()

    sys.exit(0)

