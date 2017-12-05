## This script will grab data from Wisconsin 511 API and output to ArcGIS REST End Feature Service.
## Developed by Kayne Neigherbauer for Wisconsin Emergency Management


#import modules
try:
    import sys, urllib, urllib2, json, time, string, logging, logging.handlers, datetime, os, socket
except ImportError:
    sys.exit("Error importing 1 or more required modules")


def main():
    
    #function to retrieve data from urls  
    def getData(url):
        #get data from url
        try:
            webUrl = urllib2.urlopen(url[0])
        except urllib2.HTTPError as e:
            my_logger.exception('getData Error:' + str(e.code))
        except urllib2.URLError as e:            
            my_logger.exception('getData Error:' + str(e.reason))
        else:
            code = webUrl.getcode()
            if code == 200:
                # if success (200) then read the data
                try:
                    data = json.load(webUrl)
                except ValueError as e:
                    my_logger.exception('getData Error:'+ str(e))
                if data == []: data = None
                return data
            else:
                if "ErrorCode" in response:
                    my_logger.error(repsonse["ErrorCode"].get("Msg"))
                return None
        

    #function deletes old data on our end first, before adding up-to-date data
    def deleteData(url):
        try: #request to server
            req = urllib2.Request(url[1],'f=json&where=objectid <> 0')
            webUrl = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            my_logger.exception('deleteData HTTPError: Code' + str(e.code))
        except urllib2.URLError as e: #url error exception handling
            my_logger.exception('deleteData - URLError:' + str(e.reason))
        else:
            #read response data
            response = json.load(webUrl)
            if response.get("success"): 
                my_logger.info("Existing features successfully deleted.")
            else:
                my_logger.info("Error deleting features or no features to delete.")

    
    #function to post the parsed data to the database
    def postData(data, url):
        #send the new data 
        try:
            req = urllib2.Request(url[2],'f=json&features=' + json.dumps(data, separators=(',', ': ')))
            webUrl = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            my_logger.exception('postData HTTPError:' + str(e.code))
        except urllib2.URLError as e:            
            my_logger.exception('postData URLError:' + str(e.reason))
        else: #load response data and report
            response = json.load(webUrl)
            if response.get("addResults"):
                for item in response.get("addResults"):
                    if item.get("success") == True:
                        global successCount
                        successCount += 1
            elif response.get("error"):
                if response["error"]["details"]:
                    my_logger.error("Error adding features -" + response["error"].get("message"),response["error"]["details"][0])
                elif response["error"]["message"]:
                    my_logger.error('Error adding features -' + response["error"].get("message"))
            else:
                my_logger.error("Unknown Error")

      
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
                    paths.append([round(point.get("Longitude"),5) , round(point.get("Latitude"),5)])
                attributes = data[i].copy()
                attributes["LocationDescription"] = attributes.get("LocationDescription").replace("/","-")
                try:
                    del attributes["SegmentCoordinates"]
                    del attributes["StartCounty"]
                except KeyError:
                    my_logger.exception("KeyError - postWinterDriving")
                newFeat = [{"geometry": {"paths": [paths], "spatialReference" : {"wkid" : 4326}} , "attributes" : attributes}]
                #add newly formatted data item to new geojson
                newGJSON.append(newFeat)
        #if new data was created, post it to WEM feature service
        if newGJSON:
            for feature in newGJSON:
                postData(feature,url)
       
                

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
                

    #function to define variables and start timing for repeating the data retrieval
    def timed_func(token, key, legacy_key):
                                    
        #data format requested 'xml' or 'json'
        dataFormat = 'json'
        #### URLs ####
        #urls for winter driving conditions (511, our rest end delete, our rest end add)
        winterDrivingUrl = ('https://511wi.gov/web/api/winterroadconditions?key=' + legacy_key + '&format=' + dataFormat,
                            'https://___________________/511_Winter_Road_Conditions/FeatureServer/0/deleteFeatures?token=' + token,
                            'https://___________________/511_Winter_Road_Conditions/FeatureServer/0/addFeatures?token=' + token)
        #url for getEvents feed
        eventsUrl = ('https://511wi.gov/api/getevents?key=' + key + '&format=' + dataFormat,
                     'https://___________________511_Event_Incidents/FeatureServer/0/deleteFeatures?token=' + token,
                     'https://___________________511_Event_Incidents/FeatureServer/0/addFeatures?token=' + token)
      
        #counter for successful items added
        global successCount
        successCount = 0
        
        #call each function with each url string as the argument
        postWinterDriving(winterDrivingUrl)
        postEvents(eventsUrl)

        my_logger.info(str(successCount) + " Features successfully added.")
        print log_time, str(successCount), "Features successfully added."

                       
   
    #set a timeout for web requests via socket module
    timeout = 10
    socket.setdefaulttimeout(timeout)
    
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
