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
zRanking = []

#zone list representated as dictionaries with the name of zone, host and representant agent
zone_list = []

#time that can wait a client connection are defined in the timeout variable
timeout=40

#variable with the Rest system to use
app = Flask(__name__)


#-----------------------------------------------------------------------
#!!!--------------------ZONE REPRESENTANTS---------------------------!!!
#-----------------------------------------------------------------------


#agent that represents a zone
class zoneRepr(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("zoneRepresentant")
        sd.setOwnership("national")
        sd.addProperty("description", "zone representant")
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
        content = msg.getContent().split("-")
        rmh = ""
        for i in zone_list:
            if i["aid"] == aid:
                rmh = i["remoteHost"]
        if rmh == "":
            rmh = content[3]
        result = ""
        try:
            if content[0] == "getPL":
                r = requests.get("http://"+rmh+"/patients", data = content[2], timeout = 11)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
            elif content[0] == "getZC" or content[0] == "getECC":
                r = requests.get("http://"+rmh+"/confirmation", data = content[2], timeout = 11)
                result = str(r.status_code) + "-" + content[1] + "-" + r.text
        except requests.exceptions.RequestException:
            print self.myAgent.getAID().getName() + ": ERROR, connection refused"
            result = "404-" + content[1] + "-ERROR(nationalConnectionRefused)"
        except requests.exceptions.Timeout:
            print self.myAgent.getAID().getName() + ": ERROR, client timeOut reached"
            result = "408-" + content[1] + "-ERROR(nationalTimeOutReached)"
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.addReceiver(spade.AID.aid(aid, ["xmpp://"+aid]))
        if content[0] == "getECC":
            msg2.setPerformative("emergencyCoordinator")
            msg2.setContent("requestInformation-" + result)
        else:
            msg2.setPerformative("zone")
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
            msg2.setPerformative("emergencyCoordinator")
            msg2.addReceiver(spade.AID.aid("emergency@"+spadeHost, ["xmpp://emergency@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getCP":
            msg2.setPerformative("national")
            msg2.addReceiver(spade.AID.aid("national@"+spadeHost, ["xmpp://national@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getC":
            msg2.setPerformative("national")
            msg2.addReceiver(spade.AID.aid("national@"+spadeHost, ["xmpp://national@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "getECC":
            msg2.setPerformative("emergencyCoordinator")
            msg2.addReceiver(spade.AID.aid("emergency@"+spadeHost, ["xmpp://emergency@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "putT":
            msg2.setPerformative("historicalAgent")
            msg2.addReceiver(spade.AID.aid("historical@"+spadeHost, ["xmpp://historical@"+spadeHost]))
            msg2.setContent(msg.getContent())
        elif content[0] == "postP":
            msg2.setPerformative("emergencyCoordinator")
            msg2.addReceiver(spade.AID.aid("emergency@"+spadeHost, ["xmpp://emergency@"+spadeHost]))
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
                msg2.addReceiver(spade.AID.aid("national@"+spadeHost, ["xmpp://national@"+spadeHost]))
                msg2.setContent(content[2]+"-"+content[3]+"-"+content[4])
            elif content[1] == "getZC":
                msg2.setPerformative("national")
                msg2.addReceiver(spade.AID.aid("national@"+spadeHost, ["xmpp://national@"+spadeHost]))
                msg2.setContent("zoneConfirmation-"+content[2]+"-"+content[3]+"-"+content[4])                
        elif content[0] == "patientList":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2])
        elif content[0] == "ZCRequest":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent("getZC-"+content[1]+"-"+content[2])
            startRestRequest(aid)
        self.myAgent.send(msg2)

#behaviour to register an agent in AMS
class AMS(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        a = self.myAgent.getAID()
        aad = spade.AMS.AmsAgentDescription()
        aad.setAID(a)
        aad.setOwnership = "national"
        result = self.myAgent.modifyAgent(aad)
        if not result:
            print a.getName() + ": WARNING, AMS not updated"


#-----------------------------------------------------------------------
#!!!---------------EMERGENCY COORDINATOR AGENT-----------------------!!!
#-----------------------------------------------------------------------


#agent that contain the critical receptors list
class ecAgent(spade.Agent.Agent):
    def _setup(self):
        self.ecDB = []
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("emergencyCoordinator")
        sd.setOwnership("national")
        sd.addProperty("description", "coordinator for critical receptors")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(self.getAID())
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#actions that can do emergency coordinator agent
class ecaActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        aid = msg.getSender().getName()
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "getECP":
            organ = json.loads(content[2])
            receptors = []
            for i in self.myAgent.ecDB:
                if i[1]["organ_type"] == organ["organ_type"]:
                    receptors.append(i[1])
            res = json.dumps(receptors)
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid(aid, ["xmpp://"+aid]))
            msg2.setContent("patientList-" + content[1] + "-" + res)
        elif content[0] == "getECC":
            patient = json.loads(content[2])
            host = ""
            for i in self.myAgent.ecDB:
                if i[1] == patient:
                    host = i[0]
            msg2.setPerformative(self.myAgent.getAID().getName())
            msg2.setContent(msg.getContent + "-" + host)
            startRestRequest(self.myAgent.getAID().getName())
        elif content[0] == "postP":
            patient = content[2].split("//")
            self.myAgent.ecDB.append([patient[0], json.loads(patient[1])])
            msg2.setPerformative("zone")
            msg2.setContent("patientList-" + content[1] + "-POST realized")
        elif content[0] == "requestInformation":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[2]+"-"+content[3])
        self.myAgent.send(msg2)


#-----------------------------------------------------------------------
#!!!---------------------HISTORICAL AGENT----------------------------!!!
#-----------------------------------------------------------------------


#agent that contain information about transplants realized on the country
class hAgent(spade.Agent.Agent):
    def _setup(self):
        self.hDB = []
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("historicalAgent")
        sd.setOwnership("national")
        sd.addProperty("description", "realize stadistics from transplants")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(self.getAID())
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#actions that can do historical agent
class haActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        self.myAgent.hDB.append(content[2])
        aid = msg.getSender().getName()
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("complete")
        msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
        msg2.setContent(content[1] + "-PUT realized")
        self.myAgent.send(msg2)


#-----------------------------------------------------------------------
#!!!---------------------NATIONAL COORDINATOR------------------------!!!
#-----------------------------------------------------------------------


#agent that represents the national coordinator
class national(spade.Agent.Agent):
    def _setup(self):
        self.rec = 0
        self.zSender = ""
        self.nationalPatients = {}
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(self.getAID())
        sd.setType("nationalCoordinator")
        sd.setOwnership("national")
        sd.addProperty("description", "communication with zones")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(self.getAID())
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behaviour to create a list of possibles receptors
class patientsList(spade.Behaviour.TimeOutBehaviour):
    def onStart(self):
        print "waiting zones"

    def timeOut(self):
        print "waiting ended"
        self.myAgent.nationalPatients = {}
        patients = []
        pid = ""
        for x in range(self.myAgent.rec):
            msg = self._receive(False)
            if msg and msg.getContent.split("-")[0] == "200":
                zname = msg.getSender().getName()
                content = msg.getContent().split("-")
                pid = content[1]
                zpatients = json.loads(content[2])
                self.myAgent.nationalPatients[zname] = zpatients
                patients += zpatients
        self.myAgent.rec = 0
        #ONT Protocol
        zPatients = []
        for i in zRanking:
            hzPatients = []
            for j in zone_list:
                if j["zone"] == i:
                    zPatients += self.myAgent.nationalPatients[j["aid"]]
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("zone")
        msg2.setContent("patientList-" + pid + "-" + json.dumps(zPatients))
        msg2.addReceiver(spade.AID.aid(self.myAgent.zSender, ["xmpp://rest@"+self.myAgent.zSender]))
        self.myAgent.zSender = ""
        self.myAgent.send(msg2)

#variable with the instance of the previous behaviour
pl = patientsList(12)

#method to instance the previous behaviour
def startPatientsList():
    pl = patientsList(12)
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative("response")
    t = spade.Behaviour.MessageTemplate(template)
    nc.addBehaviour(pl, t)
    print "patientsList Behaviour started"

#rest of actions that can do a national coordinator
class nationalActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "getCP":
            aid = msg.getSender().getName()
            self.myAgent.zSender = aid
            msg2.setPerformative("zone")
            msg2.setContent("getPatientsList-" + content[1] + "-" + content[2])
            for i in zone_list:
                if i["aid"] != aid:
                    msg2.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
                    self.myAgent.rec += 1
            startPatientsList()
        elif content[0] == "getC":
            cZone = ""
            for i in self.myAgent.zonePatients.keys():
                print i
                print str(content[2])
                if json.loads(content[2]) in self.myAgent.nationalPatients[i]:
                    cZone = i
            msg2.setPerformative("zone")
            msg2.addReceiver(spade.AID.aid(cZone, ["xmpp://"+cZone]))
            msg2.setContent("ZCRequest-" + content[1] + "-" + content[2])
        elif content[0] == "zoneConfirmation":
            msg2.setPerformative("complete")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[2]+"-"+content[3])
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
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getECP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Country":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getCP-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_Confirmation":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getC-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_ECConfirmation":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("getECC-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="PUT_Transplant":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("putT-" + str(k) + "-" + self.myAgent.petitions[k][4])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="POST_Patient":
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("zone")
                        msg.addReceiver(spade.AID.aid(self.myAgent.petitions[k][3], ["xmpp://"+self.myAgent.petitions[k][3]]))
                        msg.setContent("postP-" + str(k) + "-" + self.myAgent.petitions[k][4])
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
-GET <zone>/<level> -> return receptor list from emergency coordinator and other zones
-GET <zone>/country/confimration -> return confirmation of an hospital from diferent zone
-GET <zone>/0Emergency/confirmation -> return confirmation of an hospital that have the receptor in emergency coordinator
-PUT /<zone>/hAgent -> update historical agent information
-POST /<zone>/ecAgent -> add new patient in critical receptors list
-OPTIONS / -> return list of possible requests from the platform
"""

#GET request route, linked to funcion consult
#Call Rest agent to get receptor list from diferents coordination levels
#Requires organ data input
#request form: [request state, request used, empty string for information to send, organ data]
@app.route('/<string:zone>/<string:level>', methods=['GET'])
def getPatients(zone, level):
    a = ""
    plv = ""
    for i in zone_list:
        if i["zone"] == zone:
            a = i["aid"]
    if level == "0Emergency":
        plv = "GET_EC"
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
@app.route('/<string:zone>/country/confirmation', methods=['GET'])
def getConfirmation(zone):
    a = ""
    for i in zone_list:
        if i["zone"] == zone:
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
@app.route('/<string:zone>/0Emergency/confirmation', methods=['GET'])
def getECConfirmation(zone):
    a = ""
    for i in zone_list:
        if i["zone"] == zone:
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

#PUT request route, linked to funcion consult
#Call Rest agent to update historical agent information
#Requires transplant data input
#request form: [request state, request used, empty string for information to send, transplant data]
@app.route('/<string:zone>/hAgent', methods=['PUT'])
def putTransplant(zone):
    a = ""
    for i in zone_list:
        if i["zone"] == zone:
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
@app.route('/<string:zone>/ecAgent', methods=['POST'])
def postPatient(zone):
    a = ""
    for i in zone_list:
        if i["zone"] == zone:
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
    zones = []
    arg = ""
    for x in range(1,len(sys.argv)):
        if sys.argv[x] == "-s":
            arg = "spadeHost"
        elif sys.argv[x] == "-r":
            arg = "restHost"
        elif sys.argv[x] == "-u":
            arg = "remoteHost"
        elif sys.argv[x] == "-z":
            arg = "zone"
        elif sys.argv[x] == "-hr":
            arg = "zoneRanking"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "restHost" and restHost == "":
                restHost = sys.argv[x]
            elif arg == "remoteHost":
                remoteHosts.append(sys.argv[x])
            elif arg == "zone":
                zones.append(sys.argv[x].lower())
            elif arg == "zoneRanking":
                zRanking.append(sys.argv[x].lower())

    remoteHosts = list(set(remoteHosts))
    zones = list(set(zones))
    zRanking = list(set(zRanking))

    if spadeHost == "" or restHost == "" or len(remoteHosts) == 0 or len(zones) == 0 or len(zRanking) == 0:
        print "Require next arguments: -s Spade_host -r rest_host -z [zones] -u [remote_hosts] -hr [zone_rankings]"
        sys.exit(0)
    if len(zones) != len(remoteHosts) or len(zones) != len(zRanking):
        print "The number of remote hosts, zones & ranking from each zone must be equal"
        sys.exit(0)
    for i in zRanking:
        if i not in zones:
            print "The name of ranked zones must exist in zone list"
            sys.exit(0)

    for i in range(len(remoteHosts)):
        h = {}
        h["remoteHost"] = remoteHosts[i]
        h["zone"] = zones[i]
        zone_list.append(h)

    print "Spade host: " + spadeHost
    print "zones:"
    for i in zone_list:
        print i["zone"] + " -> " + i["remoteHost"]
    print "Hospital Ranking:"
    n = 1
    for i in zRanking:
        print str(n) + " : " + i
        n += 1

    #create zone representant agents
    for i in zone_list:
        i["agent"] = zoneRepr(i["zone"]+"@"+spadeHost, "secret")
        i["aid"] = i["agent"].getAID().getName()
        i["agent"].addBehaviour(AMS(), None)

        aclt = spade.Behaviour.ACLTemplate()
        aclt.setPerformative("zone")
        t = spade.Behaviour.MessageTemplate(aclt)
        i["agent"].addBehaviour(reprActions(), t)

        i["agent"].start()

    #create national coordinator agent
    nc = national("national@"+spadeHost, "secret")
    nc.addBehaviour(AMS(), None)

    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("national")
    t = spade.Behaviour.MessageTemplate(aclt)
    nc.addBehaviour(nationalActions(), t)

    #create emergency coordinator agent
    eca = ecAgent("emergency@"+spadeHost, "secret")
    eca.addBehaviour(AMS(), None)

    aclt3 = spade.Behaviour.ACLTemplate()
    aclt3.setPerformative("emergencyCoordinator")
    t3 = spade.Behaviour.MessageTemplate(aclt3)
    nc.addBehaviour(ecaActions(), t3)

    #create historical agent
    ha = hAgent("historical@"+spadeHost, "secret")
    ha.addBehaviour(AMS(), None)

    aclt4 = spade.Behaviour.ACLTemplate()
    aclt4.setPerformative("historicalAgent")
    t4 = spade.Behaviour.MessageTemplate(aclt4)
    nc.addBehaviour(haActions(), t4)

    eca.start()
    ha.start()
    nc.start()

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

    for i in zone_list:
        i["agent"].stop()

    nc.stop()
    eca.stop()
    ha.stop()
    rest.stop()

    sys.exit(0)

