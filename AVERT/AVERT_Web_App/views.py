from django.shortcuts import render
from flask import Flask, request, render_template, jsonify
from collections import defaultdict
import urllib.request, json, requests, sys, re
import datetime
import urllib.parse
from collections import OrderedDict

rkdvoc = "http://ontologies.adaptcentre.ie/fairvasc#"
voidVocab = "http://rdfs.org/ns/void#vocabulary"

def index(request):
    context = {}
    layers = genClasses()
    info = genInfo()
    context["info"] = json.dumps(info)
    context["layersjson"] = json.dumps(layers)
    context["layers"] = layers
    return render(request, "index.html", context)

def genInfo():
    info = {}
    query = """ prefix void: <http://rdfs.org/ns/void#> 
                prefix rkddata: <http://data.fairvasc.ie/resource/rkd/> 
                prefix rkdvoc: <http://ontologies.adaptcentre.ie/fairvasc#> 
                prefix xsd: <http://www.w3.org/2001/XMLSchema#> 
                prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
                prefix dcterms: <http://purl.org/dc/terms/> 
                prefix prov: <http://www.w3.org/ns/prov#> 
                prefix foaf: <http://xmlns.com/foaf/0.1/> 
                prefix : <#> 

                SELECT DISTINCT ?key ?value
                WHERE {
                rkdvoc:RKD ?key ?value
                FILTER (?key != void:subset)
                }
            """
    finalquery = createquery(query)
    site = urlify(finalquery)   
    res = getjsonresults(site)

    for val in res:
        key = val["key"]["value"]
        if key in info and not type(info[key]) is list:
            tmpVal = info[key]
            info[key] = []
            info[key].append(tmpVal)
            info[key].append(val["value"]["value"])
        elif key in info:
            info[key].append(val["value"]["value"])
        else:
            info[key] = val["value"]["value"]
    return info
        
def genClasses():
    layers = {}
    query = """prefix void: <http://rdfs.org/ns/void#> 
    prefix rkddata: <http://data.fairvasc.ie/resource/rkd/> 
    prefix rkdvoc: <http://ontologies.adaptcentre.ie/fairvasc#> 
    prefix xsd: <http://www.w3.org/2001/XMLSchema#> 
    prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
    prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
    prefix dcterms: <http://purl.org/dc/terms/> 
    prefix prov: <http://www.w3.org/ns/prov#> 
    prefix foaf: <http://xmlns.com/foaf/0.1/> 
    prefix : <#> 

    SELECT DISTINCT ?layer_one ?layer_two ?layer_three ?n ?item ?rdf_n 
    WHERE 
    { 
    rkdvoc:RKD void:subset ?layer_one .
    OPTIONAL {
    ?layer_one void:objectsTarget [ ?rdf_n ?item ] .
    ?layer_one void:triples ?n . 
    }
    OPTIONAL {
        ?layer_one void:subset ?layer_two  .
        OPTIONAL {
        ?layer_two void:triples ?n . 
        ?layer_two void:objectsTarget [ ?rdf_n ?item ] .
        }
        OPTIONAL {
        ?layer_two void:subset ?layer_three  .
        ?layer_three void:triples ?n . 
        ?layer_three void:objectsTarget [ ?rdf_n ?item ] .
        }
    }
    } ORDER BY xsd:integer(strafter(str(?rdf_n), str(rdf:_)))"""

    finalquery = createquery(query)
    site = urlify(finalquery)   
    res = getjsonresults(site)

    for c in res:
        layerOne = c["layer_one"]["value"].replace(rkdvoc, '')
        if "layer_two" not in c:
            if layerOne not in layers:
                layers[layerOne] = []
                layers[layerOne].append("total_" + c["n"]["value"])
                layers[layerOne].append(c["item"]["value"])
            elif layerOne in layers:
                layers[layerOne].append(c["item"]["value"])
        if "layer_two" in c and "layer_three" not in c:
            layerTwo = c["layer_two"]["value"].replace(rkdvoc, '')
            if layerOne not in layers:
                layers[layerOne] = {}
            if layerTwo not in layers[layerOne]:
                layers[layerOne][layerTwo] = []
                layers[layerOne][layerTwo].append("total_" + c["n"]["value"])
                layers[layerOne][layerTwo].append(c["item"]["value"])
            else:
                layers[layerOne][layerTwo].append(c["item"]["value"])
        if "layer_two" in c and "layer_three" in c:
            layerTwo = c["layer_two"]["value"].replace(rkdvoc, '')
            layerThree = c["layer_three"]["value"].replace(rkdvoc, '')
            if layerOne not in layers:
                layers[layerOne] = {}
            if layerTwo not in layers[layerOne]:
                layers[layerOne][layerTwo] = {}
            if layerThree not in layers[layerOne][layerTwo]:
                layers[layerOne][layerTwo][layerThree] = []
                layers[layerOne][layerTwo][layerThree].append("total_" + c["n"]["value"])
                layers[layerOne][layerTwo][layerThree].append(c["item"]["value"])
            else:
                layers[layerOne][layerTwo][layerThree].append(c["item"]["value"])
    return layers

def displayResults(request):
    context ={}
    query = request.POST.get("query")
    query = json.loads(query)
    context["queries"] = query
    genQuery(query)
    return render(request, "displayResults.html", context)

def genQuery(query):
    finalQuery = ""
    rkdvoc = query["information"][voidVocab].replace('<', "").replace('>', "")

    select = "SELECT ?id "

    selectvalues = ""

    where = " WHERE { "

    groupby = "GROUP BY "

    where = where + " ?rec " + "<" + rkdvoc + "patientID> ?id. "

    index = 1

    for levelOne in query:
        if levelOne != "information":
            if type(query[levelOne]) is list:
                for val in query[levelOne]:
                    where = where + " ?rec " + "<" + rkdvoc + levelOne + ">" + " '" + val + "' ."
            else:
                where = where + " ?rec " + "<" + rkdvoc + levelOne + ">" + " ?var" + str(index) + " ." 
                select = select + "?var" + str(index) + " "

                for levelTwo in query[levelOne]:
                    if type(query[levelOne][levelTwo]) is list:
                        for levelThree in query[levelOne][levelTwo]:
                            where = where + " ?var" + str(index) + " " + "<" + rkdvoc + levelTwo + "> '" + levelThree + "' ." 
                    else:
                        where = where + " ?var" + str(index) + " "  + "<" + rkdvoc + levelTwo + ">" + " ?var" + str(index + 1) + " ." 
                        select = select + "?var" + str(index + 1) + " "
                        index = index + 1

                        for levelThree in query[levelOne][levelTwo]:
                            for levelFour in query[levelOne][levelTwo][levelThree]:
                                where = where + " ?var" + str(index) + " " + "<" + rkdvoc + levelThree + "> '" + levelFour + "' ." 

                index = index + 1 
    finalQuery = select + where + "}"
    print(finalQuery)


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
