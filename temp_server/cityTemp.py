#!flask/bin/python
from flask import Flask, abort, request
import spade
import sys
import time
import random


#-----------------------------------------------------------------------
#!!!-----------------GLOBAL VARIABLES--------------------------------!!!
#-----------------------------------------------------------------------


restHost = ""
spadeHost = ""

#list of local agents that are declared in the system
agents = []

#time that can wait a REST connection are defined in the timeout variable
timeout=10

#variable with the Rest system to use
app = Flask(__name__)


#-----------------------------------------------------------------------
#!!!---------------------LOCAL AGENT--------------------------------!!!
#-----------------------------------------------------------------------


#local agent that get temperature from a virtual sensor
class localAgent(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(aid.getName())
        sd.setType("localTemperature")
        sd.setOwnership("city")
        sd.addProperty("description", "local temperature sensor")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behaviour that generate a random temperature
class getTemp(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent()
        temp=float("{0:.2f}".format(random.uniform(15,35)))

        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("response")
        msg2.addReceiver(spade.AID.aid("city@"+spadeHost, ["xmpp://city@" + spadeHost]))
        msg2.setContent(content + "-" + str(temp))
        self.myAgent.send(msg2)

#behavior that register agents in the AMS
class AMS(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        a = self.myAgent.getAID()
        aad = spade.AMS.AmsAgentDescription()
        aad.setAID(a)
        aad.setOwnership = "city"
        result = self.myAgent.modifyAgent(aad)
        if not result:
            print a.getName() + ": WARNING, AMS not updated"


#-----------------------------------------------------------------------
#!!!---------------------CITY REPRESENTANT---------------------------!!!
#-----------------------------------------------------------------------


#agent that represents the city that get the average temperature from diferents local agents
class city(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(aid.getName())
        sd.setType("temperatureAverage")
        sd.setOwnership("city")
        sd.addProperty("description", "local temperature sensor average")
        sd.addLanguage("URI")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behaviour that get the temperature from diferents local agents
class averageTemp(spade.Behaviour.TimeOutBehaviour):
    def onStart(self):
        print "waiting local temperatures"

    def timeOut(self):
        print "waiting time finished"
        temps = 0
        pid = self.myAgent.petitionID
        avg = 0
        res = 0
        for x in range(len(agents)):
            msg = self._receive(False)
            if msg:
                content = msg.getContent().split("-")
                if content[0] == self.myAgent.petitionID:
                    temps += float(content[1])
                    avg += 1
        print "msgs received: " + str(avg)
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
pl = averageTemp(3)

#method that add the previous behaviour to city agent
def startAverageTemp():
    pl = averageTemp(3)
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative("response")
    t = spade.Behaviour.MessageTemplate(template)
    ct.addBehaviour(pl, t)
    print "averageTemp Behaviour started"

#behaviour that receive messages from REST agent
class getAverage(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("local")
        msg2.setContent(msg.getContent())
        self.myAgent.petitionID = msg.getContent()
        for i in agents:
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
                        msg.setPerformative("city")
                        msg.addReceiver(spade.AID.aid("city@"+spadeHost, ["xmpp://city@"+spadeHost]))
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

    numAgents = 0
    arg = ""
    for x in range(1,len(sys.argv)):
        if sys.argv[x] == "-s":
            arg = "spadeHost"
        elif sys.argv[x] == "-r":
            arg = "restHost"
        elif sys.argv[x] == "-n":
            arg = "agents"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "restHost" and restHost == "":
                restHost = sys.argv[x]
            elif arg == "agents" and numAgents == 0:
                numAgents = int(sys.argv[x])

    if spadeHost == "" or restHost == "" or numAgents == 0:
        print "Require next arguments: -s Spade_host -r rest_host -n num_agents"
        sys.exit(0)

    print "Spade host: "+spadeHost
    print "Rest host: "+restHost
    print "creating " + str(numAgents) + " agents..."

    for i in range(numAgents):
        agent = {}
        agent["agent"] = localAgent("localagent"+str(i)+"@"+spadeHost, "secret")
        agent["aid"] = agent["agent"].getAID().getName()
        agent["agent"].addBehaviour(AMS(), None)

        aclt = spade.Behaviour.ACLTemplate()
        aclt.setPerformative("local")
        t = spade.Behaviour.MessageTemplate(aclt)
        agent["agent"].addBehaviour(getTemp(), t)

        agents.append(agent)
        agents[i]["agent"].start()

    ct = city("city@"+spadeHost, "secret")
    rest = RestAgent("rest@"+spadeHost, "secret")

    ct.addBehaviour(AMS(), None)
    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("city")
    t = spade.Behaviour.MessageTemplate(aclt)
    ct.addBehaviour(getAverage(), t)
    ct.start()
    
    rest.addBehaviour(RestBehaviour, None)
    aclt2 = spade.Behaviour.ACLTemplate()
    aclt2.setPerformative("complete")
    t2 = spade.Behaviour.MessageTemplate(aclt2)
    rest.addBehaviour(petitionCompleted(), t2)

    rest.start()

    #execute Rest system
    r = restHost.split(":")
    app.run(host = r[0], port = r[1])

    for i in agents:
        i["agent"].stop()

    ct.stop()
    rest.stop()

    sys.exit(0)

