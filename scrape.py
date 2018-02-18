from bs4 import BeautifulSoup
import urllib.request
import re
import os
import sys
import time
from time import gmtime, strftime
import json
import gspread
from oauth2client.client import SignedJwtAssertionCredentials
import traceback

def authoriseGoogle(creds):
	json_key = json.load(open(creds)) # json credentials you downloaded earlier
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'].encode(), scope) # get email and key from creds
	file = gspread.authorize(credentials) # authenticate with Google		
	
	return file
		
def first_empty_row(sheet):
    all = sheet.get_all_values()
    row_num = 1
    consecutive = 0
    for row in all:
        flag = False
        for col in row:
            if col != "":
                flag = True
                break
        if flag:
            consecutive = 0
        else:
            consecutive += 1

        if consecutive == 2:
            return row_num - 1
        row_num += 1
    return row_num

def getName(myDict):
	advertName = re.findall(myDict["namePattern"], str(myDict["pricingMeta"]))[0]
	
	return advertName

def getPrice(myDict):
	advertPrice = re.findall(myDict["pricePattern"], str(myDict["pricingMeta"]))[0]
	
	return advertPrice

def getLink(myDict):
	advertLink = re.findall(myDict["linkPattern"], str(myDict['currentAdvert']))[0]
	advertLink = advertLink.encode('ascii', 'ignore').decode('ascii')
	return advertLink
	
def scanListItem(myDict):
	myDict["pricingMeta"] = myDict['currentAdvert'].find_all("span",  { "class" : "listing-price" })

	myDict["advertName"] = getName(myDict)
	myDict["advertPrice"] = getPrice(myDict)
	myDict["advertLink"] = getLink(myDict)
	n=0
	
	myKey = myDict["advertName"] + myDict["advertLink"]
	myKey = str(myKey.encode(sys.stdout.encoding, errors='replace'))
	#print(myKey)
	if not myDict["advertName"] in myDict["viewedAdverts"] and not myKey in myDict["previousAdverts"]:	
		myDict["viewedAdverts"].append(myKey)
		myDict["previousAdvertsLog"].write(myKey+"\n")
		
		if float(myDict["advertPrice"]) <= myDict["maxPrice"]:
			for titleExcludeKWWords in myDict["titleExcludeKW"]:
				if titleExcludeKWWords.upper() in str(myDict["advertName"]).upper():
					n=n+1
					
			if n == 0:
				openAdvert(myDict)

def openAdvert(myDict):

	writeToLog(myDict["logfile"],myDict["protocol"] + "://" + myDict["hostName"] + myDict["advertLink"])
	print(myDict["protocol"] + "://" + myDict["hostName"] + myDict["advertLink"])
	
	page = urllib.request.urlopen(myDict["protocol"] + "://" + myDict["hostName"] + myDict["advertLink"])

	soup = BeautifulSoup(page, "html.parser", from_encoding="utf-8")
	description = soup.find_all("p", { "class" : "ad-description" })
	stringDescription = description[0].encode()
	
	n=0	
	for keyWord in myDict["descriptionKW"]:
		if keyWord.upper() in stringDescription.decode('utf8').upper():
			n=n+1
				
	if n > 0:
		writeAdvertToFile(myDict)
	
def writeAdvertToFile(myDict):
	priceColumn = "A"
	titleColumn = "B"
	linkColumn = "C"
	row_num = str(first_empty_row(myDict["googleSheet"]))
	
	currentRange = priceColumn + row_num
	myDict["googleSheet"].update_acell(currentRange, myDict["advertPrice"])
	
	currentRange = titleColumn + row_num
	myDict["googleSheet"].update_acell(currentRange, myDict["advertName"])

	currentRange = linkColumn + row_num
	myDict["googleSheet"].update_acell(currentRange, myDict["protocol"] + "://" + myDict["hostName"] + myDict["advertLink"])
	
	myDict["savedAdverts"].write(myDict["advertPrice"] + "," + myDict["advertName"] + "," + myDict["protocol"] + "://" + myDict["hostName"] + myDict["advertLink"] +"\n")
			
def createFile(name):
	if not os.path.isfile(name):
		f = open(name,"w+")
	else:
		f = open(name,"a+")
		
	return f

def writeToLog(file,message):
	file.write(message + "\n")
	file.flush()
	
def runShpock(metaDict, sharedDict):
	myDict = dict()
	myDict["googleSheet"] = sheet
	intialSearch = "https://en.shpock.com/q/laptop/"
	page = urllib.request.urlopen(intialSearch)
	soup = BeautifulSoup(page, "html.parser")
	mydivs = soup.find_all("div", { "class" : "items-wrapper-bg" })
	
	print(str(mydivs))
	
def runGumtree(metaDict, sharedDict):
	myDict = dict()
	myDict["hostName"] = r"www.gumtree.com"
	myDict["protocol"] = r"https"
	myDict["searchLocation"] = r"London"
	myDict["category"] = metaDict["category"]
	myDict["maxPrice"] = metaDict["maxPrice"]
	myDict["descriptionKW"] = metaDict["descriptionKW"]
	myDict["titleExcludeKW"] = metaDict["titleExcludeKW"] 
	myDict["viewedAdverts"] = []
	myDict["previousAdvertsLog"] = createFile(r"previousAdverts.txt")
	myDict["savedAdverts"] = createFile(r"savedAdverts.txt")
	myDict["logfile"] = sharedDict["logfile"]
	myDict["googleSheet"] = sharedDict["sheet"]
	myDict["namePattern"] =r'<meta content=(.*?) itemprop=\"name\"'
	myDict["pricePattern"] = r'<meta content=\"(.*?)\" itemprop=\"price\"'
	myDict["linkPattern"] = r'listing-link\" href=\"(.*?)\" itemprop=\"url'
	
	with open(r"previousAdverts.txt") as f:
		myDict["previousAdverts"] = f.readlines()
		myDict["previousAdverts"] = [x.strip() for x in myDict["previousAdverts"]]
		
	intialSearch = myDict["protocol"] + "://" + myDict["hostName"] + "/search?featured_filter=false&urgent_filter=false&sort=date&search_scope=false&photos_filter=false&search_category=" + myDict["category"] + "&q=&search_location=" + myDict["searchLocation"]
	page = urllib.request.urlopen(intialSearch)

	soup = BeautifulSoup(page, "html.parser")
	mydivs = soup.find_all("ul", { "class" : "list-listing-mini" })

	for div in mydivs:
		adverts = div.find_all('article')
		for myDict['currentAdvert'] in adverts:
			scanListItem(myDict)
	
	myDict["previousAdvertsLog"].close()
	myDict["savedAdverts"].close()

def main():
	sharedDict = dict()
	sharedDict["logfile"] = createFile(r"output.log")
	
	try:
		iterations = int(sys.argv[1])
		pacing = int(sys.argv[2])
		
		pcDict = dict()
		pcDict["category"] = "desktop-workstation-pcs"
		pcDict["maxPrice"] = 280
		pcDict["descriptionKW"] = ["i5", "i7", "ssd", "ryzen", "970", "1050", "1060"]
		pcDict["titleExcludeKW"] = ["hp", "dell", "lenovo", "q6600", "q9550", "apple", "Fujitsu","mac","packard","hewlett"]

		pcHighDict = dict()
		pcHighDict["category"] = "desktop-workstation-pcs"
		pcHighDict["maxPrice"] = 500
		pcHighDict["descriptionKW"] = ["1060", "1070", "1080"]
		pcHighDict["titleExcludeKW"] = ["hp", "dell", "lenovo", "q6600", "q9550", "apple", "Fujitsu","mac","packard","hewlett"]
		
		laptopDict = dict()
		laptopDict["category"] = "laptops"
		laptopDict["maxPrice"] = 500
		laptopDict["descriptionKW"] = ["970", "1060", "1050", "xps", "surface book"]
		laptopDict["titleExcludeKW"] = ["duo","mac","packard","hewlett"]
		
		gtxDict = dict()
		gtxDict["category"] = "video-cards-sound-cards"
		gtxDict["maxPrice"] = 310
		gtxDict["descriptionKW"] = ["1070"]
		gtxDict["titleExcludeKW"] = ["duo","mac","packard","hewlett"]
		
	except Exception as e:
		writeToLog(sharedDict["logfile"],traceback.format_exc())
		
	for x in range(0, iterations):
	
		try:
			file = authoriseGoogle('creds.json')
			sharedDict["sheet"] = file.open("gumtreeAdverts").sheet1
		
			writeToLog(sharedDict["logfile"],strftime("%Y-%m-%d %H:%M:%S", gmtime()))
			print(strftime("%Y-%m-%d %H:%M:%S", gmtime()))

			sharedDict["sheet"].update_acell("D1", strftime("%Y-%m-%d %H:%M:%S", gmtime()))
		
			runGumtree(pcDict,sharedDict)
			runGumtree(pcHighDict,sharedDict)
			runGumtree(laptopDict,sharedDict)
			runGumtree(gtxDict,sharedDict)
			
		except Exception as e:
			writeToLog(sharedDict["logfile"],traceback.format_exc())
		
		#runShpock(laptopDict)
		#if iterations <= 1:
		time.sleep(pacing) 
	
	sharedDict["logfile"].close()
	
if __name__ == "__main__": 
	main()
