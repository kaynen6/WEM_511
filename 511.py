## This script will grab data from Wisconsin 511 API and output to ArcGIS REST End Feature Service.
## Developed by Kayne Neigherbauer for Wisconsin Emergency Management


#import modules
try:
    import sys, urllib2, json, time, string, logging, logging.handlers, datetime, os
except ImportError:
    sys.exit("Error importing 1 or more required modules")
  

def main():
    
    #function to retrieve data from urls  
    def getData(url, feed):
        #get data from url
        try:
            webUrl = urllib2.urlopen(url[0])
        except urllib2.HTTPError as e:
            my_logger.exception("{0} getData Error: {1}".format(feed,str(e.code)))
        except urllib2.URLError as e:            
            my_logger.exception("{0} getData Error: {1}".format(feed,str(e.reason)))
        else:
            code = webUrl.getcode()
            if code == 200:
                # if success (200) then read the data
                try:
                    data = json.load(webUrl)
                except ValueError as e:
                    my_logger.exception("{0} getData Error: {1}".format(feed,str(e)))
                return data
            else:
                data = json.load(webUrl)
                if "ErrorCode" in data:
                    my_logger.error("Error Code in {0} getData: {1}".format(feed, data["ErrorCode"].get("Msg")))
                return None
        

    #function deletes old data on our end first, before adding up-to-date data
    def deleteData(url, feed):
        try: #request to server
            req = urllib2.Request(url[1],'f=json&where=objectid > 0')
            webUrl = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            my_logger.exception("{0} deleteData HTTPError: Code {1}".format(feed,str(e.code)))
        except urllib2.URLError as e: #url error exception handling
            my_logger.exception("{0} deleteData URLError: {1}".format(feed,str(e.reason)))
        else:
            #read response data
            response = json.load(webUrl)
            if response.get("success"): 
                my_logger.info("Existing {0} features successfully deleted.".format(feed))
            else:
                my_logger.info("Error deleting {0} features or no {0} features to delete.".format(feed))

    
    #function to post the formatted data to the database
    def postData(data, url):
        successCount = 0
        #send the new data
        try:
            req = urllib2.Request(url[2],'f=json&features=' + json.dumps(data, separators=(',', ': ')))
            web_url = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            my_logger.exception("{0} postData HTTPError: {1}".format(feed,str(e.code)))
        except urllib2.URLError as e:            
            my_logger.exception("{0} postData URLError {1}".format(feed,str(e.reason)))
        else: #load response data and report
            response = json.load(web_url)
            if response.get("addResults"):
                for item in response.get("addResults"):
                    if item.get("success") is True:
                        successCount += 1
                return successCount, None
            elif response.get("error"):
                if response["error"]["details"]:
                    return None, response["error"].get("details"[0])
                elif response["error"]["message"]:
                    return None, response["error"].get("message")
            else:
                return None, "Unknown Error"


    #dump last request data to log file for debugging help
    def writeFile(filename, data):
        with open(filename, "w") as f:
            json.dump(data, f)

      
    #winter road conditions 
    def postWinterDriving(url, feed):
        #delete old data
        deleteData(url, feed)
        #get new data from 511
        data = getData(url, feed)
        #create new empty geojson for newly formatted data
        newGJSON = []
        #parse and format data correctly for ESRI JSON specs
        if data:
            for i in range(0, len(data)):
                paths = []
                for point in data[i].get("SegmentCoordinates"):
                    paths.append([round(point.get("Longitude"), 5), round(point.get("Latitude"), 5)])
                attributes = data[i].copy()
                attributes["LocationDescription"] = attributes.get("LocationDescription").replace("/", "-")
                try:
                    del attributes["SegmentCoordinates"]
                    del attributes["StartCounty"]
                except KeyError:
                    my_logger.exception("KeyError - postWinterDriving")
                newFeat = [{"geometry": {"paths": [paths], "spatialReference": {"wkid": 4326}}, "attributes": attributes}]
                #add newly formatted data item to new geojson
                newGJSON.append(newFeat)
        #if new data was created, post it to WEM feature service
        if newGJSON:
            successCount = 0
            errors = []
            writeFile("WinterDriving.log",newGJSON)
            for feature in newGJSON:
                success, error = postData(feature,url)
                if success:
                    successCount = successCount + success
                if error:
                    if error not in errors:
                        errors.append(error)
            if errors:
                for e in errors:
                    my_logger.error("Error adding {0} features - {1}".format(feed, e))
            if successCount > 0:
                my_logger.info("{0} {1} features successfully added.".format(str(successCount), feed))


                

    #function for getEvents feed
    def postEvents(url, feed):
        #delete old data 
        deleteData(url, feed)
        #get new data from 511
        data = getData(url, feed)
        newGJSON = []
        #the event types from the feed we are interested in:
        eventTypes = ["accidentsAndIncidents", "closures","specialEvents"]
        #parse and format data correctly for ESRI JSON specs
        if data:
            for i in range(0,len(data)):
                if data[i].get("EventType") in eventTypes:
                    #format the dates correctly for webeoc
                    for date in ["Reported", "LastUpdated", "StartDate"]:
                        oldDate = time.strptime(data[i].get(date), "%d/%m/%Y %H:%M:%S")
                        newDate = time.strftime("%m/%d/%Y %H:%M:%S",oldDate)
                        data[i][date] = newDate
##                    if "Severity" in data[i]:
##                        data[i]["Severity"] = 0
                    #create new feature formatting and assign values
                    newFeat = {"geometry":{"x": data[i].get("Longitude"), "y": data[i].get("Latitude"), "spatialReference" : {"WKID": 4326}},"attributes": data[i].copy()}
                    #capitalize the event type
                    newFeat["attributes"]["EventSubType"] = string.capwords(newFeat["attributes"].get("EventSubType"))
                    if newFeat["attributes"]["Description"] is not None:
                        newFeat["attributes"]["Description"] = '{0}:\n{1}'.format(newFeat["attributes"]["EventSubType"], newFeat["attributes"]["Description"])
                    else:
                        newFeat["attributes"]["Description"] = '{0}'.format(newFeat["attributes"]["EventSubType"])
                    #add newly formatted data item to new geojson
                    newGJSON.append(newFeat)
                else: pass
            #if new data was created, post it to WEM feature service
            if newGJSON:
                writeFile("Events.log",newGJSON)
                successCount, errors = postData(newGJSON,url)
                if errors:
                    my_logger.error("Error adding {0} features - {1}".format(feed, errors))
                if successCount > 0:
                    my_logger.info("{0} {1} features successfully added.".format(str(successCount), feed))

    ##mainline link feed grabber
    def postMainlines(url, feed):
        #delete old data
        deleteData(url, feed)
        #get new data from 511
        data = getData(url, feed)
        newGJSON = []
        if data:
            for road in data:
                #format json as esri likes
                newFeat = {"geometry": {"paths": [], "spatialReference": {"wkid":4326}}, "attributes": road}
                segments = []
                #interate through the segments of lat/long pairs within each road segment
                for seg in newFeat["attributes"].pop("SegmentCoordinates"):
                    segment = [round(seg["Longitude"],5),round(seg["Latitude"],5)]
                    segments.append(segment)
                newFeat["geometry"]["paths"].append(segments)
                newGJSON.append(newFeat)
        successCount, errors = postData(newGJSON,url)
        if errors:
            my_logger.error("Error adding {0} features - {1}".format(feed, errors))
        if successCount > 0:
            my_logger.info("{0} {1} features successfully added.".format(str(successCount), feed))


    #function to define variables and start timing for repeating the data retrieval
    def timed_func(token, key, legacy_key):
        #### URLs ####
        #urls for winter driving conditions (511, our rest end delete, our rest end add)
        winterDrivingUrl = ('https://511wi.gov/web/api/winterroadconditions?key={0}&format=json'.format(legacy_key),
                            'https://widmamaps.us/dma/rest/services/WEM_Private/511_Winter_Road_Conditions/FeatureServer/0/deleteFeatures?token=' + token,
                            'https://widmamaps.us/dma/rest/services/WEM_Private/511_Winter_Road_Conditions/FeatureServer/0/addFeatures?token=' + token)
        #url for getEvents feed
        eventsUrl = ('https://511wi.gov/api/getevents?key={0}&format=json'.format(key),
                     'https://widmamaps.us/dma/rest/services/WEM_Private/511_Event_Incidents/FeatureServer/0/deleteFeatures?token=' + token,
                     'https://widmamaps.us/dma/rest/services/WEM_Private/511_Event_Incidents/FeatureServer/0/addFeatures?token=' + token)

        mainlineUrl = ('https://511wi.gov/web/api/MainlineLinks?key=' + legacy_key + '&format=json',
                       'https://widmamaps.us/dma/rest/services/WEM_Private/511_MainlineLinks/FeatureServer/0/deleteFeatures?token=' + token,
                       'https://widmamaps.us/dma/rest/services/WEM_Private/511_MainlineLinks/FeatureServer/0/addFeatures?token=' + token)

        #call each function with each url string as the argument
        postWinterDriving(winterDrivingUrl, "Winter Driving Conditions")
        postEvents(eventsUrl, "Events")
        postMainlines(mainlineUrl, "Mainline Links")


    #set up a logger
    logFile = '511.log'
    my_logger = logging.getLogger()
    my_logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(logFile,maxBytes = 2*1024*1024,backupCount=2)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',datefmt = '%m/%d/%y %I:%M:%S%p')
    handler.setFormatter(formatter)
    my_logger.addHandler(handler)
        
    #get current data and time for logging purposes 
    dt = datetime.datetime.now()
    log_time = dt.strftime("%m/%d/%y %I:%M:%S%p")
    #get a token from command line
    token = sys.argv[1]
    #511 api keys 
    key = sys.argv[2]
    legacy_key = sys.argv[3]
    
    timed_func(token, key, legacy_key)
       
if __name__ == "__main__":
    main()
