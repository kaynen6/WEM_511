## quick script to email log file result of other scripts. Meant to be run as a scheduled event ###
## author- Kayne Neigherbauer for Wisconsin Emergency Management 2017 ##

import smtplib
from email.mime.text import MIMEText

fromAdd = 'email@domain.com'
toAdd = 'email@domain.gov'

def readFile(fileName):
    with open('N:\\GIS_Program\\Projects\\Scripting_Live_Data_Feeds\\'+fileName, 'rb') as f:
        text = ""
        lines = []
        for line in f:
            lines.append(line)
        for i in range((len(lines)-10), len(lines)):
            text += lines[i]
    return text
    #for lines in message - find only todays/errors/etc

message511 = readFile('511.log')
messageEaglei = readFile('eaglei.log')

message = "Last 10 511 Log Results:\n" + message511 + "Last 10 Eagle-i Log Results:\n" + messageEaglei
msg = MIMEText(message)
msg['Subject'] = "Today's recent script log results"
msg['From'] = fromAdd
msg['To'] = toAdd

server = smtplib.SMTP_SSL('smtp.gmail.com',465)
server.set_debuglevel(1)
server.login('email@domain.com', 'app_password')
try:
    server.sendmail(fromAdd, toAdd, msg.as_string())
except Exception as e:
    print e
server.quit()

