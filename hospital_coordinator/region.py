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
rgName = ""
zoneHost = ""

#hospital list representated as dictionaries with the name of hospital, host and representant agent
hospital_list = []

#time that can wait a client connection are defined in the timeout variable
timeout=10

#variable with the Rest system to use
app = Flask(__name__)


#-----------------------------------------------------------------------
#!!!----------------HOSPITAL REPRESENTANTS---------------------------!!!
#-----------------------------------------------------------------------


#agent that represents an hospital
class hospitalRepr(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("hospitalRepresentant")
        sd.setOwnership("region")
        sd.addProperty("description", "hospital representant")
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
        isHospital = False
        for i in hospital_list:
            if i["aid"] == aid:
                rmh = i["remoteHost"]
                isHospital = True
        if rmh == "":
            rmh = zoneHost
        content = msg.getContent().split("-")
        result = ""
        try:
            if content[0] == "getPL":
                r = requests.get("http://"+rmh+"/patients", data = content[2], timeout = 5)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getHC":
                r = requests.get("http://"+rmh+"/confirmation", data = content[2], timeout = 5)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getECP":
                r = requests.get("http://"+rmh+"/"+rgName+"/0Emergency", data = content[2], timeout = 6)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getZP":
                r = requests.get("http://"+rmh+"/"+rgName+"/zone", data = content[2], timeout = 10)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getCP":
                r = requests.get("http://"+rmh+"/"+rgName+"/country", data = content[2], timeout = 18)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getZC":
                r = requests.get("http://"+rmh+"/"+rgName+"/zone/confirmation", data = content[2], timeout = 9)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getECC":
                r = requests.get("http://"+rmh+"/"+rgName+"/0Emergency/confirmation", data = content[2], timeout = 6)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "putT":
                r = requests.put("http://"+rmh+"/"+rgName+"/hAgent", data = content[2], timeout = 6)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "postP":
                r = requests.post("http://"+rmh+"/"+rgName+"/ecAgent", data = content[2], timeout = 6)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
        except requests.exceptions.RequestException:
            print self.myAgent.getAID().getName() + ": ERROR, connection refused"
            result = "404-" + content[1] + "-ERROR(regionConnectionRefused)"
        except requests.exceptions.Timeout:
            print self.myAgent.getAID().getName() + ": ERROR, client timeOut reached"
            result = "408-" + content[1] + "-ERROR(regionTimeOutReached)"
        msg2 = spade.ACLMessage.ACLMessage()
        if isHospital:
            msg2.setPerformative("hospital")
            msg2.addReceiver(spade.AID.aid(aid, ["xmpp://"+aid]))
        else:
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
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

#actions that can do an hospital representant agent
class reprActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "getRP":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getECP":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getZP":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getCP":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getC":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getECC":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "putT":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "postP":
            msg2.setPerformative("region")
            msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
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
                msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
                msg2.setContent(content[2]+"-"+content[3]+"-"+content[4])
            elif content[1] == "getHC":
                msg2.setPerformative("region")
                msg2.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
                msg2.setContent("hospitalConfirmation-"+content[2]+"-"+content[3]+"-"+content[4])                
        elif content[0] == "patientList":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2])
        elif content[0] == "HCRequest":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent("getHC-"+content[1]+"-"+content[2])
            startRestRequest(aid)
        self.myAgent.send(msg2)

#behaviour to register an agent in AMS
class AMS(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        a = self.myAgent.getAID()
        aad = spade.AMS.AmsAgentDescription()
        aad.setAID(a)
        aad.setOwnership = "region"
        result = self.myAgent.modifyAgent(aad)
        if not result:
            print a.getName() + ": WARNING, AMS not updated"


#-----------------------------------------------------------------------
#!!!---------------------REGION COORDINATOR--------------------------!!!
#-----------------------------------------------------------------------


#agent that represents the region coordinator
class region(spade.Agent.Agent):
    def _setup(self):
        self.rec = 0
        self.hSender = ""
        self.regionPatients = {}
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("regionCoordinator")
        sd.setOwnership("region")
        sd.addProperty("description", "communication with other hospitals & zone")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(self.getAID())
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behaviour to create a list of possibles receptors
class patientsList(spade.Behaviour.TimeOutBehaviour):
    def onStart(self):
        print "waiting hospitals"

    def timeOut(self):
        print "waiting ended"
        self.myAgent.regionPatients = {}
        patients = []
        pid = ""
        for x in range(self.myAgent.rec):
            msg = self._receive(False)
            if msg and msg.getContent().split("-")[0] == "200":
                hname = msg.getSender().getName()
                content = msg.getContent().split("-")
                pid = content[1]
                hpatients = json.loads(content[2])
                self.myAgent.regionPatients[hname] = hpatients
                patients += hpatients
        self.myAgent.rec = 0
        msg2 = spade.ACLMessage.ACLMessage()
        if self.myAgent.hSender == "":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(pid + "-" + json.dumps(patients))
        else:
            msg2.setPerformative("hospital")
            msg2.setContent("patientList-" + pid + "-" + json.dumps(patients))
            msg2.addReceiver(spade.AID.aid(self.myAgent.hSender, ["xmpp://"+self.myAgent.hSender]))
            self.myAgent.hSender = ""
        self.myAgent.send(msg2)
        print "ENVIO"

#variable with the instance of the previous behaviour
pl = patientsList(4)

#method to instance the previous behaviour
def startPatientsList():
    pl = patientsList(4)
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative("response")
    t = spade.Behaviour.MessageTemplate(template)
    rg.addBehaviour(pl, t)
    print "patientsList Behaviour started"

#rest of actions that can do a region coordinator
class regionActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "getRP":
            aid = msg.getSender().getName()
            self.myAgent.hSender = aid
            msg2.setPerformative("hospital")
            msg2.setContent("getPatientsList-" + content[1] + "-" + content[2])
            city = ""
            for i in hospital_list:
                if i["aid"] == aid:
                    city = i["city"]
            for i in hospital_list:
                if i["aid"] != aid and i["city"] != city:
                    msg2.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
                    self.myAgent.rec += 1
            startPatientsList()
        elif content[0] == "getECP":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(msg.getContent())
            startRestRequest(aid)
        elif content[0] == "getZP":
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
            cHospital = ""
            print self.myAgent.regionPatients
            for i in self.myAgent.regionPatients.keys():
                print i
                print str(content[2])
                if json.loads(content[2]) in self.myAgent.regionPatients[i]:
                    cHospital = i
            print cHospital
            if cHospital != "":
                msg2.setPerformative("hospital")
                msg2.addReceiver(spade.AID.aid(cHospital, ["xmpp://"+cHospital]))
                msg2.setContent("HCRequest-" + content[1] + "-" + content[2])
            else:
                aid = self.myAgent.getAID().getName()
                msg2.setPerformative(aid)
                msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
                msg2.setContent("getZC-" + content[1] + "-" + content[2])
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
            cHospital = ""
            for i in hospital_list:
                if json.loads(content[2]) in self.myAgent.regionPatients[i["aid"]]:
                    cHospital = i["aid"]
            msg2.setPerformative("hospital")
            msg2.addReceiver(spade.AID.aid(cHospital, ["xmpp://"+cHospital]))
            msg2.setContent("HCRequest-" + content[1] + "-" + content[2])
        elif content[0] == "getP":
            msg2.setPerformative("hospital")
            msg2.setContent("getPatientsList-" + content[1] + "-" + content[2])
            for i in hospital_list:
                msg2.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
                self.myAgent.rec += 1
            startPatientsList()
        elif content[0] == "hospitalConfirmation":
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
        content = msg.getContent().split("-")
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
                    elif self.myAgent.petitions[k][1]=="GET_Region":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getRP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_EC":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getECP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Zone":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getZP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Country":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getCP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Confirmation":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getC-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_ECConfirmation":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getECC-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="PUT_Transplant":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("putT-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="POST_Patient":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("hospital")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("postP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Confirmation2":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
                        msg.setContent("getC2-" + str(k) + "-" + self.myAgent.petitions[k][3])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Patients":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("region")
                        msg.addReceiver(spade.AID.aid("region@"+spadeHost, ["xmpp://region@"+spadeHost]))
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
-GET <hospital>/<level> -> return receptor list from emergency coordinator, region, other regions and other zones
-GET <hospital>/region/confimration -> return confirmation of an hospital from other city
-GET <hospital>/0Emergency/confirmation -> return confirmation of an hospital that have the receptor in emergency coordinator
-GET /confirmation -> return confirmation of an hospital from the region
-GET /patients -> return receptors list of the diferents hospitals from the region
-PUT /<hospital>/hAgent -> update historical agent information
-POST /<hospital>/ecAgent -> add new patient in critical receptors list
-OPTIONS / -> return list of possible requests from the platform
"""

#GET request route, linked to funcion consult
#Call Rest agent to get receptor list from diferents coordination levels
#Requires organ data input
#request form: [request state, request used, empty string for information to send, organ data]
@app.route('/<string:hospital>/<string:level>', methods=['GET'])
def getPatients(hospital, level):
    a = ""
    plv = ""
    for i in hospital_list:
        if i["hospital"] == hospital:
            a = i["aid"]
    if level == "region":
        plv = "GET_Region"
    elif level == "0Emergency":
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
@app.route('/<string:hospital>/region/confirmation', methods=['GET'])
def getConfirmation(hospital):
    a = ""
    for i in hospital_list:
        if i["hospital"] == hospital:
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
@app.route('/<string:hospital>/0Emergency/confirmation', methods=['GET'])
def getECConfirmation(hospital):
    a = ""
    for i in hospital_list:
        if i["hospital"] == hospital:
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
#Call Rest agent to get confirmation of an hospital from the region
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
#Call Rest agent to get receptor list of diferents hospitals from the region
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
@app.route('/<string:hospital>/hAgent', methods=['PUT'])
def putTransplant(hospital):
    a = ""
    for i in hospital_list:
        if i["hospital"] == hospital:
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
@app.route('/<string:hospital>/ecAgent', methods=['POST'])
def postPatient(hospital):
    a = ""
    for i in hospital_list:
        if i["hospital"] == hospital:
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
    hospitals = []
    cities = []
    arg = ""
    for x in range(1,len(sys.argv)):
        if sys.argv[x] == "-s":
            arg = "spadeHost"
        elif sys.argv[x] == "-r":
            arg = "restHost"
        elif sys.argv[x] == "-u":
            arg = "remoteHost"
        elif sys.argv[x] == "-h":
            arg = "hospital"
        elif sys.argv[x] == "-rg":
            arg = "region"
        elif sys.argv[x] == "-c":
            arg = "city"
        elif sys.argv[x] == "-zh":
            arg = "zoneHost"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "restHost" and restHost == "":
                restHost = sys.argv[x]
            elif arg == "zoneHost" and zoneHost == "":
                zoneHost = sys.argv[x]
            elif arg == "remoteHost":
                remoteHosts.append(sys.argv[x])
            elif arg == "hospital":
                hospitals.append(sys.argv[x].lower())
            elif arg == "region" and rgName == "":
                rgName = sys.argv[x].lower()
            elif arg == "city":
                cities.append(sys.argv[x].lower())

    remoteHosts = list(set(remoteHosts))
    hospitals = list(set(hospitals))

    if spadeHost == "" or restHost == "" or rgName == "" or zoneHost == "" or len(remoteHosts) == 0 or len(hospitals) == 0 or len(cities) == 0:
        print "Require next arguments: -rg region -s Spade_host -r rest_host -zh zone_host -h [hospitals] -u [remote_hosts] -c [cities]"
        sys.exit(0)
    if len(hospitals) != len(remoteHosts) or len(cities) != len(hospitals):
        print "The number of remote hosts, hospitals and cities must be equal"
        sys.exit(0)

    for i in range(len(remoteHosts)):
        h = {}
        h["remoteHost"] = remoteHosts[i]
        h["hospital"] = hospitals[i]
        h["city"] = cities[i]
        hospital_list.append(h)

    print "Spade host: " + spadeHost
    print "Region host: " + rgName + " -> " + restHost
    for i in hospital_list:
        print "Hospital de "+i["city"]+": " + i["hospital"] + " -> " + i["remoteHost"]

    #create hospital representant agents
    for i in hospital_list:
        i["agent"] = hospitalRepr(i["hospital"]+"@"+spadeHost, "secret")
        i["aid"] = i["agent"].getAID().getName()
        i["agent"].addBehaviour(AMS(), None)

        aclt = spade.Behaviour.ACLTemplate()
        aclt.setPerformative("hospital")
        t = spade.Behaviour.MessageTemplate(aclt)
        i["agent"].addBehaviour(reprActions(), t)

        i["agent"].start()

    #create region agent
    rg = region("region@"+spadeHost, "secret")
    rg.addBehaviour(AMS(), None)

    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("region")
    t = spade.Behaviour.MessageTemplate(aclt)
    rg.addBehaviour(regionActions(), t)

    rg.start()

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

    for i in hospital_list:
        i["agent"].stop()

    rg.stop()
    rest.stop()

    sys.exit(0)

