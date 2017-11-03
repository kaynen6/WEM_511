## This script will grab data from Wisconsin 511 API and output to ArcGIS REST End Feature Service.
## Developed by Kayne Neigherbauer for Wisconsin Emergency Management

#import modules
try:
    import sys, urllib, urllib2, json, time, string, logging, datetime, os, socket
except ImportError:
    sys.exit("Error importing 1 or more required modules")


def main():
    
    #function to retrieve data from urls  
    def getData(url):
        #get data from url
        try:
            webUrl = urllib2.urlopen(url[0])
        except urllib2.HTTPError as e:
            print "getDataError:",str(e.code)
            logging.exception('getData Error: %s' + '\n', e.code)
        except urllib2.URLError as e:            
            print "getDataError:", str(e.reason)
            logging.exception('getData Error: %s' + '\n', e.reason)
        else:
            code = webUrl.getcode()
            if code == 200:
                # if success (200) then read the data
                try:
                    data = json.load(webUrl)
                except ValueError as e:
                    dt = datetime.datetime.now()
                    print "getDataError:",str(e), dt.strftime("%m/%d/%y %I:%M:%S%p")
                    logging.exception('getData Error: %s' + '\n', e)
                if data == []: data = None
                return data
            else:
                if "ErrorCode" in response:
                    print repsonse["ErrorCode"].get("Msg")
                return None
        

    #function deletes old data on our end first, before adding up-to-date data
    def deleteData(url):
        try: #request to server
            req = urllib2.Request(url[1],'f=json&where=objectid <> 0')
            webUrl = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            print "HTTP Error: " + str(e.code)
            logging.exception('deleteData HTTPError: %s' + '\n', e.code)
        except urllib2.URLError as e: #url error exception handling
            print "URL Error Code: " + str(e.reason)
            logging.exception('deleteData - URLError: %s' + '\n', e.reason)
        else:
            #read response data
            response = json.load(webUrl)
            if response.get("success"): 
                print "Existing features successfully deleted."
            else:
                print "Error deleting features or no features to delete." #have this try function again to attempt delete if error.    

    
    #function to post the parsed data to the database
    def postData(data, url):
        #send the new data 
        try:
            req = urllib2.Request(url[2],'f=json&features=' + json.dumps(data, separators=(',', ': ')))
            webUrl = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            print "postData HTTP Error: " + str(e.code)
            logging.exception('postData HTTPError: %s' + '\n', e.code)
        except urllib2.URLError as e:            
            print "postData URL Error Code: " + str(e.reason)
            logging.exception('postData URL Error: %s'+ '\n', e.reason)
            time.sleep(3600)
        else: #load response data and report
            response = json.load(webUrl)
            #print response
            if response.get("addResults"):
                for item in response.get("addResults"):
                    if item.get("success") == True:
                        global successCount
                        successCount += 1
            elif response.get("error"):
                if response["error"]["details"]:
                    print "Error adding features" + " - " + response["error"].get("message") + ', ' + response["error"]["details"][0]
                    logging.debug("Error adding features" + " - " + response["error"].get("message") + ', ' + response["error"]["details"][0]+"\n")
                elif response["error"]["message"]:
                    print "Error adding features" + " - " + response["error"].get("message")
                    logging.debug("Error adding features" + " - " + response["error"].get("message")+"\n")
            else:
                print "Unknown Error, response from data feed: " + json.dumps(response) +"\n" + json.dumps(data, indent=2, separators=(',', ': '))



            
    #winter road conditions 
    def postWinterDriving(url):
        #delete old data
        deleteData(url)
        #get new data from 511
        data = getData(url)
        #create new empty geojson for newly formatted data
        newGJSON = []
        #parse and format data correctly for ESRI JSON specs
        if data:
            for i in range(0,len(data)):
                paths = []
                for point in data[i].get("SegmentCoordinates"):
                    paths.append([point.get("Longitude") , point.get("Latitude")])
                attributes = data[i].copy()
                try:
                    del attributes["SegmentCoordinates"]
                except KeyError:
                    print "KeyError - winter driving processing"
                    pass
                newFeat = {"geometry": {"paths": [paths], "spatialReference" : {"wkid" : 4326}} , "attributes" : attributes}
                #add newly formatted data item to new geojson
                newGJSON.append(newFeat)
        #if new data was created, post it to WEM feature service
        if newGJSON:
            postData(newGJSON,url)        
                

     
    #function for getEvents feed
    def postEvents(url):
        #delete old data 
        deleteData(url)
        #get new data from 511
        data = getData(url)
        newGJSON = []
        #the event types from the feed we are interested in:
        eventTypes = ["accidentsAndIncidents", "closures","specialEvents"]
        #parse and format data correctly for ESRI JSON specs
        if data:
            for i in range(0,len(data)):
                if data[i].get("EventType") in eventTypes:
                    newFeat = {"geometry":{"x": data[i].get("Longitude"), "y": data[i].get("Latitude"), "spatialReference" : {"WKID": 4326}},"attributes": data[i].copy()}
                    #capitalize the event type
                    newFeat["attributes"]["EventSubType"] = string.capwords(newFeat["attributes"].get("EventSubType"))
                    #add newly formatted data item to new geojson
                    newGJSON.append(newFeat)
                else: pass
            #if new data was created, post it to WEM feature service
            if newGJSON:
                postData(newGJSON,url)



    #function to fetch token for arcgis server access
    def getToken():
        ### change credentials ###
        params = {"username":"",
                  "password":"",
                  "client":"",
                  "f":"json",
                  "expiration":"60"}
        # url for token generation on our server
        tokenUrl = ""

        try:
            req = urllib2.Request(tokenUrl, urllib.urlencode(params))
            webUrl = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            print "HTTP Error: " + str(e.code)
            logging.exception("getToken HTTP Error: " + str(e.code))
        except urllib2.URLError as e:            
            print "URL Error: " + str(e.reason)
            logging.exception("getToken URL Error Code: " + str(e.reason))
        else:
            response = json.load(webUrl)
            print response
            if "token" in response:
                print "Getting new token..."
                #get values of token and token lifespan
                token = response.get("token")
                return token            
            else:
                if "error" in response:
                    print str(response["error"].get("message"))
                    logging.error("getToken Error:", response["error"].get("message"))
            
                return None, 0
                    


    #function to define variables and start timing for repeating the data retrieval
    def timed_func(token):
            #### Keys ####
            #511 api key 
            key = ''
            legacy_key = ''                        
            #data format requested 'xml' or 'json'
            dataFormat = 'json'
            #### URLs ####
            #urls for winter driving conditions (511, our rest end delete, our rest end add)
            winterDrivingUrl = ('https://511wi.gov/web/api/winterroadconditions?key=' + legacy_key + '&format=' + dataFormat,
                                'https://*********************' + token,
                                'https://*********************' + token)
            #url for getEvents feed
            eventsUrl = ('https://511wi.gov/api/getevents?key=' + key + '&format=' + dataFormat,
                         'https://***************' + token,
                         'https://***************' + token)
          
            #counter for successful items added
            global successCount
            successCount = 0
            
            #call each function with each url string as the argument
            postWinterDriving(winterDrivingUrl)
            postEvents(eventsUrl)
            
            #get current time
            dt = datetime.datetime.now()
            #print current time + results
            print dt.strftime("%m/%d/%y %I:%M:%S%p") +": "+ str(successCount) + " Features successfully added."

                       
    #define global var
    successCount = 0
    logging.basicConfig(filename='debug_511.log', filemode = 'w', level=logging.DEBUG)
    #set a timeout for web requests via socket module
    timeout = 30
    socket.setdefaulttimeout(timeout)
    #get a token from arcgis server
    token = getToken()
    timed_func(token)
        
             

       
if __name__ == "__main__":
    main()
