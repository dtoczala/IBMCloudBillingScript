# IBMCloudBillingScript
A script with some basic manipulation of IBM Cloud billing data, collected via IBM Cloud API calls, and dumped to both the screen, and a Cloud Object Storage area.

## Using this Python code

In order to use this you need to have some knowledge of Python.  Not a lot - but some.  You can use this code in a lot of different ways, but I see most people using it in one of two different ways.  I have provided a simple approach for both below.

### Running Local

You can run this code on your local machine, behind your own corporate and/or public firewall(s).  To do so, you will need to either download the Python code in [CSM_IBM_Cloud_Usage.py](https://github.com/dtoczala/IBMCloudBillingScript/blob/master/CSM_IBM_Cloud_Usage.py) or the Python Notebook in [CSM_IBM_Cloud_Usage.ipynb](https://github.com/dtoczala/IBMCloudBillingScript/blob/master/CSM_IBM_Cloud_Usage.ipynb).

If you download the code, **please run it in a Python 3.6 environment** because that is how I run it.  If you download the Python notebook, mae sure that you **run it in a Python 3.6 environment**, and that you have the following dependencies in your Anaconda notebook environment:
- json
- sys
- codecs
- re
- requests
- os
- datetime
- unicodecsv
- botocore.client
- ibm_boto3

_Note: I also reference time, pandas, and numpy in the code.  Those a re leftovers because I reuse code all over the place and I am too lazy to clean up my imports.  You can remove those if you want this code to be clean, or if you want to put it into some sort of container and are looking to keep it as small as possible._

You will need to make sure that you can see the IBM Cloud from where you attempt to run this script.  For those wishing to keep usage statistics local, you can write the CSV file out to local storage instead of the IBM Cloud Object Storage.  You will just need to modify the last line of code in the _dumpToCSV_ routine, and have it write to local file storage instead of Cloud Object Storage (COS).

### Running on the IBM Cloud

You can also elect to run this on the [IBM Cloud](https://cloud.ibm.com).  The easiest way to do this is to download the Python Notebook in [CSM_IBM_Cloud_Usage.ipynb](https://github.com/dtoczala/IBMCloudBillingScript/blob/master/CSM_IBM_Cloud_Usage.ipynb) to your local machine.  You can then import this notebook into a Watson Studio project.  To do so, just follow these steps:
- Open your Watson Studio project
- Click on **_Assets_** tab.
- Select **_New Notebook_**.
- Select the **_From File_** option, and then select the _CSM_IBM_Cloud_Usage.ipynb_ file that is on your local machine.

Once the file has been imported to your project, you will need to select an environment to run this project in.  This is a pretty lightweight script, so you can run it on the _Default Python 3.6 Free_ environment.  I tested it on the _Default Python 3.6 XS_ environment, but that was because I wasn't sure how crazy this thing would get (in terms of CPU horsepower needed).

## Updating the Code

You will need to update this code to have it run correctly with your IBM Cloud account.  You will need to fill in your credentials and key data so the script can access your IBM Cloud account.  So you will need to update this code:

```python
credentials = {
    'IBM_CLOUD_ACCOUNT_ID': 'x50xx4xx0dxxxxxxf8xxxxx1xx1xxxx5',
    'IBM_CLOUD_ACCOUNT_API_KEY': 'xxxxL1ixxxxxFX9fxxxxxxxdgFsxxxxxIDxxxxxxx08S',
    # Account COS creds
    'IAM_COS_SERVICE_ID': 'crn:v1:bluemix:public:iam-identity::a/dxxxxxxxxdc000000000exxxxa0002xx::serviceid:ServiceId-exa00000-7xx0-00xx-bxx6-60006xxxxxx5',
    'IBM_COS_API_KEY_ID': 'Wxxxxxxi00007-x04-0YAxxxxqFwxxxxxxexZ0000004',
    'RESULTS_BUCKET': 'billing-data'
}
```

If you are unfamiliar with identity management and the use of API keys, then check out the [documentation on API Keys on the IBM Cloud](https://cloud.ibm.com/docs/iam?topic=iam-manapikey).  You will need ID's and API keys for both the IBM Cloud account being monitored, and the Cloud Object Storage service being used.  In addition, you will need to specify an existing bucket in Cloud Object Storage where your CSV results files should be stored.

## Code Issues and Problems

This code is perfect (not really).  If you find issues with the code, or have suggestions for improvement, please join this project and open an Issue.  If this tool is useful, I would like to see the wider community support the maintainance of this project.
 
