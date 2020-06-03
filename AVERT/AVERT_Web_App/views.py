from django.shortcuts import render
from flask import Flask, request, render_template, jsonify
from collections import defaultdict
import urllib.request, json, requests, sys, re
import datetime
import urllib.parse
from collections import OrderedDict

def index(request):
    return render(request, "index.html")

def gengraph(request):
    context = {}
    if request.POST.get("patientid") != '':
        patientID = request.POST.get("patientid")
        classes, filters = genClasses(patientID)
        context["classesjson"] = json.dumps(classes)
        context["classes"] = classes
        context["filters"] = json.dumps(filters)
        
    return render(request, "index.html", context)

def genClasses(patientID):
    classes = {}
    filters = {}
    querywh = """PREFIX rkdvoc: <http://data.avert.ie/voc/rkd/>
        PREFIX rkddict: <http://data.avert.ie/data/rkddict/> 

		SELECT DISTINCT ?label ?kvp1 ?v1 ?v2 (strafter(str(?_sub_label), str(rkddict:)) as ?sub_label)
		WHERE {
			{  ?cat a rkdvoc:RKDRecord.
    		   ?cat rkdvoc:patientID '""" + patientID + """'.
    		   ?cat  rkdvoc:recordCategory ?label .
               ?cat rkdvoc:hasReading ?r1.
    		   ?r1 rkdvoc:hasTerm ?_sub_label	.
  			} 

        OPTIONAL {
                ?_sub_label rkdvoc:hasKeyValuePair ?kvp1.
                ?kvp1 rkdvoc:key ?v1.
                ?kvp1 rkdvoc:value ?v2.
            }
    } order by asc(UCASE(str(?sub_label)))"""

    finalquery = createquery(querywh)
    site = urlify(finalquery)   
    r = getjsonresults(site)

    for c in r:
        label = c["label"]["value"].replace('_', ' ')
        if label not in classes:
            classes[label] = []
        if c["sub_label"]["value"].replace('_', ' ') not in classes[label]:
            classes[label].append(c["sub_label"]["value"].replace('_', ' '))
        if "kvp1" in c:
            sub_label = c["sub_label"]["value"].replace('_', ' ')
            if sub_label not in filters:
                filters[sub_label] = []
            filters[sub_label].append(c["v2"]["value"].replace('_', ' '))

    return classes, filters

def tmpshowquery(request):
    context ={}
    q = request.POST.get("tmpquery")
    
    print(q, file=sys.stderr)
    context["queries"] = q
    return render(request, "tmpshowquery.html", context)

def initsearch(request):
    return render(request, "initsearch.html")

def getpatientid(request):
    recs = None
    r = None

    patienttype = str(request.POST.get("mulpatients"))

    userinput = None
    startdate = None
    enddate = None

    if (request.POST.get("startdate") != ''):
        startdate = request.POST.get("startdate")
        # datetime.datetime.strptime(startdate, '%Y-%m-%d').strftime('%m/%d/%y')
    
    if  (request.POST.get("enddate") != ''):
        enddate = request.POST.get("enddate")

    print(startdate, file=sys.stderr)
    print(enddate, file=sys.stderr)
    
    if startdate == None:
        startdate = ''
    
    if enddate == None:
        enddate = ''

    recs = get_recs(True, startdate, enddate, True)

    context = {
        "recs" : recs,
        "originaldists" : json.dumps(recs), 
        "startdate" : startdate, 
        "enddate" : enddate
    }
          
    return render(request, "displayInitialRes.html", context)

def getjsonresults(site):
    r = requests.get(url=site)
    r = r.json()
    return r["results"]["bindings"]

def createquery(query):
    return "http://localhost:3030/DB1/query?query=" + query

def removeurl(text):
    return text.replace("http://data.avert.ie/data/", "")

def urlify(in_string):
    in_string = in_string.replace(" ", "%20")
    in_string = in_string.replace("#", "%23")
    in_string = in_string.replace("<", "%3C")
    in_string = in_string.replace(">", "%3E")  
    in_string = in_string.replace("&", "%26") 
    in_string = in_string.replace("^", "%5E")   
    return in_string

def get_recs(adddist, startdate, enddate, mulpatients):
    recs = None
    r = None
    querywh = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
    prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    prefix xsd: <http://www.w3.org/2001/XMLSchema#> 
    prefix rkddict: <http://data.avert.ie/data/rkddict/>
    prefix rkdvoc: <http://data.avert.ie/voc/rkd/> 
    prefix rkddata: <http://data.avert.ie/data/rkd/> 
    prefix dc: <http://purl.org/dc/terms/> 
    prefix prov: <http://www.w3.org/ns/prov#>

    SELECT DISTINCT ?id ?hosp_val ?yob_val ?gen_val ?date
    WHERE {
    ?pr a rkdvoc:RKDRecord.
    ?pr rkdvoc:patientID ?id.
    ?pr rkdvoc:recordCategory "none".
    ?pr rkdvoc:hasReading ?r1, ?r2, ?r3, ?r4.
    ?r1 rkdvoc:hasTerm rkddict:date_of_diagnosis.
    ?r1 rkdvoc:hasValue ?date.
    ?r2 rkdvoc:hasTerm rkddict:hospital.
    ?r2 rkdvoc:hasValue ?hosp_key.
    ?r3 rkdvoc:hasTerm rkddict:year_of_birth.
    ?r3 rkdvoc:hasValue ?yob_val.
    ?r4 rkdvoc:hasTerm rkddict:gender.
    ?r4 rkdvoc:hasValue ?gen_key.
        OPTIONAL {
            rkddict:hospital rkdvoc:hasKeyValuePair ?kvp1.
            ?kvp1 rkdvoc:key ?hosp_key.
            ?kvp1 rkdvoc:value ?hosp_val.
            rkddict:gender rkdvoc:hasKeyValuePair ?kvp2.
            ?kvp2 rkdvoc:key ?gen_key.
            ?kvp2 rkdvoc:value ?gen_val.
        }"""

    # Waayyy too slow
    if startdate != '' and enddate == '':
        querywh = querywh + "FILTER (?date >= '" + startdate + "'^^xsd:date)"
    elif enddate != '' and startdate == '':
        querywh = querywh + "FILTER (?date <= '" + enddate + "'^^xsd:date)"
    elif startdate != '' and enddate != '':
        querywh = querywh + "FILTER (?date <= '" + enddate + "'^^xsd:date && ?date >= " + startdate + "^^xsd:date)"

    querywh = querywh + "} ORDER BY asc(xsd:integer(?id)) ?pr ?pr_date LIMIT 10"
    finalquery = createquery(querywh)
    site = urlify(finalquery)   
    r = getjsonresults(site)

    recs = {}

    for rec in r:
        patientId = rec["id"]["value"]
        recs[patientId] = {}
        recs[patientId]["gen_val"] = rec["gen_val"]["value"]
        recs[patientId]["hosp_val"] = rec["hosp_val"]["value"]        
        recs[patientId]["yob_val"] = rec["yob_val"]["value"]  
        recs[patientId]["age"] = datetime.datetime.now().year - int(rec["yob_val"]["value"])

    return recs


# def displayInitialRes(request):
#     if (request.POST.get("timequantity") != None and request.POST.get("timemeasure")):
#         timequantity = int(request.POST.get("timequantity"), 10)
#         timemeasure = request.POST.get("timemeasure")
#         dists = dists.replace("'", '"')
#         dists = json.loads(dists)
#         distid = request.POST.get("dist")
        
#     if request.POST.get("gender") or request.POST.get("over") or request.POST.get("under"):
#         diststmp = request.POST.get("filter")
#         diststmp = diststmp.replace("'", '"')
#         diststmp = json.loads(diststmp)
#         dists = {}
#         if request.POST.get("gender") != "0":
#             gender = request.POST.get("gender")
#         else:
#             gender = None
#         if request.POST.get("over") != '':
#             ageover = int(request.POST.get("over"))
#         else:
#             ageover = None
#         if request.POST.get("under") != '':
#             ageunder = int(request.POST.get("under"))
#         else:
#             ageunder = None

#         for dist in diststmp:
#             if ageover != None and gender != None:
#                 if diststmp[dist]["gen"] == gender and diststmp[dist]["age"] >= ageover:
#                     dists[dist] = diststmp[dist]
#             elif ageunder != None and gender != None:
#                 if diststmp[dist]["gen"] == gender and diststmp[dist]["age"] <= ageunder:
#                     dists[dist] = diststmp[dist]
#             elif ageover != None:
#                 if int(diststmp[dist]["age"]) >= ageover:
#                     dists[dist] = diststmp[dist]
#             elif ageunder != None:
#                 if int(diststmp[dist]["age"]) <= ageunder:
#                     dists[dist] = diststmp[dist]
#             elif gender != None:
#                 if diststmp[dist]["gen"] == gender:
#                     dists[dist] = diststmp[dist]
#             else:
#                 dists = diststmp
            
#         distid = None

#     context = {
#          "resultstype" : "multiplepatients", 
#          "dists" : dists, 
#          "distid" : distid, 
#          "results" : None, 
#          "patientid" : None, 
#          "originaldists" : diststmp
#     }

#     return render_template("AVERT_Web_app/displayInitialRes.html", context)

# def compareDistRecs():
#     if (request.method == "POST"):
#         demo = False
#         contmeds = False
#         plasma = False
#         encounters = False
#         complications = False
#         indivpatient = False
#         freqview = False
#         dispchart = False
#         biopsy = False
#         bvas = False
#         results = None
#         drugs = None
#         curr = None
#         title = None
#         latlon = None
#         graphresults = None
#         startdate = None
#         enddate = None
#         bvasvars = None
#         distrecs = {}

#         if request.POST.get("patientid"):
#             userinput = str(request.POST.get("patientid"))
#             if (userinput != "None"):
#                 adddist = request.POST.get("dist")
#                 startdate = None
#                 enddate = None

#                 reswdate = '{"' + userinput + '":"true", "startdate": "", "enddate": ""}' 
#                 distrecs = '{"' + userinput + '":"true"'
#                 indivpatient = True
                
#         elif request.POST.get("muldistrecs"):
#             distrecs = request.POST.get("muldistrecs")
#             startdate, enddate, distrecs, reswdate = jsoninput(distrecs)

#             if len(distrecs) == 1:
#                 indivpatient = True

#             if request.POST.get("category"):
#                 category = request.POST.get("category")
#                 if category == "Demographics":
#                     results = getDemo(list(distrecs.keys())[0])
#                     demo = True

#                 elif category == "Continuous Medication":
#                     if len(distrecs.keys()) <= 1:
#                         indivpatient = True
#                     results = getContMeds(list(distrecs.keys()), startdate, enddate)
#                     contmeds = True
                
#                 elif category == "Plasma Exchange":
#                     if len(distrecs.keys()) <= 1:
#                         indivpatient = True
#                     plasma = True
#                     results = getPlasma(list(distrecs.keys()), startdate, enddate)

#                 elif category == "Encounters":
#                     encounters = True
#                     results = getEncounters(list(distrecs.keys()), startdate, enddate)
                
#                 elif category == "Complications":
#                     complications = True
#                     results = getComplications(list(distrecs.keys()), startdate, enddate)
                
#                 elif category == "Biopsy":
#                     biopsy = True
#                     results = getBiopsy(list(distrecs.keys()), startdate, enddate)
            
#             if request.POST.get("type"):
#                 curr = request.POST.get("type")
#                 drugs = {}
#                 indivpatient = True

#                 plasma = True
#                 results = getPlasma(list(distrecs.keys()), startdate, enddate)

#                 for d in results:
#                     for d2 in results[d]:
#                         if (d2 == curr):
#                             date = datetime.strptime(results[d][d2].get("date"), '%Y-%m-%d')
#                             date = (date).strftime("%m-%d-%Y %H:%M:%S")
#                             drugs[date] = results[d][d2].get("vol")                        

#             if request.POST.get("drug"):
#                 results = getContMeds(list(distrecs.keys()), startdate, enddate)
#                 drug = request.POST.get("drug")
#                 drugs = {}
#                 curr = drug
#                 contmeds = True
#                 indivpatient = True
#                 tmp = None
#                 first = True
#                 prevdosage = None

#                 for d in results:
#                     for d2 in results[d]:
#                         if d2 == drug:
#                             startdate = datetime.strptime(results[d][d2].get("date"), '%Y-%m-%d')
#                             enddate = datetime.strptime(results[d][d2].get("enddate"), '%Y-%m-%d')

#                             if startdate != tmp and not first:
#                                 newstartdate = (tmp + timedelta(seconds=1)).strftime("%m-%d-%Y %H:%M:%S")
#                                 drugs[newstartdate] = 0
#                                 newenddate = (startdate - timedelta(seconds=1)).strftime("%m-%d-%Y %H:%M:%S")
#                                 drugs[newenddate] = 0
#                             elif startdate == tmp and not first:
#                                 newenddate = (startdate - timedelta(seconds=1)).strftime("%m-%d-%Y %H:%M:%S")
#                                 drugs[newenddate] = prevdosage
                            
#                             prevdosage = results[d][d2].get("dosage")
#                             tmp = enddate
#                             startdate = (startdate).strftime("%m-%d-%Y %H:%M:%S")
#                             drugs[startdate] = results[d][d2].get("dosage")
#                             enddate = (enddate).strftime("%m-%d-%Y %H:%M:%S")
#                             drugs[enddate] = results[d][d2].get("dosage")
#                             first = False
                
#             if request.POST.get("freqviewcomp"):
#                 results = getMulComplications(list(distrecs.keys()), startdate, enddate)
#                 freqview = True
#                 title = "Complications"
            
#             if request.POST.get("freqviewcont"):
#                 results = getMulContmeds(list(distrecs.keys()), startdate, enddate)
#                 freqview = True
#                 title = "Continuous Medication"
            
#             if request.POST.get("freqviewplasma"):
#                 results = getMulPlasma(list(distrecs.keys()), startdate, enddate)
#                 freqview = True
#                 title = "Plasma Exchange"
            
#             if request.POST.get("encchart"):
#                 encvars = request.POST.get("encchart")
#                 encvars = encvars.replace("'", '"')
#                 encvars = json.loads(encvars)
#                 results = getEncounters(list(distrecs.keys()), startdate, enddate)
#                 graphresults = getEncountersGraph(encvars, list(distrecs.keys())[0], startdate, enddate)
#                 dispchart = True
#                 title = "Encounters"
#                 encounters = True

#             if request.POST.get("bvasvars"):
#                 results, bvasvars = getBVASindiv(list(distrecs.keys()))
#                 bvas = True

#     return render_template("AVERT_Web_app/distillerRecsDispCmp.html", muldistrecs=reswdate, demo=demo, contmeds=contmeds, results=results, indivpatient=indivpatient, curr=curr, drugs=drugs, plasma=plasma, encounters=encounters, complications=complications, biopsy=biopsy, bvas=bvas, freqview=freqview, title=title, dispchart=dispchart, latlon=latlon, graphresults=graphresults, bvasvars=bvasvars)

# def jsoninput(inputjson):
#     inputjson = inputjson.replace("'", '"')
#     inputjson = json.loads(inputjson)

#     startdate = inputjson["startdate"]
#     enddate = inputjson["enddate"]

#     keystodel = list()

#     for i in inputjson:
#         if (inputjson[i] != "true"):
#             keystodel.append(i)
        
#     for key in keystodel:
#         del inputjson[key]
    
#     resultswdate = dict(inputjson)
#     resultswdate["startdate"] = startdate
#     resultswdate["enddate"] = enddate

#     return startdate, enddate, inputjson, resultswdate


# def getenddate(timequantity, timemeasure, startdate):
#     startdate = datetime.strptime(startdate, '%Y-%m-%d')
#     enddate = None 
#     if (timemeasure == "1"):
#         enddate = startdate + relativedelta(weeks=-timequantity)
#     elif (timemeasure == "2"):
#         enddate = startdate + relativedelta(months=-timequantity)
#     return enddate
    
# def getContMeds(userinputs, startdate, enddate):
#     contmeds = {}
#     for userinput in userinputs:
#         querysel = "SELECT "
#         querywh = "WHERE { "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querysel = querysel + "?dist ?date ?units ?dosage ?freq ?name ?enddate "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Continuous Medication%22 ."
#         querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> %22Medication%22 . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/dosageUnits> ?units . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/doseage> ?dosage . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/frequency> ?freq . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/medicationName> ?name . "
#         querywh = querywh + "?rec <http://www.w3.org/ns/prov#endedAtTime> ?enddate . "

#         querywh = querywh + datefilter(startdate, enddate) + " }"

#         querywh = querywh + "ORDER BY ?date"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         for dist in r:
#             key = dist["dist"]["value"]
#             contmeds[key] = {}
#             medskey = dist["name"]["value"]
#             contmeds[key][medskey] = {}
#             contmeds[key][medskey]["date"] = dist["date"]["value"]
#             contmeds[key][medskey]["units"] = dist["units"]["value"]
#             contmeds[key][medskey]["dosage"] = dist["dosage"]["value"]
#             contmeds[key][medskey]["freq"] = dist["freq"]["value"]
#             contmeds[key][medskey]["enddate"] = dist["enddate"]["value"]
#             contmeds[key][medskey]["id"] = userinput

#     return contmeds


# def getPlasma(userinputs, startdate, enddate):
#     plasma = {}
#     for userinput in userinputs:
#         querysel = "SELECT "
#         querywh = "WHERE { "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querysel = querysel + "?type ?vol ?dist ?date "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Plasma Exchange%22 ."
#         querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> %22Intravenous therapy%22 . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/plasmaExchangeType> ?type . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/plasmaExchangeVolumn> ?vol . "

#         querywh = querywh + datefilter(startdate, enddate) + " }"

#         querywh = querywh + "ORDER BY ?date"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         for dist in r:
#             key = dist["dist"]["value"]
#             plasma[key] = {}
#             typep = dist["type"]["value"]
#             plasma[key][typep] = {}
#             plasma[key][typep]["date"] = dist["date"]["value"]
#             plasma[key][typep]["vol"] = dist["vol"]["value"]
#             plasma[key][typep]["id"] = userinput
    
#     return plasma


# def getEncounters(userinputs, startdate, enddate):
#     encounters = {}    
#     for userinput in userinputs:
#         if userinput != "startdate" and userinput != "enddate":
#             querysel = "SELECT "
#             querywh = "WHERE { "
#             querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#             querysel = querysel + "?val ?lab ?date ?persistent "
#             querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#             querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#             querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Encounters%22 ."
#             querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#             querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#             querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> ?lab . "
#             querywh = querywh + "OPTIONAL { ?rec <http://data.avert.ie/vocabulary/distiller/readingValue> ?val . } "
#             querywh = querywh + "OPTIONAL { ?dist <http://data.avert.ie/vocabulary/distiller/persistentDisease> ?persistent . } "

#             querywh = querywh + datefilter(startdate, enddate) + " } "

#             querywh = querywh + " ORDER BY ?date"

#             finalquery = createquery(querysel + querywh)
#             site = urlify(finalquery)  
#             r = getjsonresults(site)

#             for dist in r:
#                 if userinput not in encounters:
#                     encounters[userinput] = {}
#                 typee = dist["lab"]["value"]
#                 date = dist["date"]["value"]
#                 if date not in encounters[userinput]:
#                     encounters[userinput][date] = {}
#                 encounters[userinput][date][typee] = {}
#                 if "val" in dist:
#                     encounters[userinput][date][typee]["value"] = dist["val"]["value"]
#                 else:
#                     encounters[userinput][date][typee]["value"] = ''
                
#                 if "persistent" in dist and "Persistent_Disease" not in encounters[userinput][date]:
#                     encounters[userinput][date]["Persistent_Disease"] = {}
#                     encounters[userinput][date]["Persistent_Disease"]["date"] = dist["date"]["value"]
#                     encounters[userinput][date]["Persistent_Disease"]["value"] = dist["persistent"]["value"]
#                 elif "persistent" not in dist and "Persistent_Disease" not in encounters[userinput][date]:
#                     encounters[userinput][date]["Persistent_Disease"] = {}
#                     encounters[userinput][date]["Persistent_Disease"]["date"] = dist["date"]["value"]
#                     encounters[userinput][date]["Persistent_Disease"]["value"] = "No"
    
#     return encounters

# def getEncountersGraph(vars, userinput, startdate, enddate):
#     encounters = {}    
#     for var in vars:
#         querysel = "SELECT "
#         querywh = "WHERE { "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querysel = querysel + "?val ?lab ?date "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Encounters%22 ."
#         querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> %22" + var + "%22 . "
#         querywh = querywh + " OPTIONAL { "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/readingValue> ?val . } "

#         querywh = querywh + datefilter(startdate, enddate) + " }"

#         querywh = querywh + "ORDER BY ?date"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         for dist in r:
#             date = dist["date"]["value"]
#             if var not in encounters:
#                 encounters[var] = {}
#             if "val" in dist:
#                 if var == "Weight" and dist["val"]["value"] != "0":
#                     encounters[var][date] = dist["val"]["value"]
#                 else:
#                     encounters[var][date] = None
#                 if var != "Weight":
#                     encounters[var][date] = dist["val"]["value"]
#             else:
#                 encounters[var][date] = None
    
#     return encounters

# def getComplications(userinputs, startdate, enddate):
#     complications = {}
#     for userinput in userinputs:
#         querysel = "SELECT "
#         querywh = "WHERE { "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querysel = querysel + "?val ?lab ?date "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Complications%22 ."
#         querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> ?lab . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/readingValue> ?val . "

#         querywh = querywh + datefilter(startdate, enddate) + " }"

#         querywh = querywh + "ORDER BY ?date"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         for dist in r:
#             if userinput not in complications:
#                 complications[userinput] = {}
#             typee = dist["lab"]["value"]
#             complications[userinput][typee] = {}
#             complications[userinput][typee]["date"] = dist["date"]["value"]
#             complications[userinput][typee]["value"] = dist["val"]["value"]
        
#     return complications

# def getMulComplications(userinputs, startdate, enddate):
#     mulcomplications = {}
#     for userinput in userinputs:
#         querysel = "SELECT "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querywh = "WHERE { "
#         querysel = querysel + "?val ?lab ?date "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Complications%22 ."
#         #querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> ?lab . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/readingValue> ?val . "

#         querywh = querywh + datefilter(startdate, enddate) + " }"

#         #querywh = querywh + "ORDER BY ?date"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         for dist in r:
#             typee = dist["lab"]["value"]
#             if typee not in mulcomplications and dist["val"]["value"] != "None" and dist["lab"]["value"] != 0:
#                 mulcomplications[typee] = {}
#                 mulcomplications[typee] = 1
#             elif dist["val"]["value"] != "None" and dist["val"]["value"] != 0:
#                 mulcomplications[typee] = mulcomplications[typee] + 1

#     return mulcomplications

# def getMulContmeds(userinputs, startdate, enddate):
#     mulmeds = {}
#     for userinput in userinputs:
#         querysel = "SELECT "
#         querywh = "WHERE { "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querysel = querysel + "?date ?name "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Continuous Medication%22 ."
#         querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> %22Medication%22 . "
#         querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/medicationName> ?name . "

#         querywh = querywh + datefilter(startdate, enddate) + " }"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         meds = {}

#         for dist in r:
#             typee = dist["name"]["value"].capitalize()
#             if typee not in mulmeds:
#                 mulmeds[typee] = {}
#                 mulmeds[typee] = 1
#                 meds[typee] = typee
#             elif typee not in meds:
#                 mulmeds[typee] = mulmeds[typee] + 1
#                 meds[typee] = typee
    
#     return mulmeds

# def getMulPlasma(userinputs, startdate, enddate):
#     mulplasma = {}
#     for userinput in userinputs:
#         querysel = "SELECT "
#         querywh = "WHERE { "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querysel = querysel + "?type ?vol ?date "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Plasma Exchange%22 ."
#         #querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> %22Intravenous therapy%22 . "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/plasmaExchangeType> ?type . "

#         querywh = querywh + datefilter(startdate, enddate) + " }"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         typeps = {}

#         for dist in r:
#             typep = dist["type"]["value"]
#             if typep not in mulplasma:
#                 mulplasma[typep] = {}
#                 mulplasma[typep] = 1
#                 typeps[typep] = typep
#             elif typep not in typeps:
#                 mulplasma[typep] = mulplasma[typep] + 1
#                 typeps[typep] = typep
    
#     return mulplasma

# def getBiopsy(userinputs, startdate, enddate):
#     biopsy = {}
#     for userinput in userinputs:
#         querysel = "SELECT "
#         querywh = "WHERE { "
#         querysel = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> " + querysel
#         querysel = querysel + "?site ?genfindings ?dist ?date ?renfindings ?vesfindings ?vessize ?renalberden "
#         querywh = querywh + "?dist a <http://data.avert.ie/vocabulary/distiller/DistillerPatientRecord> . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/avertID> %22" + userinput + "%22 ."
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/recordType> %22Biopsy%22 ."
#         querywh = querywh + "?dist <http://purl.org/dc/terms/date> ?date . "
#         querywh = querywh + "?dist <http://data.avert.ie/vocabulary/distiller/hasMedicalReading> ?rec . "
#         querywh = querywh + "?rec <http://www.w3.org/2000/01/rdf-schema#label> %22Biopsy%22 . "
#         querywh = querywh + " OPTIONAL { "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/biopsySite> ?site . } "
#         querywh = querywh + " OPTIONAL { "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/renalFindings> ?renfindings . } "
#         querywh = querywh + " OPTIONAL { "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/vesselFindings> ?vesfindings . } "
#         querywh = querywh + " OPTIONAL { "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/vesselSize> ?vessize . } "
#         querywh = querywh + " OPTIONAL { "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/renalBerdenScore> ?renalberden . } "
#         querywh = querywh + " OPTIONAL { "
#         querywh = querywh + "?rec <http://data.avert.ie/vocabulary/distiller/generalFindings> ?genfindings . } "

#         querywh = querywh + datefilter(startdate, enddate)

#         querywh = querywh + " }"

#         querywh = querywh + "ORDER BY ?date"

#         finalquery = createquery(querysel + querywh)
#         site = urlify(finalquery)  
#         r = getjsonresults(site)

#         for dist in r:
#             key = dist["dist"]["value"]
#             if userinput not in biopsy:
#                 biopsy[userinput] = {}
#             biopsy[userinput][key]= {}
#             biopsy[userinput][key]["date"] = dist["date"]["value"]
#             if "genfindings" in dist:
#                 biopsy[userinput][key]["genfindings"] = dist["genfindings"]["value"]
#             else:
#                 biopsy[userinput][key]["genfindings"] = "-"
#             if "renfindings" in dist:
#                 biopsy[userinput][key]["renfindings"] = dist["renfindings"]["value"]
#             else:
#                 biopsy[userinput][key]["renfindings"] = "-"
#             if "vesfindings" in dist:
#                 biopsy[userinput][key]["vesfindings"] = dist["vesfindings"]["value"]
#             else:
#                 biopsy[userinput][key]["vesfindings"] = "-"
#             if "vessize" in dist:
#                 biopsy[userinput][key]["vessize"] = dist["vessize"]["value"]
#             else:
#                 biopsy[userinput][key]["vessize"] = "-" 
#             if "site" in dist:
#                 biopsy[userinput][key]["site"] = dist["site"]["value"]
#             else:
#                 biopsy[userinput][key]["site"] = "-" 
#             if "renalberden" in dist:
#                 biopsy[userinput][key]["renalberden"] = dist["renalberden"]["value"]
#             else:
#                 biopsy[userinput][key]["renalberden"] = "-" 

#     return biopsy

# def datefilter(startdate, enddate):
#     result = ''
#     if startdate != '' and enddate != '':
#         result = result + " FILTER ( ?date <= %22" + startdate + "%22^^xsd:date && ?date > %22" + enddate + "%22^^xsd:date)"

#     elif enddate != '':
#         result = result + " FILTER (?date > %22" + enddate + "%22^^xsd:date)"
    
#     elif startdate != '':
#         result = result + " FILTER ( ?date <= %22" + startdate + "%22^^xsd:date)"

#     return result

# def getBVASindiv(userinput):
#     Cutaneous = ["Purpura", "Skin ulcer", "Progressive cutaneous gangrene", "Cutaneous vasculitis"]
#     Mucous_membranes = ["Ulcer of mouth", "Uveitis", "Sudden visual loss", "Blurred Vision", "Conjunctivitis", "Blepharitis", "Keratitis", "Episcleritis", "Scleritis", "Proptosis", "Pelvic inflammation", "Genital ulcer syndrome", "Changes in retinal vascular appearance"]
#     ENT = ["Hemorrhagic nasal discharge", "Paranasal Sinus", "Subglottic stenosis", "Conductive hearing loss", "Sensorineural hearing loss"]
#     Chest = ["Wheezing", "Lung nodule", "Pleural effusion", "Pulmonary Infiltrate", "Endobronchial", "Pulmonary alveolar haemorrhage", "Respiratory failure"]
#     Cardiovascular = ["Loss of Pulse", "Valvular Heart Disease", "Pericarditis", "Ischaemic chest pain", "Cardiomyopathy", "Congestive Heart Failure"]
#     Abdominal = ["Bloody diarrhoea", "Peritonitis", "Mesenteric ischemia"]
#     Renal = ["Renal hypertension", "Proteinuria", "Blood in urine", "Serum creatinine level 125-249", "Serum creatinine level 250-499", "Serum creatinine level 500", "Serum Creatinine Rise or Fall"]
#     Nervous_system = ["Headache", "Meningitis", "Confusion", "Seizures", "Cerebrovascular accident", "Spinal cord lesion", "Cranial Nerve Palsy", "Peripheral Sensory Neuropathy", "Mononeuritis multiplex"]
#     Persistent = ["Persistent_Disease"]

#     finalres = {}

#     tmp = getEncounters(userinput, '', '')

#     bvasvars = Cutaneous + Mucous_membranes + ENT + Chest + Cardiovascular + Abdominal + Renal + Nervous_system + Persistent

#     for t in tmp:
#         for t2 in tmp[t]:
#             date = t2
#             if date not in finalres:
#                 finalres[date] = {}
#                 finalres[date] = dict.fromkeys(bvasvars, ' ')
#                 finalres[date]["flare"] = False
#             for t3 in tmp[t][t2]:
#                 if t3 in bvasvars:
#                     finalres[date][t3] = {}   
#                     finalres[date][t3]["value"] = tmp[t][t2][t3]["value"]
#                     if finalres[date][t3]["value"] == "1":
#                         finalres[date]["flare"] = True

#                     if t3 == "Persistent_Disease":
#                         if tmp[t][t2][t3]["value"] == "Yes":
#                             finalres[date]["Persistent"] = "True"
#                         elif tmp[t][t2][t3]["value"] == "No":
#                             finalres[date]["Persistent"] = "False" 
#                         else:
#                             finalres[date]["Persistent"] = "N/A"  
#                     if t3 in Cutaneous:
#                         finalres[date][t3]["type"] = "Cutaneous"
#                     elif t3 in Mucous_membranes:
#                         finalres[date][t3]["type"] = "Mucous_membranes"
#                     elif t3 in ENT:
#                         finalres[date][t3]["type"] = "ENT"
#                     elif t3 in Chest:
#                         finalres[date][t3]["type"] = "Chest"
#                     elif t3 in Cardiovascular:
#                         finalres[date][t3]["type"] = "Cardiovascular"
#                     elif t3 in Abdominal:
#                         finalres[date][t3]["type"] = "CutAbdominalaneous"
#                     elif t3 in Renal:
#                         finalres[date][t3]["type"] = "Renal"
#                     elif t3 in Nervous_system:
#                         finalres[date][t3]["type"] = "Nervous_system"   

#     return finalres, bvasvars