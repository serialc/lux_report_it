import sys
import os
import requests
from bs4 import BeautifulSoup
import time

"""
This script retrieves a URL (with GET), retrieves the hidden inputs,
then POSTs a request (to the same URL) using the defined hidden inputs
and retrieves reports.
"""

#### Constants ####
# our site of interest
site = "https://www.vdl.lu/fr/la-ville/participez-vous-aussi/report-it-signalez-un-incident"
# but the data retrieval is actually in a frame from a separate url
qurl = "https://reportit.vdl.lu/frame/search.php"

mode = "endless"
verbose = True
sleep_duration = 60 

# raw data is stored here
raw_data_path = "../data/raw/"
# log of closed but removed reports
removed_reports_path = "../data/removed_closed_reports.txt"

# get the list of report ids - we're looking for the max id
replist = os.listdir("../data/raw/")
report_id = max([int(rid) for rid in replist])

# continue retrieval from there until the following maximum
max_report_scanning = 90
max_report_scanning = 29215

#### Command line arguments ####
if len(sys.argv) >= 2 and sys.argv[1] == "one":
    sleep_duration = 2
    verbose = False
    mode = "one"

#### PART 1 ####

# start a session
s = requests.session()

# define headers
customheaders = {
    'get': '/frame/search.php HTTP/1.1',
    'host': 'reportit.vdl.lu',
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache'
                }


# get the page that we want to query
pageres = s.get(qurl, headers=customheaders)

# We need some of the hidden elements from the form for the query
# Extract with BS4
soup = BeautifulSoup(pageres.text, 'html.parser')

# we want the second input [1]
sid_inputs = soup.find_all('input')[1]

# extract the needed values
sid = sid_inputs.get('id')
sidval = sid_inputs.get('value')

#### PART 2 ####

# Sequentially scan to see if reports exist
while report_id < max_report_scanning:
    report_id += 1
    if verbose:
      print(f"Attempting to retrieve report id {report_id}.", end=" ")

    # where we will save the data once retreived
    report_filename = raw_data_path + str(report_id)

    # make sure this report isn't already downloaded, skip if so
    if os.path.exists(report_filename):
        if verbose:
            print("Downloaded report already exists. Skipped.")
        continue

    # the session sends the necessary cookies generated by the earlier request
    datares = s.post(qurl, data={"search_id": report_id, sid: sidval}, headers=customheaders)

    # look at the retrieved data
    soup = BeautifulSoup(datares.text, 'html.parser')

    # check if it's the correct header types, there are 3 know types
    # bg-danger: Report not found -> skip
    # bg-success: Report no longer exists -> add id to log
    # bg-primary: Exists and has details -> save the data
    cardheader = soup.find('div', class_='card-header')
    # just get the class of interest
    cardheader = cardheader.get("class")[2]

    # handle the return report type
    if cardheader == "bg-danger":
        errmsg = soup.find('div', class_=cardheader).contents[0]
        if verbose:
            print(f"Received 'not found' message: {errmsg}")
        time.sleep(sleep_duration)
        continue

    if cardheader == "bg-success":
        errmsg = soup.find('div', class_=cardheader).contents[0]
        if verbose:
            print(f"Received 'removed' message: {errmsg}")
        with open(removed_reports_path, 'a') as rf:
            rf.write(str(report_id) + ",")
        time.sleep(sleep_duration)
        continue

    if cardheader == "bg-primary":
        # extract, clean up, get the text
        status, subdate = soup.body.find_all('td')
        status = status.contents[0].contents[0]
        subdate = subdate.contents[0]

        data = soup.find_all('div', class_='container-lg')[0]

        with open(report_filename, 'w') as fh:
            fh.write(str(data))
            if verbose:
                print("Saved data.", end=" ")

        if verbose:
            print(f"Report created on {subdate} has status '{status}'.")

        if mode == "one" and verbose == False:
            exit("Finished retrieving one valid report.")

        # get ready for next query
        time.sleep(sleep_duration)

        continue

    print(soup)
    exit(f"ERROR - Received an unexpected report header '{cardheader}'. See above.")

if verbose:
    print(f"Finished scanning up to max_report_scanning limit of {max_report_scanning}.")
