#!/usr/bin/env python
# coding: utf-8

# # Notebook for pulling account usage data on the IBM Cloud
# [IBM Cloud](https://cloud.ibm.com) is a platform of cloud services that help partners and clients solve a variety business problems.
#
# **NOTE:**
# This notebook was initially based upon a Python notebook provided by Dan Toczala.
#
# Further work to extend some of the concepts, and take advantage of the IBM Cloud usage API (see https://cloud.ibm.com/apidocs/metering-reporting), was done by the folowing contributors:
#
# D. Toczala (dtoczala@us.ibm.com)
#

# In[ ]:


#Import utilities
import json
import sys
import codecs
import re
import time
import requests
from os.path import join, dirname
from datetime import datetime
import unicodecsv as csv
import pandas as pd
import numpy as np
from botocore.client import Config
import ibm_boto3


# In[ ]:


#
# Build a simple class to hold all of the billable data and other supporting data
# coming from all of these different sources.
#
class CloudService:
    def __init__(self, guid):
        self.guid = guid
        self.resource_id = ""
        self.type = ""
        self.name = ""
        self.crn = ""
        self.region = ""
        self.resource_grp = ""
        self.resource_grp_id = ""
        self.org = ""
        self.org_id = ""
        self.space = ""
        self.space_id = ""
        self.cost = 0.0
        self.month = ""
        self.year = ""



# In[ ]:


DEBUG = True
#DEBUG = False
#
UNDERSCORE = '_'
#
# Set Initial IBM Cloud and COS parameters
#
# YOU WILL NEED TO UNCOMMENT THIS CREDENTIALS LIST AND PROVIDE VALID SERVICE CREDENTIALS
# FOR THIS SCRIPT TO RUN PROPERLY
#
#credentials = {
#    'IBM_CLOUD_ACCOUNT_ID': 'x50xx4xx0dxxxxxxf8xxxxx1xx1xxxx5',
#    'IBM_CLOUD_ACCOUNT_API_KEY': 'xxxxL1ixxxxxFX9fxxxxxxxdgFsxxxxxIDxxxxxxx08S',
#    # Account COS creds
#    'IAM_COS_SERVICE_ID': 'crn:v1:bluemix:public:iam-identity::a/dxxxxxxxxdc000000000exxxxa0002xx::serviceid:ServiceId-exa00000-7xx0-00xx-bxx6-60006xxxxxx5',
#    'IBM_COS_API_KEY_ID': 'Wxxxxxxi00007-x04-0YAxxxxqFwxxxxxxexZ0000004',
#    'RESULTS_BUCKET': 'billing-data'
#}

#
# Service endpoints
#
# You may need to change these if you use a different data center
#
endpoints = {
    'IBM_CLOUD_BILLING_ENDPOINT': 'https://billing.cloud.ibm.com',
    'IBM_CLOUD_IAM_ENDPOINT': 'https://iam.cloud.ibm.com',
    'IBM_CLOUD_TAG_ENDPOINT': 'https://tags.global-search-tagging.cloud.ibm.com',
    'IBM_CLOUD_RESCONT_ENDPOINT': 'https://resource-controller.cloud.ibm.com/v2',
    'IBM_CLOUD_RESMGR_ENDPOINT': 'https://resource-manager.bluemix.net/v2/',
    'IBM_CLOUD_REPORTING_PREFIX': '/v4/accounts/',
    'IBM_AUTH_ENDPOINT': 'https://iam.bluemix.net/oidc/token',
#
# Cloud Object Storage Settings
#
    'COS_ENDPOINT': 'https://s3.us-south.cloud-object-storage.appdomain.cloud',

}
#
# Get current date and time
#
myDatetime = datetime.now()
CURRENT_MONTH = datetime.now().strftime('%m')
CURRENT_YEAR  = datetime.now().strftime('%Y')

if (DEBUG):
    print (myDatetime, "   Month - ", CURRENT_MONTH, "   Year - ", CURRENT_YEAR)
myDatetime = re.sub(r'\s',UNDERSCORE,str(myDatetime))
goodDatetime,junk = myDatetime.split('.')
#
# Build filename
#
Billing_file = 'IBM_Cloud_Billing_'+goodDatetime+'.csv'
Billing_path = './'+ Billing_file
#
# Build your common request header, userID for REST calls
#
#REQ_HEADER = {'Authorization':credentials['IBM_CLOUD_ACCOUNT_BEARER_TOKEN']}

USER_ID = credentials['IBM_CLOUD_ACCOUNT_ID']
API_KEY = credentials['IBM_CLOUD_ACCOUNT_API_KEY']
IBM_CLOUD_BILLING_ENDPOINT = endpoints['IBM_CLOUD_BILLING_ENDPOINT']
IBM_CLOUD_REPORTING_PREFIX = endpoints['IBM_CLOUD_REPORTING_PREFIX']


# # Setup Cloud Object Storage (COS)

# In[ ]:


#
# IBM COS interface
#
def __iter__(self): return 0
from ibm_botocore.client import Config
#
cos = ibm_boto3.client(service_name='s3',
    ibm_api_key_id=credentials['IBM_COS_API_KEY_ID'],
    ibm_service_instance_id=credentials['IAM_COS_SERVICE_ID'],
    ibm_auth_endpoint=endpoints['IBM_AUTH_ENDPOINT'],
    config=Config(signature_version='oauth'),
    endpoint_url=endpoints['COS_ENDPOINT'])


# # IBM Cloud Usage API methods
# Define some useful methods to grab data using the IBM Cloud Usage REST API (https://cloud.ibm.com/apidocs/metering-reporting).
#

# In[ ]:


#
# Go and grab a bearer token for an account using their API Key, from a call to the IAM Identity API endpoint
#
def getBearerToken(accountID,APIKey):
    MAX_ATTEMPTS = 3
    tries = 0
    REQ_HEADER = {
        'Content-Type':'application/x-www-form-urlencoded',
        'Accept':'application/json'
        }
    DATA = {
        'grant_type':'urn:ibm:params:oauth:grant-type:apikey',
        'apikey': credentials['IBM_CLOUD_ACCOUNT_API_KEY']
        }
    data = {}
    #
    target_url = endpoints['IBM_CLOUD_IAM_ENDPOINT'] + '/identity/token'
    #
    # Set up your parameters (in a PARAMS dict)
    #
    #PARAMS = {}
    #
    # Try API - only do MAX_ATTEMPTS at most
    #
    while True:
        try:
            # sending get request and saving the response as response object
            r = requests.post(url = target_url, data = DATA, headers = REQ_HEADER)
            if r.status_code == 200:
                # extracting data in json format
                data = r.json()
                if (DEBUG):
                    print ("Got bearer token")
                break
            if tries < MAX_ATTEMPTS:
                tries += 1
                print ("ERROR - Status ",str(r.status_code)," returned from call to IAM Identity management.\n")
                time.sleep(2)
                continue
        except:
            if tries < MAX_ATTEMPTS:
                tries += 1
                time.sleep(2)
                continue
            break
        break
    # end of loop to retry
    #
    if (DEBUG):
        print(json.dumps(data, indent=2))
    token = data['access_token']
    #
    # return token
    #
    return token

# Go and grab the JSON respopnse from a call to the SUMMARY API endpoint for some user selected month and year
# If month and year are not provided, use the current month and year
#
def getAccountSummaryJSON(accountID,token,billYear,billMonth):
    MAX_ATTEMPTS = 3
    tries = 0
    data = {}
    #
    # Determine time period
    #
    if billYear == "":
        billYear = CURRENT_YEAR
    if billMonth == "":
        billMonth = CURRENT_MONTH
    #
    target_url = IBM_CLOUD_BILLING_ENDPOINT + IBM_CLOUD_REPORTING_PREFIX + accountID + '/summary/' + billYear + '-' + billMonth
    #
    # Set up your parameters (in a PARAMS dict)
    #
    PARAMS = {}
    REQ_HEADER = {'Authorization':token}
    #
    # Try API - only do MAX_ATTEMPTS at most
    #
    while True:
        try:
            # sending get request and saving the response as response object
            r = requests.get(url = target_url, params = PARAMS, headers = REQ_HEADER)
            if r.status_code == 200:
                # extracting data in json format
                data = r.json()
                if (DEBUG):
                    print ("Got summary data")
                break
            if tries < MAX_ATTEMPTS:
                tries += 1
                print ("ERROR - Status ",str(r.status_code)," returned from call to /summary.\n")
                time.sleep(2)
                continue
        except:
            if tries < MAX_ATTEMPTS:
                tries += 1
                time.sleep(2)
                continue
            break
        break
    # end of loop to retry
    #
    # return response
    #
    return data

# Go and grab the JSON respopnse from a call to the USAGE API endpoint for some user selected month and year
# If month and year are not provided, use the current month and year
#
def getAccountUsageJSON(accountID,token,billYear,billMonth):
    MAX_ATTEMPTS = 3
    tries = 0
    data = {}
    #
    # Determine time period
    #
    if billYear == "":
        billYear = CURRENT_YEAR
    if billMonth == "":
        billMonth = CURRENT_MONTH
    #
    target_url = IBM_CLOUD_BILLING_ENDPOINT + IBM_CLOUD_REPORTING_PREFIX + accountID + '/usage/' + billYear + '-' + billMonth
    #
    # Set up your parameters (in a PARAMS dict)
    #
    PARAMS = {}
    REQ_HEADER = {'Authorization':token}
    #
    # Try API - only do MAX_ATTEMPTS at most
    #
    while True:
        try:
            # sending get request and saving the response as response object
            r = requests.get(url = target_url, params = PARAMS, headers = REQ_HEADER)
            if r.status_code == 200:
                # extracting data in json format
                data = r.json()
                if (DEBUG):
                    print ("Got usage data")
                break
            if tries < MAX_ATTEMPTS:
                tries += 1
                print ("ERROR - Status ",str(r.status_code)," returned from call to /usage.\n")
                time.sleep(2)
                continue
        except:
            if tries < MAX_ATTEMPTS:
                tries += 1
                time.sleep(2)
                continue
            break
        break
    # end of loop to retry
    #
    # return response
    #
    return data

#
# Go and grab the JSON response from a call to the RESOURCE CONTROLLER API endpoint for some user,
# and return a list of resources
#
def getAccountResourceList(accountID,token):
    MAX_ATTEMPTS = 3
    tries = 0
    return_token = ""
    data = {}
    #
    target_url = endpoints['IBM_CLOUD_RESCONT_ENDPOINT'] + "/resource_instances"

    #
    # Set up your parameters (in a PARAMS dict)
    #
    this_token = "Bearer " + token
    PARAMS = {}
    DATA = {}
    REQ_HEADER = {
        'Authorization':this_token
        }
    #
    # Try API - only do MAX_ATTEMPTS at most
    #
    while True:
        try:
            # sending get request and saving the response as response object
            r = requests.get(url = target_url, headers = REQ_HEADER)
            if r.status_code == 200:
                # extracting data in json format
                data = r.json()
                if (DEBUG):
                    print ("Got resource data")
                break
            if tries < MAX_ATTEMPTS:
                tries += 1
                print ("ERROR - Status ",str(r.status_code)," returned from call to Resource Controller.\n")
                time.sleep(2)
                continue
        except:
            if tries < MAX_ATTEMPTS:
                tries += 1
                time.sleep(2)
                continue
            break
        break
    # end of loop to retry
    #
    # return response
    #
    return data

#
# Go and grab the JSON response from a call to the RESOURCE CONTROLLER API endpoint for some user,
# and return a list of resources
#
def parseAccountResourceList(accountID,token):
    MAX_ATTEMPTS = 3
    tries = 0
    return_token = ""
    data = {}
    #
    target_url = endpoints['IBM_CLOUD_RESCONT_ENDPOINT'] + "/resource_instances"

    #
    # Set up your parameters (in a PARAMS dict)
    #
    this_token = "Bearer " + token
    PARAMS = {}
    DATA = {}
    REQ_HEADER = {
        'Authorization':this_token
        }
    #
    # Try API - only do MAX_ATTEMPTS at most
    #
    while True:
        try:
            # sending get request and saving the response as response object
            r = requests.get(url = target_url, headers = REQ_HEADER)
            if r.status_code == 200:
                # extracting data in json format
                data = r.json()
                if (DEBUG):
                    print ("Got resource data")
                break
            if tries < MAX_ATTEMPTS:
                tries += 1
                print ("ERROR - Status ",str(r.status_code)," returned from call to Resource Controller.\n")
                time.sleep(2)
                continue
        except:
            if tries < MAX_ATTEMPTS:
                tries += 1
                time.sleep(2)
                continue
            break
        break
    # end of loop to retry
    #
    # return response
    #
    return data

#
# Go and grab the JSON response from a call to the RESOURCE CONTROLLER API endpoint for some user,
# and return a list of resources
#
def getAccountResourceGroupList(accountID,token):
    MAX_ATTEMPTS = 3
    tries = 0
    return_token = ""
    data = {}
    #
    target_url = endpoints['IBM_CLOUD_RESCONT_ENDPOINT'] + "/resource_groups?account_id=" + accountID

    #
    # Set up your parameters (in a PARAMS dict)
    #
    this_token = "Bearer " + token
    PARAMS = {}
    DATA = {}
    REQ_HEADER = {
        'Authorization':this_token
        }
    #
    # Try API - only do MAX_ATTEMPTS at most
    #
    while True:
        try:
            # sending get request and saving the response as response object
            r = requests.get(url = target_url, headers = REQ_HEADER)
            if r.status_code == 200:
                # extracting data in json format
                data = r.json()
                if (DEBUG):
                    print ("Got resource group data")
                break
            if tries < MAX_ATTEMPTS:
                tries += 1
                print ("ERROR - Status ",str(r.status_code)," returned from call to Resource Controller.\n")
                time.sleep(2)
                continue
        except:
            if tries < MAX_ATTEMPTS:
                tries += 1
                time.sleep(2)
                continue
            break
        break
    # end of loop to retry
    #
    # return response
    #
    return data


# # Go and grab all of your data
#
# First we get a bearer token from the IAM Identity API - this will be in our header to authenticate all of the following calls.
#
# Then we make a call to get the account summary and the account usage data from the Usage API.
#
#
#

# In[ ]:


#
# Go and grab the monthly usage data for some specified month,
# and print a list of resources and usage costs
#
# Bill year and Bill Month must be two digit numeric strings (i.e. "01", "09", 19", etc.)
#
def getMonthlyUsageList(accountID,apikey,billYear,billMonth):
    #DEBUG = True
    DEBUG=False
    result_array = []
    #
    # Build a simple class to hold all of the billable data and other supporting data
    # coming from all of these different sources.
    #
    class CloudService:
        def __init__(self, guid):
            self.guid = guid
            self.resource_id = ""
            self.type = ""
            self.name = ""
            self.crn = ""
            self.region = ""
            self.resource_grp = ""
            self.resource_grp_id = ""
            self.org = ""
            self.org_id = ""
            self.space = ""
            self.space_id = ""
            self.cost = 0.0
            self.month = ""
            self.year = ""
    #
    AllCloudServices = []
    #
    # Get current date and time
    #
    myDatetime = datetime.now()
    CURRENT_MONTH = datetime.now().strftime('%m')
    CURRENT_YEAR  = datetime.now().strftime('%Y')
    #
    # Determine time period
    #
    if billYear == "":
        billYear = CURRENT_YEAR
    if billMonth == "":
        billMonth = CURRENT_MONTH
    #
    # First go and get a bearer token using your API key - and reset the request header
    #
    IBM_CLOUD_ACCOUNT_BEARER_TOKEN = getBearerToken(accountID,apikey)
    #
    # Reset the default request header
    #
    #REQ_HEADER = {'Authorization':IBM_CLOUD_ACCOUNT_BEARER_TOKEN}
    #
    #
    # First get account summary - current date/time
    #
    #DEBUG=True
    acct_summary_data = getAccountSummaryJSON(USER_ID,IBM_CLOUD_ACCOUNT_BEARER_TOKEN,billYear,billMonth)
    if (DEBUG):
        print ("\n*************************\n")
        print ("Account Summary Data")
        print ("\n**********\n")
        print(json.dumps(acct_summary_data, indent=2))
    #
    # Then get account usage data
    #
    #DEBUG=True
    acct_usage_data = getAccountUsageJSON(USER_ID,IBM_CLOUD_ACCOUNT_BEARER_TOKEN,billYear,billMonth)
    if (DEBUG):
        print ("\n*************************\n")
        print ("Account Usage Data")
        print ("\n**********\n")
        print(json.dumps(acct_usage_data, indent=2))
    #
    # Get Resource Group data
    #
    resource_group_data = getAccountResourceGroupList(USER_ID,IBM_CLOUD_ACCOUNT_BEARER_TOKEN)
    if (DEBUG):
        print ("\n*************************\n")
        print ("Account Resource Group List")
        print ("\n**********\n")
        print(json.dumps(resource_group_data, indent=2))
    #
    # Now go and get service/instance data
    #
    data = getAccountResourceList(USER_ID,IBM_CLOUD_ACCOUNT_BEARER_TOKEN)
    if (DEBUG):
        print ("\n*************************\n")
        print ("Account Resource List")
        print ("\n**********\n")
        print(json.dumps(data, indent=2))
    #
    # Create a dict of Resource Group names, keyed by the Resource Group ID
    #
    resourceNames = {}
    for resGroup in resource_group_data['resources']:
        thisKey = resGroup['id']
        resourceNames[thisKey] = resGroup['name']
    if (DEBUG):
        print (resourceNames)
    #
    # Parse out all of that resource data - we want a list of services objects, with relevant data
    # for each instance
    #
    #DEBUG = True
    for resource in data['resources']:
        a = CloudService(resource['guid'])
        a.type = resource['type']
        a.name = resource['name']
        a.crn = resource['crn']
        a.region = resource['region_id']
        a.resource_grp_id = resource['resource_group_id']
        rgKey = resource['resource_group_id']
        a.resource_grp = resourceNames[rgKey]
        a.resource_id = resource['resource_id']
        a.org = ""
        a.space = ""
        a.cost = 0.0
        a.month = billMonth
        a.year = billYear
        #
        AllCloudServices.append(a)
        if (DEBUG):
            print ("Storing service " + a.name)
            print ("             GUID is " + a.guid)
            print ("             type is " + a.type)
            print ("             name is " + a.name)
            print ("              crn is " + a.crn)
            print ("        region ID is " + a.region)
            print ("Resource group ID is " + a.resource_grp_id)
            print ("      Resource ID is " + a.resource_id)
            print ("    Billable cost is " + str(a.cost))
            print ("")
    #
    # Now loop thru the Account Summary data, and fill in the missing pieces
    #
    for CloudService in AllCloudServices:
        #
        # Find matching resource id
        #
        for accounts in acct_usage_data['resources']:
            #
            # Do we have a match?
            #
            matchId = CloudService.resource_id
            thisId = accounts['resource_id']
            if thisId == matchId:
                #
                # We have a match, save off the cost information
                #
                serviceCost = accounts['billable_cost']
                CloudService.cost = serviceCost
                if (DEBUG):
                    print ("Match found for " + thisId + " named " + CloudService.name + "  Cost of " + str(serviceCost))
            # end loop accounts
        # end loop CloudService
    #
    # Now loop thru the Account Summary data, and we're going to dump
    # all resources with some kind of billable usage
    #
    storageArray = []
    #DEBUG=True
    for CloudService in AllCloudServices:
        #
        # Find any resource ID that has billable use (above $0.01)
        #
        if CloudService.cost > 0.01:
            #
            # Save the name and GUID in an array (so you can sort by name)
            #
            packedName = CloudService.resource_grp + " -- " + CloudService.name + " -- " + CloudService.guid
            storageArray.append(packedName)
            if (DEBUG):
                print ("Saved " + packedName)
    #
    # Sort the results
    #
    storageArray.sort()
    #
    # Now loop thru the sorted storageArray
    #
    for BillableUnit in storageArray:
        #
        # Split out the name and the resource ID
        #
        (thisResourceGroup,thisName,thisID) = BillableUnit.split(" -- ")
        #
        # Make resource group 40 characters long
        #
#        if len(thisResourceGroup) > 40:
#            dispResourceGroup = thisResourceGroup[:40]
#        else:
#            dispResourceGroup = thisResourceGroup
#            while len(dispResourceGroup) < 40:
#                dispResourceGroup = dispResourceGroup + " "
        #
        # Make name 60 characters long
        #
#        if len(thisName) > 60:
#            dispName = thisName[:60]
#        else:
#            dispName = thisName
#            while len(dispName) < 60:
#                dispName = dispName + " "
        #
        # Find resource and billable amount
        #
        for CloudService in AllCloudServices:
            if ((CloudService.guid == thisID) and (CloudService.name == thisName)):
                thisCost = '${:>10.2f}'.format(CloudService.cost)
                thisDate = billMonth + "/" + billYear
#                print (thisDate + "   " + dispResourceGroup + "  " + CloudService.guid + "   " + dispName + " " + thisCost)
#                result_line = (thisDate,dispResourceGroup,CloudService.guid,dispName,thisCost)
                result_line = (thisDate,thisResourceGroup,CloudService.guid,thisName,thisCost)
                result_array.append(result_line)
        #
    return result_array


# In[ ]:


def printResults(resultArray):
    #
    # loop thru entries
    #
    for outputline in resultArray:
        #
        # Grab each field
        #
        (thisDate,thisResourceGroup,thisGuid,thisName,thisCost) = outputline
        #
        # Make resource group 40 characters long
        #
        if len(thisResourceGroup) > 40:
            thisResourceGroup = thisResourceGroup[:40]
        else:
            while len(thisResourceGroup) < 40:
                thisResourceGroup = thisResourceGroup + " "
        #
        # Make name 60 characters long
        #
        if len(thisName) > 60:
            thisName = thisName[:60]
        else:
            while len(thisName) < 60:
                thisName = thisName + " "
        #
        # Print entry
        #
        print (thisDate + "   " + thisResourceGroup + "  " + thisGuid + "   " + thisName + " " + thisCost)
        #
    return True


# In[ ]:


def dumpToCSV(resultArray,csvfilename):
    #
    # Save CSV in local storage
    #
    csvfileOut = './'+ csvFilename
    #
    # Open CSV file for writing
    #
    csvWriter = codecs.open(csvfileOut, 'w', encoding="utf-8-sig")
    #
    # Write header row
    #
    csvWriter.write("Date"+","+"Resource Group"+","+"Resource GUID"+","+"Resource Name"+","+"Cost")
    csvWriter.write("\n")
    #
    # loop thru entries
    #
    for outputline in resultArray:
        #
        # Grab each field
        #
        (thisDate,thisResourceGroup,thisGuid,thisName,thisCost) = outputline
        #
        # Dump entry to CSV file
        #
        csvWriter.write(thisDate+","+thisResourceGroup+","+thisGuid+","+thisName+","+thisCost)
        csvWriter.write("\n")
        #
    #
    # Close CSV file
    #
    csvWriter.close()
    #
    # Write results out to Cloud Object Storage
    #
    cos.upload_file(Filename=csvfileOut,Bucket=credentials['RESULTS_BUCKET'],Key=csvFilename)
    return True


# In[ ]:


#
# MAIN PROGRAM
#
# This sample program will both print and write the usage data to a CSV file out on Cloud
# Object Storage, for the months of August 2019, September 2019 and October 2019.
#
# You can easily modify this to provide billing data over the past year, or some user
# defined window of time.
#
DEBUG=False
#
overall_results =[]
csvFilename = 'Results_'+goodDatetime+'.csv'
#
# Print Header
#
print ("*******************************************************************************************************************************************************************")
print ("Date      Resource Group                            Resource GUID                          Resource Name                                                Cost")
print ("*******************************************************************************************************************************************************************")
#
# Get usage for August 2019
#
results = getMonthlyUsageList(USER_ID,API_KEY,"2019","08")
for entry in results:
    overall_results.append(entry)
status = printResults(results)
#
# Get usage for September 2019
#
results = getMonthlyUsageList(USER_ID,API_KEY,"2019","09")
for entry in results:
    overall_results.append(entry)
status = printResults(results)
#
# Get usage for October 2019
#
results = getMonthlyUsageList(USER_ID,API_KEY,"2019","10")
for entry in results:
    overall_results.append(entry)
status = printResults(results)
#
# Dump ALL results out to a CSV file
#
csvFilename = 'Results_'+goodDatetime+'.csv'
status = dumpToCSV(overall_results,csvFilename)
#
# end


# In[ ]:
