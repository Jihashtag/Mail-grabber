#!/usr/bin/python

import sys, time, os, requests, textract, re
from threading import Thread, RLock

class error():
	status_code = -1
	text = ""

lock = RLock()
threadnb = 0
maxthread = 20000
for value in sys.argv:
	try:
		a = int(value)
	except:
		a = 0
	if a:
		maxthread = int(value)

print "Maximum Thread : " + str(maxthread)

class pagesThread(Thread):

	def __init__(self, begin, site, pages, debug, http, allfound):
		Thread.__init__(self)
		self.begin = begin
		self.site = site
		self.pages = pages
		self.debug = debug
		self.http = http
		self.allfound = allfound
		return

	def run(self):
		listpages(self.begin, self.site, self.pages, self.debug, self.http, self.allfound)
		return


def listpages(begin, site, pages, debug, http, allfound):
	if re.findall(r'.*\.php/.*\.php', site):
		return
	headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0', 'referer': begin}
	with lock:
		pages.append(site)
		try:
			page = requests.get(site,headers=headers)
		except:
			page = error
	printer = ""
	global threadnb
	if debug:
		printer += site + "\n"
	if page.status_code != 200:
		if debug:
			printer += "La page n'est pas accessible (" + str(page.status_code) + ")"
			print printer
		return
	if site is begin:
		site = site + '/'
	if re.findall(r'.*\.\.*/.*[a-zA-Z0-9\_\-]+\.[a-z]+$', site) and not ".php" in site and not ".html" in site:
		tmp = re.findall(r'[a-zA-Z0-9\.\_\-]+$', site)
		tmp = tmp[0]
		textfile = open(tmp, "a")
		textfile.write(page.text.encode('utf-8'))
		textfile.close()
		page = error
		page.text = textract.process('./' + tmp)
		os.remove(tmp)
	base = re.findall(r'base href=.*/>', page.text)
	if base:
		base = re.findall(r'[\"\'].*[\"\']', base[0])
		base = base[0][1:][:-1]
		if base.endswith('/'):
			base = base[:-1]
	if site in base:
		base = begin
	allpages = re.findall(r'href=[\'\"][a-zA-Z/0-9\-_:.]+[\"\']', page.text)
	allpages2 = re.findall(r'href=[\'\"][a-zA-Z/0-9\-_\.]+.php[a-zA-Z?/=&\.0-9\-\_]*[\"\']', page.text)
	if debug and allpages2:
		printer+= "Erreur: page mal formee" + "\n"
	allpages = allpages + allpages2
	if debug and not allpages:
		printer += "Erreur: Pas de liens dans la page" + "\n"
	mail = {}
	keypop = []
	mail[site] = re.findall(r'[a-zA-Z0-9\.]+@[a-zA-Z0-9\.]+\.[a-zA-Z0-9\.]+', page.text)
	if mail[site]:
		with lock:
			allfound[site] = re.findall(r'[a-zA-Z0-9\.]+@[a-zA-Z0-9\.]+\.[a-zA-Z0-9\.]+', page.text)
	else:
		mail.pop(site)
	if debug:
		for key in mail:
			printer+= "Trouve sur :" + key + "\n"
			for value in mail[key]:
				printer+= value + "\n"
		printer += "[" + str(len(mail)) +"] Mails ont ete trouves" + "\n" + "[" + str(len(allpages)) +"] Liens ont ete trouves" + "\n"
		print printer
		sys.stdout.flush()
	v = 0
	listpagers = []
	while v < len(allpages):
		value = allpages[v]
		if not http:
			if not '.css' in value and not '.jpg' in value and not '.png' in value and not '.js' in value and not 'favicon' in value and not '//' in value and value != 'href="/"' and value != 'href="./"' and value != 'href="."':
				if begin.endswith('/'):
					begin = begin[:-1]
				if base and value[6] == '/':
					current = base + value[6:][:-1]
				elif base:
					current = base + '/' + value[6:][:-1]
				elif value[6] == '/':
					current = begin + value[6:][:-1]
				else:
					current = begin + '/' + value[6:][:-1]
				if not current in pages:
					if threadnb < maxthread:
						t = pagesThread(begin, current, pages, debug, http, allfound)
						try:
							t.start()
							threadnb += 1
							listpagers.append(t)
						except:
							listpages(begin, current, pages, debug, http, allfound)
					else:
						listpages(begin, current, pages, debug, http, allfound)
		elif begin in value:
				current = value[6:][:-1]
				if not current in pages:
					if threadnb < maxthread:
						t = pagesThread(begin, current, pages, debug, http, allfound)
						try:
							t.start()
							threadnb += 1
							listpagers.append(t)
						except:
							listpages(begin, current, pages, debug, http, allfound)
					else:
						listpages(begin, current, pages, debug, http, allfound)
		else:
			if not '.css' in value and not '.jpg' in value and not '.png' in value and not '.js' in value and not 'favicon' in value and value != 'href="/"' and value != 'href="./"':
				if begin[-1] == '/':
					begin[:-1]
				if '://' in value:
					current = value[6:][:-1]
				elif '//' in value:
					current = 'http:' + value[6:][:-1]
				elif base and value[6] == '/':
					current = base + value[6:][:-1]
				elif base:
					current = base + '/' + value[6:][:-1]
				elif value[6] == '/':
					current = begin + value[6:][:-1]
				else:
					current = begin + '/' + value[6:][:-1]
				if not current in pages:
					if threadnb < maxthread:
						t = pagesThread(begin, current, pages, debug, http, allfound)
						try:
							t.start()
							threadnb += 1
							listpagers.append(t)
						except:
							listpages(begin, current, pages, debug, http, allfound)
					else:
						listpages(begin, current, pages, debug, http, allfound)
		allpages = filter(lambda a: a != value, allpages)
	for value in listpagers:
		value.join()
		threadnb -= 1

site = sys.argv[1]
http = re.match('http', site)
if not http:
	site = "http://" + site
begin = site
if len(sys.argv) >= 3 and "debug" in sys.argv[2]:
	debug = True
else:
	debug = False

if len(sys.argv) >= 3 and "follow" in sys.argv[2]:
	http = True
else:
	http = False
if http and len(sys.argv) >= 4 and "debug" in sys.argv[3]:
	debug = True
pages = []
allfound = {}
load = True
class silent(Thread):

	def __init__(self):
		Thread.__init__(self)

	def run(self):
		global allfound
		global pages
		while load:
			time.sleep(5)
			if not load:
				return
			printer = "\n[" + str(len(pages)) +"] Pages parcourues\n"
			print printer
			sys.stdout.flush()
			time.sleep(10)
			if not load:
				return
			time.sleep(5)
			if not load:
				return
			printer = "\n[" + str(len(pages)) +"] Pages parcourues"
			printer += "\n" + "Liste des mails :\n"
			for key in allfound:
				printer +=  "\n	Trouve sur :" + key + "\n"
				for value in allfound[key]:
					printer += value+";"
			print printer
			sys.stdout.flush()
print
if not debug:
	s = silent()
	s.start()
listpages(begin, site, pages, debug, http, allfound)
load = False
print
print
print "Liste des mails :"
for key in allfound:
	print "	Trouve sur :" + key
	for value in allfound[key]:
		print value
print
print "Pages parcourues :"
for value in pages:
	print value
print "\n[" + str(len(pages)) +"] Pages parcourues"
