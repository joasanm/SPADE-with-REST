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
znName = ""
countryHost = ""
hRanking = []

#region list representated as dictionaries with the name of region, host and representant agent
region_list = []

#time that can wait a client connection are defined in the timeout variable
timeout=20

#variable with the Rest system to use
app = Flask(__name__)


#-----------------------------------------------------------------------
#!!!------------------REGION REPRESENTANTS---------------------------!!!
#-----------------------------------------------------------------------


#agent that represents a region
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

#method to make external petitions
class restRequest(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        msg = self._receive(block=True)
        aid = msg.getSender().getName()
        rmh = ""
        isRegion = False
        for i in region_list:
            if i["aid"] == aid:
                rmh = i["remoteHost"]
                isRegion = True
        if rmh == "":
            rmh = countryHost
        content = msg.getContent().split("-")
        result = ""
        try:
            if content[0] == "getPL":
                r = requests.get("http://"+rmh+"/patients", data = content[2], timeout = 7)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getRC":
                r = requests.get("http://"+rmh+"/confirmation", data = content[2], timeout = 7)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getECP":
                r = requests.get("http://"+rmh+"/"+znName+"/0Emergency", data = content[2], timeout = 3)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getCP":
                r = requests.get("http://"+rmh+"/"+znName+"/country", data = content[2], timeout = 15)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getCC":
                r = requests.get("http://"+rmh+"/"+znName+"/country/confirmation", data = content[2], timeout = 3)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getECC":
                r = requests.get("http://"+rmh+"/"+znName+"/0Emergency/confirmation", data = content[2], timeout = 3)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "putT":
                r = requests.put("http://"+rmh+"/"+znName+"/hAgent", data = content[2], timeout = 3)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "postP":
                r = requests.post("http://"+rmh+"/"+znName+"/ecAgent", data = content[2], timeout = 3)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
        except requests.exceptions.RequestException:
            print self.myAgent.getAID().getName() + ": ERROR, connection refused"
            result = "404-" + content[1] + "-ERROR(zoneConnectionRefused)"
        except requests.exceptions.Timeout:
            print self.myAgent.getAID().getName() + ": ERROR, client timeOut reached"
            result = "408-" + content[1] + "-ERROR(zoneTimeOutReached)"
        msg2 = spade.ACLMessage.ACLMessage()
        if isRegion:
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid(aid, ["xmpp://"+aid]))
        else:
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
        msg2.setContent("requestInformation-" + content[0] + "-" + result)
        self.myAgent.send(msg2)

#variable with an instance of make petitions
rr = restRequest()

#method to create an instance of making petitions
def startRestRequest(sender):
    rr = restRequest()
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative(sender)
    t = spade.Behaviour.MessageTemplate(template)
    rest.addBehaviour(rr, t)
    print "restRequest Behaviour started"

#actions that can do a region representant agent
class reprActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "getECP":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getZP":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getCP":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getC":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getECC":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "putT":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "postP":
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getPatientsList":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent("getPL-"+content[1]+"-"+content[2])
            startRestRequest(aid)
        elif content[0] == "requestInformation":
            if content[1] == "getPL":
                msg2.setPerformative("response")
                msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
                msg2.setContent(content[2]+"-"+content[3]+"-"+content[4])
            elif content[1] == "getRC":
                msg2.setPerformative("zone")
                msg2.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
                msg2.setContent("regionConfirmation-"+content[2]+"-"+content[3]+"-"+content[4])                
        elif content[0] == "patientList":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2])
        elif content[0] == "RCRequest":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent("getRC-"+content[1]+"-"+content[2])
            startRestRequest(aid)
        self.myAgent.send(msg2)

#behaviour to register an agent in AMS
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
#!!!-----------------------ZONE COORDINATOR--------------------------!!!
#-----------------------------------------------------------------------


#agent that represents the zone coordinator
class zone(spade.Agent.Agent):
    def _setup(self):
        self.rec = 0
        self.rSender = ""
        self.zonePatients = {}
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("zoneCoordinator")
        sd.setOwnership("zone")
        sd.addProperty("description", "communication with other regions & national coordinator")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(self.getAID())
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behaviour to create a list of possibles receptors
class patientsList(spade.Behaviour.TimeOutBehaviour):
    def onStart(self):
        print "waiting regions"

    def timeOut(self):
        print "waiting ended"
        self.myAgent.zonePatients = {}
        patients = []
        pid = ""
        for x in range(self.myAgent.rec):
            msg = self._receive(False)
            if msg and msg.getContent.split("-")[0] == "200":
                rname = msg.getSender().getName()
                content = msg.getContent().split("-")
                pid = content[1]
                hpatients = json.loads(content[2])
                self.myAgent.zonePatients[rname] = hpatients
                patients += hpatients
        self.myAgent.rec = 0
        #ONT Protocol
        rkPatients = []
        for i in hRanking:
            hrPatients = []
            for j in patients:
                if j["hospital"] == i:
                    hrPatients.append(j)
            rkPatients += hrPatients
        if len(rkPatients) != len(patients):
            for i in patients:
                if i not in rkPatients:
                    rkPatients.append(i)
        msg2 = spade.ACLMessage.ACLMessage()
        if self.myAgent.rSender == "":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(pid + "-" + json.dumps(rkPatients))
        else:
            msg2.setPerformative("region")
            msg2.setContent("patientList-" + pid + "-" + json.dumps(rkPatients))
            msg2.addReceiver(spade.AID.aid(self.myAgent.rSender, ["xmpp://rest@"+self.myAgent.rSender]))
            self.myAgent.rSender = ""
        self.myAgent.send(msg2)

#variable with the instance of the previous behaviour
pl = patientsList(9)

#method to instance the previous behaviour
def startPatientsList():
    pl = patientsList(9)
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative("response")
    t = spade.Behaviour.MessageTemplate(template)
    zn.addBehaviour(pl, t)
    print "patientsList Behaviour started"

#rest of actions that can do a zone coordinator
class zoneActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "getZP":
            aid = msg.getSender().getName()
            self.myAgent.rSender = aid
            msg2.setPerformative("region")
            msg2.setContent("getPatientsList-" + content[1] + "-" + content[2])
            for i in region_list:
                if i["aid"] != aid:
                    msg2.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
                    self.myAgent.rec += 1
            startPatientsList()
        elif content[0] == "getECP":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(msg.getContent())
            startRestRequest(aid)
        elif content[0] == "getCP":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(msg.getContent())
            startRestRequest(aid)
        elif content[0] == "getC":
            cRegion = ""
            for i in self.myAgent.regionPatients.keys():
                print i
                print str(content[2])
                if json.loads(content[2]) in self.myAgent.zonePatients[i]:
                    cRegion = i
            if cRegion != "":
                msg2.setPerformative("region")
                msg2.addReceiver(spade.AID.aid(cRegion, ["xmpp://"+cRegion]))
                msg2.setContent("RCRequest-" + content[1] + "-" + content[2])
            else:
                aid = self.myAgent.getAID().getName()
                msg2.setPerformative(aid)
                msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
                msg2.setContent("getCC-" + content[1] + "-" + content[2])
                startRestRequest(aid)
        elif content[0] == "getECC":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(msg.getContent())
            startRestRequest(aid)
        elif content[0] == "putT":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(msg.getContent())
            startRestRequest(aid)
        elif content[0] == "postP":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(msg.getContent())
            startRestRequest(aid)
        elif content[0] == "getC2":
            cRegion = ""
            for i in region_list:
                if json.loads(content[2]) in self.myAgent.zonePatients[i["aid"]]:
                    cRegion = i["aid"]
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid(cRegion, ["xmpp://"+cRegion]))
            msg2.setContent("RCRequest-" + content[1] + "-" + content[2])
        elif content[0] == "getP":
            msg2.setPerformative("region")
            msg2.setContent("getPatientsList-" + content[1] + "-" + content[2])
            for i in region_list:
                msg2.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
                self.myAgent.rec += 1
            startPatientsList()
        elif content[0] == "regionConfirmation":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[2]+"-"+content[3])
        elif content[0] == "requestInformation":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[3]+"-"+content[4])
        self.myAgent.send(msg2)


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

#behaviour to complete requests
class petitionCompleted(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        try:
            print "comlpeting request"
            pid = int(content[0])
            self.myAgent.petitions[pid][2] = content[1]
            self.myAgent.petitions[pid][0] = 2
        except:
            print self.getAID().getName() + ": petition not registered"

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
                    elif self.myAgent.petitions[k][1]=="GET_EC":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getECP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Zone":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getZP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Country":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getCP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Confirmation":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getC-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_ECConfirmation":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getECC-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="PUT_Transplant":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("putT-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="POST_Patient":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("postP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Confirmation2":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
                        msg.setContent("getC2-" + str(k) + "-" + self.myAgent.petitions[k][3])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Patients":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid("zone@"+spadeHost, ["xmpp://zone@"+spadeHost]))
                        msg.setContent("getP-" + str(k) + "-" + self.myAgent.petitions[k][3])
                        self.myAgent.send(msg)

#variable to intance the previous behaviour
RestBehaviour = RestBehav()

#method to create an instance of the previous behaviour
def startRestBehaviour():
    RestBehaviour = RestBehav()
    rest.addBehaviour(RestBehaviour, None)
    print "Rest Behaviour started"

#method to delete an instance of the previous behaviour
def stopRestBehaviour():
    rest.removeBehaviour(RestBehaviour)
    print "Rest Behaviour stopped"

#method to validate data tha receive REST server
def dataValidation(model, data):
    c = json.loads(data).keys()
    conf = 1
    if model == 0:
        if "organ_type" not in c:
            conf = 0
    else:
        if "id" not in c or "organ_type" not in c or "critical_state" not in c or "hospital" not in c or "transplant_authorization" not in c:
            conf = 0
    return conf

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
-GET <region>/<level> -> return receptor list from emergency coordinator, other regions and other zones
-GET <region>/zone/confimration -> return confirmation of an hospital from other region
-GET <region>/0Emergency/confirmation -> return confirmation of an hospital that have the receptor in emergency coordinator
-GET /confirmation -> return confirmation of an hospital from the zone
-GET /patients -> return receptors list of the diferents hospitals from the zone
-PUT /<region>/hAgent -> update historical agent information
-POST /<region>/ecAgent -> add new patient in critical receptors list
-OPTIONS / -> return list of possible requests from the platform
"""

#GET request route, linked to funcion consult
#Call Rest agent to get receptor list from diferents coordination levels
#Requires organ data input
#request form: [request state, request used, empty string for information to send, organ data]
@app.route('/<string:region>/<string:level>', methods=['GET'])
def getPatients(region, level):
    a = ""
    plv = ""
    for i in region_list:
        if i["region"] == region:
            a = i["aid"]
    if level == "0Emergency":
        plv = "GET_EC"
    elif level == "zone":
        plv = "GET_Zone"
    elif level == "country":
        plv = "GET_Country"
    if a =="" or plv == "" or dataValidation(0, request.data) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, plv, "", a, request.data]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][2]
            del rest.petitions[idp]
            return str(res)
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)

#GET request route, linked to funcion consult
#Call Rest agent to get confirmation of an hospital
#Requires receptor data input
#request form: [request state, request used, empty string for information to send, receptor data]
@app.route('/<string:region>/zone/confirmation', methods=['GET'])
def getConfirmation(region):
    a = ""
    for i in region_list:
        if i["region"] == region:
            a = i["aid"]
    if a =="" or dataValidation(1, request.data) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, "GET_Confirmation", "", a, request.data]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][2]
            del rest.petitions[idp]
            return str(res)
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)

#GET request route, linked to funcion consult
#Call Rest agent to get confirmation of an hospital with the receptor in critical state
#Requires receptor data input
#request form: [request state, request used, empty string for information to send, receptor data]
@app.route('/<string:region>/0Emergency/confirmation', methods=['GET'])
def getECConfirmation(region):
    a = ""
    for i in region_list:
        if i["region"] == region:
            a = i["aid"]
    if a =="" or dataValidation(1, request.data) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, "GET_ECConfirmation", "", a, request.data]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][2]
            del rest.petitions[idp]
            return str(res)
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)

#GET request route, linked to funcion consult
#Call Rest agent to get confirmation of an hospital from the zone
#Requires receptor data input
#request form: [request state, request used, empty string for information to send, receptor data]
@app.route('/confirmation', methods=['GET'])
def getConfirmation2():
    if dataValidation(1, request.data) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, "GET_Confirmation2", "", request.data]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][2]
            del rest.petitions[idp]
            return str(res)
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)

#GET request route, linked to funcion consult
#Call Rest agent to get receptor list of diferents hospitals from the zone
#Requires organ data input
#request form: [request state, request used, empty string for information to send, organ data]
@app.route('/patients', methods=['GET'])
def getPatients2():
    if dataValidation(0, request.data) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, "GET_Patients", "", request.data]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][2]
            del rest.petitions[idp]
            return str(res)
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)

#PUT request route, linked to funcion consult
#Call Rest agent to update historical agent information
#Requires transplant data input
#request form: [request state, request used, empty string for information to send, transplant data]
@app.route('/<string:region>/hAgent', methods=['PUT'])
def putTransplant(region):
    a = ""
    for i in region_list:
        if i["region"] == region:
            a = i["aid"]
    if a =="" or dataValidation(1, request.data) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, "PUT_Transplant", "", a, request.data]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][2]
            del rest.petitions[idp]
            return str(res)
        else:
            stopRestBehaviour()
            del rest.petitions[idp]
            startRestBehaviour()
            abort(500)

#POST request route, linked to funcion consult
#Call Rest agent to add new critical receptor to emergency coordinator list
#Requires patient data input
#request form: [request state, request used, empty string for information to send, patient data]
@app.route('/<string:region>/ecAgent', methods=['POST'])
def postPatient(region):
    a = ""
    for i in region_list:
        if i["region"] == region:
            a = i["aid"]
    if a =="" or dataValidation(1, request.data) == 0:
        abort(400)
    else:
        idp=rest.id
        rest.id+=1
        rest.petitions[idp]=[0, "POST_Patient", "", a, request.data]
        endtime=time.time()+timeout
        remaining=endtime-time.time()
        while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
        if rest.petitions[idp][0]==2:
            res=rest.petitions[idp][2]
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
        elif sys.argv[x] == "-h":
            arg = "region"
        elif sys.argv[x] == "-zn":
            arg = "zone"
        elif sys.argv[x] == "-zh":
            arg = "countryHost"
        elif sys.argv[x] == "-hr":
            arg = "hospitalRanking"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "restHost" and restHost == "":
                restHost = sys.argv[x]
            elif arg == "countryHost" and countryHost == "":
                countryHost = sys.argv[x]
            elif arg == "remoteHost":
                remoteHosts.append(sys.argv[x])
            elif arg == "region":
                regions.append(sys.argv[x].lower())
            elif arg == "zone" and znName == "":
                znName = sys.argv[x].lower()
            elif arg == "hospitalRanking":
                hRanking.append(sys.argv[x].lower())

    remoteHosts = list(set(remoteHosts))
    regions = list(set(regions))

    if spadeHost == "" or restHost == "" or znName == "" or countryHost == "" or len(remoteHosts) == 0 or len(regions) == 0 or len(hRanking) == 0:
        print "Require next arguments: -zn zone -s Spade_host -r rest_host -zh zone_host -h [regions] -u [remote_hosts] -hr [hospital_rankings]"
        sys.exit(0)
    if len(regions) != len(remoteHosts):
        print "The number of remote hosts & regions must be equal"
        sys.exit(0)

    for i in range(len(remoteHosts)):
        h = {}
        h["remoteHost"] = remoteHosts[i]
        h["region"] = regions[i]
        region_list.append(h)

    print "Spade host: " + spadeHost
    print "Zone host: " + znName + " -> " + restHost
    print "Regions:"
    for i in region_list:
        print i["region"] + " -> " + i["remoteHost"]
    print "Hospital Ranking:"
    n = 1
    for i in hRanking:
        print n + " : " + i

    #create region representant agents
    for i in region_list:
        i["agent"] = regionRepr(i["region"]+"@"+spadeHost, "secret")
        i["aid"] = i["agent"].getAID().getName()
        i["agent"].addBehaviour(AMS(), None)

        aclt = spade.Behaviour.ACLTemplate()
        aclt.setPerformative("region")
        t = spade.Behaviour.MessageTemplate(aclt)
        i["agent"].addBehaviour(reprActions(), t)

        i["agent"].start()

    #create zone agent
    zn = zone("zone@"+spadeHost, "secret")
    zn.addBehaviour(AMS(), None)

    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("zone")
    t = spade.Behaviour.MessageTemplate(aclt)
    zn.addBehaviour(zoneActions(), t)

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

