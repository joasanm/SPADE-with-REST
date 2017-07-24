#!flask/bin/python
from flask import Flask, abort, request
import spade
import sys
import time
import random
import json
import requests

#-----------------------------------------------------------------------
#!!!-----------------GLOBAL VARIABLES--------------------------------!!!
#-----------------------------------------------------------------------


restHost = ""
spadeHost = ""
remoteHost = ""
hospital = ""
cityHospitals = []

#time that can wait a client connection are defined in the timeout variable
timeout=5

#variable with the Rest system to use
app = Flask(__name__)


#-----------------------------------------------------------------------
#!!!----------------------WRAPPER AGENT------------------------------!!!
#-----------------------------------------------------------------------


#agent that control hospital database
class wrapper(spade.Agent.Agent):
    def _setup(self):
        self.patientsDB = []
        self.organs = ["heart", "pancreas", "liver", "kidney", "lung"]
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName("wrapper")
        sd.setType("wrapper")
        sd.setOwnership("hospital")
        sd.addProperty("description", "database wrapper")
        sd.addLanguage("patient description")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#actions that can do wrapper agent
class wrapperActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        cont = msg.getContent().split("-")
        res = ""
        if cont[2] == "GET":
            res = json.dumps(self.myAgent.patientsDB)
        elif cont[2] == "GET_Filtered":
            organ = json.loads(cont[3])
            receptors = []
            for i in self.myAgent.patientsDB:
                if i["organ_type"] == organ["organ_type"]:
                    receptors.append(i)
            res = json.dumps(receptors)
        else:
            content = json.loads(cont[2])
            if "id" not in content or not isinstance(content["id"], int):
                res = "ERROR, invalid id"
            elif "organ_type" not in content or content["organ_type"] not in self.myAgent.organs:
                res = "ERROR, invalid organ type"
            elif "critical_state" not in content or content["critical_state"] not in range(1,11):
                res = "ERROR, invalid critical state value"
            elif "transplant_authorization" not in content or content["transplant_authorization"] not in range(2):
                res = "ERROR, invalid transplant authorization value"
            else:
                patient = {}
                patient["id"] = content["id"]
                patient["organ_type"] = content["organ_type"]
                patient["critical_state"] = content["critical_state"]
                patient["hospital"] = hospital
                patient["transplant_authorization"] = content["transplant_authorization"]
                self.myAgent.patientsDB.append(patient)
                res = "DB updated"
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative(cont[0])
        msg2.addReceiver(spade.AID.aid(msg.getSender().getName(), ["xmpp://"+msg.getSender().getName()]))
        msg2.setContent(cont[1] + "-GET_Wrapper-" + res)
        self.myAgent.send(msg2)

#baheviour to register an agent in AMS
class AMS(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        a = self.myAgent.getAID()
        aad = spade.AMS.AmsAgentDescription()
        aad.setAID(a)
        aad.setOwnership("hospital")
        result = self.myAgent.modifyAgent(aad)
        if not result:
            print a.getName() + ": WARNING, AMS not updated"


#-----------------------------------------------------------------------
#!!!---------------------INTERFACE AGENT-----------------------------!!!
#-----------------------------------------------------------------------


#agent that can comunicate with user
class interface(spade.Agent.Agent):
    def _setup(self):
        self.input = 1
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName("interface")
        sd.setType("interface")
        sd.setOwnership("hospital")
        sd.addProperty("description", "system interface")
        sd.addLanguage("doctor requests")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#extra acctions to add patients in hospital database
class interfaceActions(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        aid = self.myAgent.getAID().getName()
        content = {"id":123, "organ_type":"heart", "critical_state":5, "transplant_authorization":1}
        msg = spade.ACLMessage.ACLMessage()
        msg.setPerformative("wrapper")
        msg.addReceiver(spade.AID.aid("wrapper@"+spadeHost, ["xmpp://wrapper@" + spadeHost]))
        msg.setContent("interface-0-" + json.dumps(content))
        self.myAgent.send(msg)

        content = {"id":124, "organ_type":"lung", "critical_state":3, "transplant_authorization":1}
        msg.setContent("interface-0-" + json.dumps(content))
        self.myAgent.send(msg)

#behaviour to show in terminal the hospital actions
class interfacePrint(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        aid = self.myAgent.getAID().getName()
        content = msg.getContent().split("-")
        if content[1] == "GET_Wrapper":
            print aid + ": " + content[2]
        elif content[1] == "GET_CoordinatorPatients":
            print aid + ": " + content[0] + " -> " + content[2]
        elif content[1] == "GET_CoordinatorError":
            print aid + ": " + content[2]
        elif content[1] == "GET_CoordinatorReceptor":
            print aid + ": Searching " + content[0] + " receptors"

#behaviour to detect keyboard from user
class interfaceInput(spade.Behaviour.Behaviour):
    def onStart(self):
        time.sleep(2)
    def _process(self):
        if self.myAgent.input:
            aid = self.myAgent.getAID().getName()
            s = raw_input(aid + ": Insert organ information (CTRL+C to exit): ")
            if self.myAgent.input:
                if s not in wr.organs:
                    print aid + ": ERROR, invalid organ"
                else:
                    inter.input = 0
                    organ = {}
                    organ["organ_type"] = s
                    print aid + ": Organ DB updated"
                    msg = spade.ACLMessage.ACLMessage()
                    msg.setPerformative("coordinator")
                    msg.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                    msg.setContent("0-GET_Interface-" + json.dumps(organ))
                    self.myAgent.send(msg)


#-----------------------------------------------------------------------
#!!!----------------TRANSPLANT COORDINATOR AGENT---------------------!!!
#-----------------------------------------------------------------------


#agent that coordinate organ transplants and comunicates with REST agent
class transplantCoordinator(spade.Agent.Agent):
    def _setup(self):
        self.layers = {0 : "0Emergency", 1 : "hospital", 2 : "city", 3 : "region", 4 : "zone", 5 : "country"}
        self.requestLayer = 0
        self.organ = {}
        self.patients = []
        self.pReceptor = {}
        self.cityPatients = {}
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName("transplantCoordinator")
        sd.setType("transplantCoordinator")
        sd.setOwnership("hospital")
        sd.addProperty("description", "comunication with other hospitals & region")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> ", str(res)

#actions that can do transplant coordinator agent
class coordinatorActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[1] == "SEND_Patients":
            msg3 = spade.ACLMessage.ACLMessage()
            msg3.setPerformative("interface")
            msg3.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
            msg3.setContent("Searching patients for organ" + "-GET_CoordinatorPatients-" + content[2])
            self.myAgent.send(msg3)

            msg2.setPerformative("wrapper")
            msg2.addReceiver(spade.AID.aid("wrapper@"+spadeHost, ["xmpp://wrapper@"+spadeHost]))
            msg2.setContent("coordinator-" + content[0] + "-GET_Filtered-" + content[2])
        elif content[1] == "GET_Wrapper":
            if content[0] == "H":
                self.myAgent.patients = json.loads(content[2])
                msg2.setPerformative("coordinator")
                msg2.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                msg2.setContent("0-SMART_Protocol")
            else:
                msg2.setPerformative("complete")
                msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
                msg2.setContent(content[0] + "-" + content[2])
        elif content[1] == "GET_Interface":
            msg3 = spade.ACLMessage.ACLMessage()
            msg3.setPerformative("interface")
            msg3.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
            msg3.setContent(self.myAgent.layers[self.myAgent.requestLayer] + "-GET_CoordinatorReceptor-" + content[2])
            self.myAgent.send(msg3)

            self.myAgent.organ = json.loads(content[2])
            msg2.setPerformative("request")
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(self.myAgent.layers[self.myAgent.requestLayer] + "-" + content[2])
        elif content[1] == "SMART_Protocol":
            if self.myAgent.pReceptor != {}:
                self.myAgent.patients.remove(self.myAgent.pReceptor)
                self.myAgent.pReceptor = {}
            if len(self.myAgent.patients) == 0:
                msg2.setPerformative("coordinator")
                msg2.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                msg2.setContent("0-New_Search")
            else:
                #PROTOCOL SMART
                print "PROTOCOL"
                self.myAgent.pReceptor = self.myAgent.patients[random.randint(0, len(self.myAgent.patients)-1)]
                res = "Posible receptor: " + json.dumps(self.myAgent.pReceptor)
                msg3 = spade.ACLMessage.ACLMessage()
                msg3.setPerformative("interface")
                msg3.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
                msg3.setContent("0-GET_CoordinatorError-" + res)
                if self.myAgent.requestLayer == 1:
                    msg2.setPerformative("coordinator")
                    msg2.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                    msg2.setContent("2-GET_Response-" + str(random.randint(0,1)))
                else:
                    msg2.setPerformative("request")
                    msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
                    msg2.setContent("GET_hospitalConfirmation-" + json.dumps(self.myAgent.pReceptor))
        elif content[1] == "GET_Response":
            if content[0] == "0":
                msg2.setPerformative("interface")
                msg2.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
                msg2.setContent("0-GET_CoordinatorError-" + content[2])
                self.myAgent.requestLayer = 0
                self.myAgent.pReceptor = {}
                self.myAgent.patients = []
                self.myAgent.cityPatients = {}
                inter.input = 1
            elif content[0] == "1":
                self.myAgent.patients = json.loads(content[2])
                print str(self.myAgent.patients)
                msg2.setPerformative("coordinator")
                msg2.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                msg2.setContent("0-SMART_Protocol")
            elif content[0] == "2":
                if content[2] == "1":
                    print "RECEPTOR ACEPTAT -> " + str(self.myAgent.pReceptor)
                    self.myAgent.requestLayer = 0
                    self.myAgent.pReceptor = {}
                    self.myAgent.patients = []
                    self.myAgent.cityPatients = {}
                    inter.input = 1

                else:
                    msg2.setPerformative("coordinator")
                    msg2.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                    msg2.setContent("0-SMART_Protocol")
            elif content[0] == "3":

                pass
            elif content[0] == "4":

                pass
        elif content[1] == "New_Search":
            self.myAgent.requestLayer += 1
            if self.myAgent.requestLayer == 6:
                msg2.setPerformative("interface")
                msg2.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
                msg2.setContent("0-GET_CoordinatorError-There are not compatible receptors")
                self.myAgent.requestLayer = 0
                self.myAgent.pReceptor = {}
                self.myAgent.patients = []
                self.myAgent.cityPatients = {}
                inter.input = 1
            elif self.myAgent.layers[self.myAgent.requestLayer] == "hospital":
                msg3 = spade.ACLMessage.ACLMessage()
                msg3.setPerformative("interface")
                msg3.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
                msg3.setContent(self.myAgent.layers[self.myAgent.requestLayer] + "-GET_CoordinatorReceptor")
                self.myAgent.send(msg3)

                msg2.setPerformative("wrapper")
                msg2.addReceiver(spade.AID.aid("wrapper@"+spadeHost, ["xmpp://wrapper@"+spadeHost]))
                msg2.setContent("coordinator-H-GET_Filtered-" + json.dumps(self.myAgent.organ))
            elif self.myAgent.layers[self.myAgent.requestLayer] == "city":
                if len(cityHospitals) > 0:
                    msg3 = spade.ACLMessage.ACLMessage()
                    msg3.setPerformative("interface")
                    msg3.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
                    msg3.setContent(self.myAgent.layers[self.myAgent.requestLayer] + "-GET_CoordinatorReceptor")
                    self.myAgent.send(msg3)

                    msg2.setPerformative("request")
                    msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
                    msg2.setContent(self.myAgent.layers[self.myAgent.requestLayer] + "-" + json.dumps(self.myAgent.organ))
                else:
                    msg2.setPerformative("coordinator")
                    msg2.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                    msg2.setContent("0-New_Search")
            else:
                msg3 = spade.ACLMessage.ACLMessage()
                msg3.setPerformative("interface")
                msg3.addReceiver(spade.AID.aid("interface@"+spadeHost, ["xmpp://interface@"+spadeHost]))
                msg3.setContent(self.myAgent.layers[self.myAgent.requestLayer] + "-GET_CoordinatorReceptor")
                self.myAgent.send(msg3)

                msg2.setPerformative("request")
                msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
                msg2.setContent(self.myAgent.layers[self.myAgent.requestLayer] + "-" + json.dumps(self.myAgent.organ))
        self.myAgent.send(msg2)


#-----------------------------------------------------------------------
#!!!-------------------------REST AGENT------------------------------!!!
#-----------------------------------------------------------------------


#agent that resolve request from Rest and comunicates with other agents from the platform 
class restAgent(spade.Agent.Agent):
    def _setup(self):
        self.petitions = {}
        self.id = 0
        aid = self.getAID()
        print aid.getName() + ": starting"

#behaviour to make external petitions
class makeRequest(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        c = 1
        status = "404/408"
        result = "invalid request body"
        try:
            if content[0] == "0Emergency":
                r = requests.get("http://"+remoteHost+"/"+hospital+"/0Emergency", data=content[1])
                result = r.text
                status = str(r.status_code)
            elif content[0] == "city":
                cPatients = []
                for i in cityHospitals:
                    try:
                        r = requests.get("http://"+i["remoteHost"]+"/patients", data=content[1])
                        cPatients += json.loads(r.text)
                        tc.cityPatients[i["hospital"]] = json.loads(r.text)
                        status = str(r.status_code)
                    except requests.exceptions.RequestException:
                        print "ERROR: Connection refused with " + i["hospital"]
                result = json.dumps(cPatients)
            elif content[0] == "region":
                r = requests.get("http://"+remoteHost+"/"+hospital+"/region", data=content[1], timeout = 10)
                result = r.text
                status = str(r.status_code)
            elif content[0] == "zone":
                r = requests.get("http://"+remoteHost+"/"+hospital+"/zone", data=content[1], timeout = 10)
                result = r.text
                status = str(r.status_code)
            elif content[0] == "country":
                r = requests.get("http://"+remoteHost+"/"+hospital+"/country", data=content[1])
                result = r.text
                status = str(r.status_code)
            elif content[0] == "PUT_HA":
                r = requests.put("http://"+remoteHost+"/"+hospital+"/hAgent", data=content[1])
                result = r.text
                status = str(r.status_code)
                c = 3
            elif content[0] == "POST_EC":
                r = requests.post("http://"+remoteHost+"/"+hospital+"/ecAgent", data=content[1])
                result = r.text
                status = str(r.status_code)
                c = 4
            elif content[0] == "GET_hospitalConfirmation":
                if tc.requestLayer == 0:
                    r = requests.get("http://"+remoteHost+"/"+hospital+"/0Emergency/confirmation", data=content[1])
                    result = r.text
                    status = str(r.status_code)
                elif tc.requestLayer == 2:
                    for i in cityHospitals:
                        if json.loads(content[1]) in tc.cityPatients[i["hospital"]]:
                            r = requests.get("http://"+i["remoteHost"]+"/confirmation", data=content[1])
                            result = r.text
                            status = str(r.status_code)
                else:
                    r = requests.get("http://"+remoteHost+"/"+hospital+"/region/confirmation", data=content[1], timeout = 10)
                    result = r.text
                    status = str(r.status_code)
                c = 2
        except requests.exceptions.RequestException:
            result = "ERROR 404 (connectionRefused)"
        except requests.exceptions.Timeout:
            result = "ERROR 408 (timeOutReached)"
        if status != "200" or "ERROR" in result:
            c = 0
        msg = spade.ACLMessage.ACLMessage()
        msg.setPerformative("coordinator")
        msg.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
        msg.setContent(str(c) + "-GET_Response-" + result)
        print "c: " + str(c)
        self.myAgent.send(msg)

#behaviour to receive messages from agents of the same platform
class petitionCompleted(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        pid = int(content[0])
        self.myAgent.petitions[pid][2] = content[1]
        self.myAgent.petitions[pid][0] = 2

#behaviour with the action that Rest agent can do, depending on the request to resolve
class restBehav(spade.Behaviour.Behaviour):
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
                    elif self.myAgent.petitions[k][1]=="GET_patients":
                        aid = self.myAgent.getAID().getName()
                        msg = spade.ACLMessage.ACLMessage()
                        msg.setPerformative("coordinator")
                        msg.addReceiver(spade.AID.aid("coordinator@"+spadeHost, ["xmpp://coordinator@"+spadeHost]))
                        msg.setContent(str(k) + "-SEND_Patients-" + self.myAgent.petitions[k][3])
                        self.myAgent.send(msg)
                    elif self.myAgent.petitions[k][1]=="GET_confirmation":
                        self.myAgent.petitions[k][2] = str(random.randint(0,1))
                        self.myAgent.petitions[k][0] = 2


#variable to intance the previous behaviour
RestBehaviour = restBehav()

#method to create an instance of the previous behaviour
def startRestBehaviour():
    RestBehaviour = restBehav()
    rest.addBehaviour(RestBehaviour, None)
    print "Rest Behaviour started"

#method to delete an instance of the previous behaviour
def stopRestBehaviour():
    rest.removeBehaviour(RestBehaviour)
    print "Rest Behaviour stopped"

#GET & OPTIONS request route, linked to funcion information
#if the request is GET, call Rest agent to inform about agent services platform
#request form: [request state, request used, empty string for information to send]
#if the request is OPTIONS, inform about the valid requests to use on this Rest API
@app.route('/', methods=['GET', 'OPTIONS'])
def information():
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
-GET /confirmation -> return confirmation of do organ transplant to a patient from the hospital
-GET /patients -> return receptors list from hospitals that are compatible with organ information sended
-OPTIONS / -> return list of possible requests from the platform
"""

#GET request route, linked to funcion consult
#Call Rest agent to get receptor list of the hospital
#Requires organ data input
#request form: [request state, request used, empty string for information to send, organ data]
@app.route("/patients", methods=["GET"])
def getPatients():
    idp=rest.id
    rest.id+=1
    rest.petitions[idp]=[0,"GET_patients", "", request.data]
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
#Call Rest agent to get confirmation of the hospital
#Requires receptor data input
#request form: [request state, request used, empty string for information to send, receptor data]
@app.route("/confirmation", methods=["GET"])
def getConfirmation():
    idp=rest.id
    rest.id+=1
    rest.petitions[idp]=[0,"GET_confirmation", "", request.data]
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

    arg = ""
    ch = []
    crh = []
    for x in range(1,len(sys.argv)):
        if sys.argv[x] == "-s":
            arg = "spadeHost"
        elif sys.argv[x] == "-r":
            arg = "restHost"
        elif sys.argv[x] == "-u":
            arg = "remoteHost"
        elif sys.argv[x] == "-h":
            arg = "hospital"
        elif sys.argv[x] == "-ch":
            arg = "cityHospitals"
        elif sys.argv[x] == "-cu":
            arg = "cityHosts"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "restHost" and restHost == "":
                restHost = sys.argv[x]
            elif arg == "remoteHost" and remoteHost == "":
                remoteHost = sys.argv[x]
            elif arg == "hospital" and hospital == "":
                hospital = sys.argv[x].lower()
            elif arg == "cityHospitals":
                ch.append(sys.argv[x].lower())
            elif arg == "cityHosts":
                crh.append(sys.argv[x])

    ch = list(set(ch))
    crh = list(set(crh))

    if spadeHost == "" or restHost == "" or remoteHost == "" or hospital == "":
        print "Require next arguments: -h hospital -s Spade_host -r rest_host -u region_host"
        print "OPTIONAL: -ch [city_hospitals] -cu [city_hospital_hosts]"
        sys.exit(0)
    if len(ch) > 0:
        if len(ch) != len(crh):
            print "The number of city hospitals and city hospital hosts must be equal"
            sys.exit(0)
        else:
            for i in range(len(ch)):
                h = {}
                h["hospital"] = ch[i]
                h["remoteHost"] = crh[i]
                cityHospitals.append(h)

    print "Spade host: " + spadeHost
    print "Hospital host: " + hospital + " -> " + restHost
    print "remote host: " + remoteHost
    if len(cityHospitals) > 0:
        for i in cityHospitals:
            print "City hospital: " + i["hospital"] + " -> " + i["remoteHost"]


    wr = wrapper("wrapper@"+spadeHost, "secret")
    inter = interface("interface@"+spadeHost, "secret")
    tc = transplantCoordinator("coordinator@"+spadeHost, "secret")
    rest = restAgent("rest@"+spadeHost, "secret")

    wr.addBehaviour(AMS(), None)
    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("wrapper")
    t = spade.Behaviour.MessageTemplate(aclt)
    wr.addBehaviour(wrapperActions(), t)

    inter.addBehaviour(AMS(), None)
    inter.addBehaviour(interfaceActions(), None)
    aclt2 = spade.Behaviour.ACLTemplate()
    aclt2.setPerformative("interface")
    t2 = spade.Behaviour.MessageTemplate(aclt2)
    inter.addBehaviour(interfacePrint(), t2)

    tc.addBehaviour(AMS(), None)
    aclt3 = spade.Behaviour.ACLTemplate()
    aclt3.setPerformative("coordinator")
    t3 = spade.Behaviour.MessageTemplate(aclt3)
    tc.addBehaviour(coordinatorActions(), t3)

    aclt4 = spade.Behaviour.ACLTemplate()
    aclt4.setPerformative("complete")
    t4 = spade.Behaviour.MessageTemplate(aclt4)
    rest.addBehaviour(petitionCompleted(), t4)

    aclt5 = spade.Behaviour.ACLTemplate()
    aclt5.setPerformative("request")
    t5 = spade.Behaviour.MessageTemplate(aclt5)
    rest.addBehaviour(makeRequest(), t5)
    rest.addBehaviour(RestBehaviour, None)

    wr.start()
    inter.start()
    tc.start()
    rest.start()

    inter.addBehaviour(interfaceInput(), None)

    #execute Rest system
    r = restHost.split(":")
    app.run(host = r[0], port = r[1])

    inter.input = 0

    wr.stop()
    inter.stop()
    tc.stop()
    rest.stop()

    sys.exit(0)

