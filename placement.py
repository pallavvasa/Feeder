'''
Author: Pallav Vasa
There could have been many ways to implement this thing and this is one of them.
'''

import urllib2, re, logging, time, signal, sys
from BeautifulSoup import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Header import Header
from email.Utils import formataddr
from smtplib import SMTP

def loadLastId():
	# File to load the lastId e.g., a file containing only: 674
	f = open('public_html/lastId','r')
	lastId = f.read()
	f.close()
	return re.search("\d+",lastId).group(0)

def loadConfig():
	# A config file with your ldap username and password
	f = open('placement.config','r')
	ldap = f.read().split('\n')
	f.close()
	return ldap

def updateLastId():
	global lastId
	# As explained above
	f = open('public_html/lastId','w')
	f.write(lastId)
	f.close()

def beforeShutdown(ab,cd):
	updateLastId()
	logger.info("lastId: "+lastId+" before shutdown "+str(ab)+" "+str(cd))
	sys.exit(1)

def filterPosts(post):
	keywords = ["ppt","workshop","regist","form","elec","ee"]
	return any(word in post.lower() for word in keywords)

def fetchBlog():
	global lastId
	while True:
		try:
			# Placement blog link
			contentObj = urllib2.urlopen("http://placements.iitb.ac.in/blog","",3)
			break
		except Exception, e:
			logger.info("Problem with urlopen: "+ str(e))
	content = contentObj.read()

	# Parse the data
	regExp = re.compile("<div class=\"post-(\d+) post type-post status-publish format-standard hentry (.*)\" id=\"post-\d+\">")
	postIds = regExp.findall(content)
	
	# Check for update
	newIds = []
	for k in postIds:
		if k[0] <= lastId:
			break
		newIds += [k[0]]

	# Report Updates if any
	if len(newIds) > 0:
		logger.info("Update Found: "+str(newIds))
		return newIds
	else:
		return None

def sendMail(sub,body,recipients):
	global ldap
	# IITB SMTP server
	SMTPserver = "smtp-auth.iitb.ac.in"
	# sender of the mail (Details removed)
	sender = formataddr(("Placements","I AM THE SENDER (email id offcourse)"))

	msg = MIMEMultipart('alternative')
	msg['Subject'] = "[PB]: "+sub
	msg['From'] = sender
	msg['To'] = ",".join(recipients)

	# Record the MIME types of both parts - text/plain and text/html.
	part2 = MIMEText(body, 'html')

	# Attach parts into message container.
	# According to RFC 2046, the last part of a multipart message, in this case
	# the HTML message, is best and preferred.
	msg.attach(part2)

	# Send the message via local SMTP server.
	try:
		conn = SMTP(SMTPserver)
		conn.set_debuglevel(False)
		conn.starttls()
		conn.login(ldap[0],ldap[1])
		try:
			conn.sendmail(sender,recipients,msg.as_string())
		finally:
			conn.close()
	except Exception, exc:
		logger.error("Mail Send Failed: " + str(exc))


def mainFunc():
	global lastId
	# group1 is the set of people who get the filtered mails
	group1 = ["I USE GOOGLE GROUPS"]
	# group2 gets all the mails
	group2 = ["VAS WAS HERE"]

	try:	
		while True:
			Ids = fetchBlog()
			if Ids == None:
				time.sleep(100)
				continue
			
			posts = []
			for k in Ids:
				content = urllib2.urlopen("http://placements.iitb.ac.in/blog/?p="+k).read()

				# Parse
				soup = BeautifulSoup(content, convertEntities=BeautifulSoup.HTML_ENTITIES)
				posts += [str(soup.find('div',id='post-'+k))]
			
			for post in posts:
				sub = re.search("<h2>(.*)</h2>",post).group(1)
				body = re.search("<div class=\"entry\">(.*)</div>.*</div>",post,re.DOTALL).group(1)
				if not filterPosts(post):
					sendMail(sub,body,group2)
					logger.info("Post Filtered")
				else:
					sendMail(sub,body,group2)
					sendMail(sub,body,group1)
					logger.info("Mail Sent to group")
			
			lastId = Ids[0]
			updateLastId()
			time.sleep(100)
	except Exception, exc:
		logger.error("Udi baba: " + str(exc))
	except KeyboardInterrupt:
		logger.error("You stopped me")

logger = logging.getLogger('placement')
# Logs are essential part
hdlr = logging.FileHandler('public_html/placement.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

logger.info("-------------")
logger.info("MyApp started")
logger.info("-------------")

for i in [x for x in dir(signal) if x.startswith("SIG")]:
	try:
		signum = getattr(signal,i)
		if signum>0:
			signal.signal(signum,beforeShutdown)
	except RuntimeError,m:
		logger.error("Skipping %s"%i)

ldap = loadConfig()
lastId = loadLastId()
mainFunc()
