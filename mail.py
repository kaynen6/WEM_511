import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

##user settings config file and variables
import config

from_add = config.from_email
to_add = config.to_email
smtp = config.smtp

now = datetime.now()
one_day_ago = now - timedelta(1)

def readFile(fileName):
    with open(fileName, 'rb') as f:
        errors = ""
        error_lines = []
        info_line = ""
        for line in f:
            if "ERROR" in line:
                words = line.split()
                del words[2:len(words)]
                date_str = " "
                date_str.join(words)
                if date_str == " ":
                    break
                date_obj = datetime.strptime(date_str, "%m/%d/%y %I:%M:%S%p")
                if date_obj >= one_day_ago:
                    error_lines.append(line)
        if len(error_lines) >= 10:
            for i in range((len(error_lines)-10), len(error_lines)):
                errors += error_lines[i]
        elif error_lines:
            errors = str(error_lines)
    if errors:
        return errors
    else:
        return None
    #for lines in message - find only todays/errors/etc


message = ""

#get any errors from 511.log file
errors511 = readFile('511.log')
#add text if errors
if errors511:
    message = "Last 10 511 errors logged in the past 24 hours:\n{0}\n".format(errors511)

#get errors from eaglei.log file
errors_eaglei = readFile('eaglei.log')
#add text if errors
if errors_eaglei:
    message += "Last 10 Eagle-i errors logged in the past 24 hours:\n{0}".format(errors_eaglei)

#send an email if there are errors
if len(message) > 0:
    msg = MIMEText(message)
    msg['Subject'] = "Today's recent script log results"
    msg['From'] = from_add
    msg['To'] = to_add

    server = smtplib.SMTP(smtp, 25)
    server.set_debuglevel(1)
    try:
        server.sendmail(from_add, to_add, msg.as_string())
    except Exception as e:
        print e
    server.quit()

