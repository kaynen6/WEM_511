import smtplib
from email.mime.text import MIMEText

fromAdd = 'email@domain.com'
toAdd = 'email@domain.com
def readFile(fileName):
    with open(fileName, 'rb') as f:
        text = ""
        lines = []
        for line in f:
            if "INFO" in line and "features" in line:
                lines.append(line)
            elif "ERROR" in line:
                lines.append(line)
        for i in range((len(lines)-10), len(lines)):
            text += lines[i]
    return text
    #for lines in message - find only todays/errors/etc

message511 = readFile('511.log')
messageEaglei = readFile('eaglei.log')

message = "Last 10 511 Log Results:\n" + message511 + "\nLast 10 Eagle-i Log Results:\n" + messageEaglei
msg = MIMEText(message)
msg['Subject'] = "Today's recent script log results"
msg['From'] = fromAdd
msg['To'] = toAdd

server = smtplib.SMTP('smtpout.domain.com', 25)
server.set_debuglevel(1)
try:
    server.sendmail(fromAdd, toAdd, msg.as_string())
except Exception as e:
    print e
server.quit()

