#!flask/bin/python
from flask import Flask, abort, request
import spade
import sys
import time
import requests


#-----------------------------------------------------------------------
#!!!-----------------GLOBAL VARIABLES--------------------------------!!!
#-----------------------------------------------------------------------


spadeHost = ""
restHost = ""
remoteHost = ""

#list of city representant agents that are declared in the system
city_list = []

#time that can wait a client connection are defined in the timeout variable
timeout=15

#variable with the Rest system to use
app = Flask(__name__)


#-----------------------------------------------------------------------
#!!!------------------CITY REPRESENTANTS-----------------------------!!!
#-----------------------------------------------------------------------


#city representant agent that get the average temperature from his city
class cityRepr(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(aid.getName())
        sd.setType("cityRepresentant")
        sd.setOwnership("autonom")
        sd.addProperty("description", "city temperature sensor")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behavior that register agents in the AMS
class AMS(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        a = self.myAgent.getAID()
        aad = spade.AMS.AmsAgentDescription()
        aad.setAID(a)
        aad.setOwnership = "autonomy"
        result = self.myAgent.modifyAgent(aad)
        if not result:
            print a.getName() + ": WARNING, AMS not updated"

#behaviour from REST agent tha make request to other platforms
class restRequest(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        msg = self._receive(block=True)
        aid = msg.getSender().getName()
        rmh = ""
        for i in city_list:
            if i["aid"] == aid:
                rmh = i["remoteHost"]
        content = msg.getContent()
        result = ""
        try:
            r = requests.get("http://"+rmh+"/average", timeout = 7)
            result = content + "-" + str(r.status_code) + "-" + r.text
        except requests.exceptions.RequestException as e:
            print self.myAgent.getAID().getName() + ": ERROR, connection refused"
            print e
            result = content + "-ERROR-0"
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("city")
        msg2.addReceiver(spade.AID.aid(aid, ["xmpp://"+aid]))
        msg2.setContent("requestInformation-" + result)
        self.myAgent.send(msg2)

#variable that represents an instance of the previous behaviour
rr = restRequest()

#method that add the previous behaviour to REST agent
def startRestRequest(sender):
    rr = restRequest()
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative(sender)
    t = spade.Behaviour.MessageTemplate(template)
    rest.addBehaviour(rr, t)
    print "restRequest Behaviour started"

#behaviour that receive messages from autonomy and REST agents
class reprActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "getTemperature":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            msg2.setContent(content[1])
            startRestRequest(aid)
        elif content[0] == "requestInformation":
            msg2.setPerformative("response")
            msg2.addReceiver(spade.AID.aid("autonom@"+spadeHost, ["xmpp://autonom@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2]+"-"+content[3])
        self.myAgent.send(msg2)


#-----------------------------------------------------------------------
#!!!---------------------AUTONOMY AGENT------------------------------!!!
#-----------------------------------------------------------------------


#agent that represents the autonomy that get the average temperature from diferents cities
class autonom(spade.Agent.Agent):
    def _setup(self):
        self.petitionID = ""
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(aid.getName())
        sd.setType("regionCoordinator")
        sd.setOwnership("autonom")
        sd.addProperty("description", "communication with cities & country")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behaviour that get the temperature from diferents cities
class averageTemp(spade.Behaviour.TimeOutBehaviour):
    def onStart(self):
        print "waiting local temperatures"

    def timeOut(self):
        print "waiting time finished"
        temps = 0
        pid = self.myAgent.petitionID
        avg = 0
        res = 0
        for x in range(len(city_list)):
            msg = self._receive(False)
            if msg:
                content = msg.getContent().split("-")
                if content[0] == self.myAgent.petitionID and content[1] == "200":
                    temps += float(content[2])
                    avg += 1
        print "msgs received correctly: " + str(avg)
        try:
            res = float("{0:.2f}".format(temps/avg))
        except ZeroDivisionError:
            res = 0

        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("complete")
        msg2.setContent(pid + "-" + str(res))
        msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
        self.myAgent.send(msg2)

#variable that represents an instance of the previous behaviour
pl = averageTemp(9)

#method that add the previous behaviour to city agent
def startAverageTemp():
    pl = averageTemp(9)
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative("response")
    t = spade.Behaviour.MessageTemplate(template)
    au.addBehaviour(pl, t)
    print "averageTemp Behaviour started"

#behaviour that receive messages from REST agent
class getAverage(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("city")
        msg2.setContent("getTemperature-" + msg.getContent())
        self.myAgent.petitionID = msg.getContent()
        for i in city_list:
            msg2.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
        self.myAgent.send(msg2)
        startAverageTemp()


#-----------------------------------------------------------------------
#!!!-------------------------REST AGENT------------------------------!!!
#-----------------------------------------------------------------------


#agent that resolve request from Rest and comunicates with other platform agents
class RestAgent(spade.Agent.Agent):
    def _setup(self):
        self.petitions = {}
        self.id = 0
        aid = self.getAID()
        print aid.getName() + ": starting"

#behaviour that receive messages from platform agents
class petitionCompleted(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        pid = int(content[0])
        self.myAgent.petitions[pid][2] = content[1]
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
                        msg.setPerformative("autonom")
                        msg.addReceiver(spade.AID.aid("autonom@"+spadeHost, ["xmpp://autonom@"+spadeHost]))
                        msg.setContent(str(k))
                        self.myAgent.send(msg)

#variable that represents an instance of the previous behaviour
RestBehaviour = RestBehav()

#method that add the previous behaviour to REST agent
def startRestBehaviour():
    RestBehaviour = RestBehav()
    rest.addBehaviour(RestBehaviour, None)
    print "started Rest Behaviour"

#method that remove the previous behaviour from REST agent
def stopRestBehaviour():
    rest.removeBehaviour(RestBehaviour)
    print "stopped Rest Behaviour"

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
        return """$GET / > return services list of the platform
$GET /average > return average temperature in Celsius from diferents city agent sensors
$OPTIONS / > return list of possible requests from the platform
"""

#GET request route, linked to funcion consult
#Call Rest agent to get information about the local temperature from some local zones,
#representated by agents, and get its average
#request form: [request state, request used, empty string for information to send]
@app.route('/average', methods=['GET'])
def consult():
    control = time.time()
    idp=rest.id
    rest.id+=1
    rest.petitions[idp]=[0,"GET2", ""]
    endtime=time.time()+timeout
    remaining=endtime-time.time()
    while rest.petitions[idp][0]!=2 and remaining>0.0:
            time.sleep(1)
            remaining=endtime-time.time()
    if rest.petitions[idp][0]==2:
        res=rest.petitions[idp][2]
        del rest.petitions[idp]
        print time.time() - control
        return str(res)
    else:
        stopRestBehaviour()
        del rest.petitions[idp]
        startRestBehaviour()
        print time.time() - control
        abort(500)

#-----------------------------------------------------------------------
#!!!----------------------------MAIN---------------------------------!!!
#-----------------------------------------------------------------------


if __name__ == "__main__":

    remoteHosts = []
    cities = []
    arg = ""
    for x in range(1,len(sys.argv)):
        if sys.argv[x] == "-s":
            arg = "spadeHost"
        elif sys.argv[x] == "-r":
            arg = "restHost"
        elif sys.argv[x] == "-u":
            arg = "remoteHost"
        elif sys.argv[x] == "-c":
            arg = "city"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "restHost" and restHost == "":
                restHost = sys.argv[x]
            elif arg == "remoteHost":
                remoteHosts.append(sys.argv[x])
            elif arg == "city":
                cities.append(sys.argv[x].lower())

    if spadeHost == "" or restHost == "" or len(remoteHosts) == 0 or len(cities) == 0:
        print "Require next arguments: -s Spade_host -r rest_host -c [cities] -u [city_hosts]"
        sys.exit(0)
    if len(cities) != len(remoteHosts):
        print "The number of city hosts and cities must be equal"
        sys.exit(0)

    for i in range(len(remoteHosts)):
        c = {}
        c["remoteHost"] = remoteHosts[i]
        c["city"] = cities[i]
        city_list.append(c)

    print "Spade host: " + spadeHost
    print "Region host: " + restHost
    for i in city_list:
        print "City: " + i["city"] + " -> " + i["remoteHost"]

    for i in city_list:
        i["agent"] = cityRepr(i["city"]+"@"+spadeHost, "secret")
        i["aid"] = i["agent"].getAID().getName()
        i["agent"].addBehaviour(AMS(), None)

        aclt = spade.Behaviour.ACLTemplate()
        aclt.setPerformative("city")
        t = spade.Behaviour.MessageTemplate(aclt)
        i["agent"].addBehaviour(reprActions(), t)

        i["agent"].start()
        

    au = autonom("autonom@"+spadeHost, "secret")
    rest = RestAgent("rest@"+spadeHost, "secret")

    au.addBehaviour(AMS(), None)
    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("autonom")
    t = spade.Behaviour.MessageTemplate(aclt)
    au.addBehaviour(getAverage(), t)

    au.start()
    
    rest.addBehaviour(RestBehaviour, None)
    aclt2 = spade.Behaviour.ACLTemplate()
    aclt2.setPerformative("complete")
    t2 = spade.Behaviour.MessageTemplate(aclt2)
    rest.addBehaviour(petitionCompleted(), t2)

    rest.start()

    #execute Rest system
    r = restHost.split(":")
    app.run(host = r[0], port = r[1])

    for i in city_list:
        i["agent"].stop()

    au.stop()
    rest.stop()

    sys.exit(0)

