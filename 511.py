## This script will grab data from Wisconsin 511 API and output to ArcGIS REST End Feature Service.
## Developed by Kayne Neigherbauer for Wisconsin Emergency Management


#import modules
try:
    import sys, requests, json, time, string, logging, logging.handlers, datetime, os
except ImportError:
    sys.exit("Error importing 1 or more required modules")



def main():
    
    #function to retrieve data from urls  
    def getData(url, payload):
        #get data from url
        try:
            r = requests.get(url, params=payload, timeout=10)
        except requests.HTTPError as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        except requests.URLRequired as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        except requests.Timeout as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        else:
            if r.status_code == 200:
                # if success (200) then read the data
                try:
                    data = r.json()
                except ValueError as e:
                    my_logger.exception('getData Error: {0}'.format(e.message))
                    data = None
                return data
            else:
                data = r.json()
                if "ErrorCode" in data:
                    my_logger.error(data["ErrorCode"].get("Msg"))
                return None
        

    #function deletes old data on our end first, before adding up-to-date data
    def deleteData(url, payload):
        payload['where'] = "objectid > 0"
        try: #request to server
            r = requests.post(url, data=payload, timeout=10)
        except requests.HTTPError as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        except requests.URLRequired as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        except requests.Timeout as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        else:
            #read response data
            if r.status_code == 200:
                response = r.json()
                if response.get("success"):
                    my_logger.info("Existing features successfully deleted.")
                else:
                    my_logger.info("Error deleting features or no features to delete.")

    
    #function to post the parsed data to the database
    def postData(data, url, payload):
        #send the new data
        global successCount
        payload['features'] = data
        try:
            r = requests.post(url, data=payload, timeout=10)
        except requests.HTTPError as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        except requests.URLRequired as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        except requests.Timeout as e:
            my_logger.exception('getData Error: {0}'.format(e.message))
        else:
            #load response data and report
            if r.status_code == 200:
                response = r.json()
                if response.get("addResults"):
                    for item in response.get("addResults"):
                        if item.get("success"):
                            successCount += 1
                elif response.get("error"):
                    if response["error"]["details"]:
                        my_logger.error("Error adding features - {0}{1}".format(response["error"].get("message"),response["error"]["details"][0]))
                    elif response["error"]["message"]:
                        my_logger.error('Error adding features -' + response["error"].get("message"))
                else:
                    my_logger.error("Unknown Error")

    #dump last request data to log file for debugging help
    def writeFile(filename, data):
        with open(filename, "w") as f:
            json.dump(data, f)

      
    #winter road conditions 
    def postWinterDriving(url, payloads):
        #delete old data
        deleteData(url[1], payloads['WEM'])
        #get new data from 511
        data = getData(url[0], payloads['511_legacy'])
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
            writeFile("WinterDriving.log",newGJSON)
            for feature in newGJSON:
                postData(json.dumps(feature), url[2], payloads['WEM'])
       
                

    #function for getEvents feed
    def postEvents(url, payloads):
        #delete old data 
        deleteData(url[1], payloads['WEM'])
        #get new data from 511
        data = getData(url[0], payloads['511'])
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
                postData(json.dumps(newGJSON), url[2], payloads['WEM'])


    def log_count(successCount):
        my_logger.info(str(successCount) + " Features successfully added.")
        print log_time, str(successCount), "Features successfully added."

    #function to define variables and start timing for repeating the data retrieval
    def timed_func(token, key, legacy_key):
        #### URLs ####
        #urls for winter driving conditions (511, our rest end delete, our rest end add)
        winterDrivingUrl = ('https://511wi.gov/web/api/winterroadconditions',
                            'https://widmamaps.us/dma/rest/services/WEM_Private/511_Winter_Road_Conditions/FeatureServer/0/deleteFeatures',
                            'https://widmamaps.us/dma/rest/services/WEM_Private/511_Winter_Road_Conditions/FeatureServer/0/addFeatures')
        payloads = {
            '511_legacy': {'key': legacy_key, 'format': 'json'},
            '511': {'key': key, 'format': 'json'},
            'WEM': {'token': token, 'f': 'json'}
            }
        #url for getEvents feed
        eventsUrl = ('https://511wi.gov/api/getevents',
                     'https://widmamaps.us/dma/rest/services/WEM_Private/511_Event_Incidents/FeatureServer/0/deleteFeatures',
                     'https://widmamaps.us/dma/rest/services/WEM_Private/511_Event_Incidents/FeatureServer/0/addFeatures')
      

        #call each function with each url string as the argument
        postWinterDriving(winterDrivingUrl, payloads)
        postEvents(eventsUrl, payloads)
        my_logger.info(str(successCount) + " Features successfully added.")
        print log_time, str(successCount), "Features successfully added."


    #set up a logger
    logFile = '511_run.log'
    my_logger = logging.getLogger()
    my_logger.setLevel(20)
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
    # counter for successful items added
    global successCount
    successCount = 0
    timed_func(token, key, legacy_key)
       
if __name__ == "__main__":
    main()
