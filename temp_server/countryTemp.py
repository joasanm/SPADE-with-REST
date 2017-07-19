import spade
import sys
import time
import requests


#-----------------------------------------------------------------------
#!!!-----------------GLOBAL VARIABLES--------------------------------!!!
#-----------------------------------------------------------------------


spadeHost = ""

#list of autonomy representant agents that are declared in the system
autonomy_list = []

#list of request arguments that the REST agant will use to make a request
request = []


#-----------------------------------------------------------------------
#!!!------------------AUTONOMY REPRESENTANTS-------------------------!!!
#-----------------------------------------------------------------------


#autonomy representant agent that get the average temperature from his autonomy
class autonomRepr(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(aid.getName())
        sd.setType("autonomRepresentant")
        sd.setOwnership("country")
        sd.addProperty("description", "autonomy temperature representant")
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
        aad.setOwnership = "country"
        result = self.myAgent.modifyAgent(aad)
        if not result:
            print a.getName() + ": WARNING, AMS not updated"

#behaviour from REST agent tha make request to other platforms
class restRequest(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        msg = self._receive(block=True)
        aid = msg.getSender().getName()
        rmh = ""
        for i in autonomy_list:
            if i["aid"] == aid:
                rmh = i["remoteHost"]
        content = msg.getContent().split("-")
        result = ""
        try:
            if content[0] == "GET":
                if len(content) == 2 and content[1] == "average":
                    r = requests.get("http://"+rmh+"/"+content[1], timeout=12)
                    result = str(r.status_code) + "-" + r.text
                #else:
                    #r = requests.get("http://"+rmh+"/", timeout=12)
                    #result = str(r.status_code) + "-" + r.text
            #elif content[0] == "OPTIONS":
                #r = requests.options("http://"+rmh+"/", timeout=12)
                #result = str(r.status_code) + "-" + r.text
        except requests.exceptions.RequestException as e:
            print self.myAgent.getAID().getName() + ": ERROR, connection refused"
            print e
            result = "ERROR-connection refused"
        print "RESULT: " + result
        msg2 = spade.ACLMessage.ACLMessage()
        msg2.setPerformative("autonomy")
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

#behaviour that receive messages from country and REST agents
class reprActions(spade.Behaviour.Behaviour):
    def _process(self):
        msg = self._receive(block=True)
        content = msg.getContent().split("-")
        msg2 = spade.ACLMessage.ACLMessage()
        if content[0] == "makeRequest":
            aid = self.myAgent.getAID().getName()
            msg2.setPerformative(aid)
            msg2.addReceiver(spade.AID.aid("rest@"+spadeHost, ["xmpp://rest@"+spadeHost]))
            req = content[1]
            if len(content) == 3:
                req = req + "-" + content[2]
            msg2.setContent(req)
            startRestRequest(aid)
        elif content[0] == "requestInformation":
            msg2.setPerformative("response")
            msg2.addReceiver(spade.AID.aid("country@"+spadeHost, ["xmpp://country@"+spadeHost]))
            msg2.setContent(content[1]+"-"+content[2])
        self.myAgent.send(msg2)


#-----------------------------------------------------------------------
#!!!------------------------COUNTRY AGENT----------------------------!!!
#-----------------------------------------------------------------------

#agent that represents the country that get the average temperature from diferents autonomies
class countryRepr(spade.Agent.Agent):
    def _setup(self):
        aid = self.getAID()
        sd = spade.DF.ServiceDescription()
        sd.setName(aid.getName())
        sd.setType("countryAgent")
        sd.setOwnership("country")
        sd.addProperty("description", "country temperature representant")
        sd.addLanguage("requests")
        dad = spade.DF.DfAgentDescription()
        dad.addService(sd)
        dad.setAID(aid)
        res = self.registerService(dad)
        print aid.getName() + ": service registered -> " + str(res)

#behaviour that get the temperature from diferents autonomies
class averageTemp(spade.Behaviour.TimeOutBehaviour):
    def onStart(self):
        print "waiting autonomy temperatures"

    def timeOut(self):
        print "waiting time finished"
        temps = 0
        avg = 0
        res = 0
        for x in range(len(autonomy_list)):
            msg = self._receive(False)
            if msg:
                content = msg.getContent().split("-")
                if content[0] == "200":
                    temps += float(content[1])
                    avg += 1
        print "msgs received correctly: " + str(avg)
        try:
            res = float("{0:.2f}".format(temps/avg))
        except ZeroDivisionError:
            res = 0

        print res

#variable that represents an instance of the previous behaviour
pl = averageTemp(15)

#method that add the previous behaviour to city agent
def startAverageTemp():
    pl = averageTemp(15)
    template = spade.Behaviour.ACLTemplate()
    template.setPerformative("response")
    t = spade.Behaviour.MessageTemplate(template)
    au.addBehaviour(pl, t)
    print "averageTemp Behaviour started"

#behaviour that send to each autonomy representant the request to make
class countryActions(spade.Behaviour.OneShotBehaviour):
    def _process(self):
        req=""
        if request[0]=="GET": 
            if len(request)>1:
                if request[1]=="average":
                    print "OBJETIVE: get average temperature from autonom"
                    req = "GET-" + request[1]
                else:
                    print "ERROR: invalid GET argument"
            else:
                print "OBJETIVE: get information about platform services"
                req = "GETED"

        if req == "":
            print "invalid request"
        elif req == "GETED":
            dad = spade.DF.DfAgentDescription()
            search=self.myAgent.searchService(dad)
            print search
        else:
            msg = spade.ACLMessage.ACLMessage()
            msg.setPerformative("autonomy")
            for i in autonomy_list:
                msg.addReceiver(spade.AID.aid(i["aid"], ["xmpp://"+i["aid"]]))
            msg.setContent("makeRequest-" + req)
            self.myAgent.send(msg)
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


#-----------------------------------------------------------------------
#!!!----------------------------MAIN---------------------------------!!!
#-----------------------------------------------------------------------


if __name__ == "__main__":

    arg = ""
    autonomies = []
    remoteHosts = []
    for x in range(1,len(sys.argv)):
        if sys.argv[x] == "-s":
            arg = "spadeHost"
        elif sys.argv[x] == "-u":
            arg = "remoteHost"
        elif sys.argv[x] == "-r":
            arg = "request"
        elif sys.argv[x] == "-a":
            arg = "autonomy"
        else:
            if arg == "spadeHost" and spadeHost == "":
                spadeHost = sys.argv[x]
            elif arg == "remoteHost":
                remoteHosts.append(sys.argv[x])
            elif arg == "request":
                request.append(sys.argv[x])
            elif arg == "autonomy":
                autonomies.append(sys.argv[x].lower())

    if spadeHost == "" or len(remoteHosts) == 0 or len(request) == 0 or len(autonomies) == 0:
        print "Require next arguments: -s Spade_host -a [autonomies] -u [remote_hosts] -r request (request_arguments)"
        sys.exit(0)
    if len(autonomies) != len(remoteHosts):
        print "The number of autonomy hosts and autonomies must be equal"
        sys.exit(0)

    for i in range(len(remoteHosts)):
        a = {}
        a["remoteHost"] = remoteHosts[i]
        a["autonomy"] = autonomies[i]
        autonomy_list.append(a)

    print "Spade host: " + spadeHost
    for i in autonomy_list:
        print "Autonomy: " + i["autonomy"] + " -> " + i["remoteHost"]

    for i in autonomy_list:
        i["agent"] = autonomRepr(i["autonomy"]+"@"+spadeHost, "secret")
        i["aid"] = i["agent"].getAID().getName()
        i["agent"].addBehaviour(AMS(), None)

        aclt = spade.Behaviour.ACLTemplate()
        aclt.setPerformative("autonomy")
        t = spade.Behaviour.MessageTemplate(aclt)
        i["agent"].addBehaviour(reprActions(), t)

        i["agent"].start()

    rest = RestAgent("rest@"+spadeHost, "secret")
    rest.start()

    ctr = countryRepr("country@"+spadeHost, "secret")

    ctr.addBehaviour(AMS(), None)
    aclt = spade.Behaviour.ACLTemplate()
    aclt.setPerformative("country")
    t = spade.Behaviour.MessageTemplate(aclt)
    ctr.addBehaviour(countryActions(), t)
    ctr.start() 

    alive = True
    while alive:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            alive=False

    for i in autonomy_list:
        i["agent"].stop()

    ctr.stop()
    rest.stop()

    sys.exit(0)

