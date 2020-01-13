######## INFORMATION ########
# 
# BB2ASM 
# This program will use the Blackbaud API to create the appropriate users, classes,
# and lists in Apple School Manager.
#
# Jared Katzman (jared.katzman@coloradoacademy.org)
#
# This program incorporates code from SKY API Authentication/Query Scripts
# Mitch Hollberg (mhollberg@gmail.com, mhollberg@cfgreateratlanta.org)
#
#


######## INSTRUCTIONS ########
# 
# Python 3.7+ is required.
#
# You will need to install paramiko on your computer for
# this script to work (https://github.com/paramiko/paramiko)
#
# Copy the sample configuration file bbconfig.sample.py to bbconfig.py
# and fill in any necessary fields.
#
# The first time you run this script use the following command:
#   python3 bb2asm.py --authorize
#
# This will generate a new Blackbaud API token.
#
# For subsequent runs, use the following command:
#   python3 bb2asm.py
#
# The processed files and zip file will be exported to the same path as the script.
# If sendtoasm is set to True the script will attempt to send the processed files
# to the Apple School Manager sftp server.
#
# The README file contains additional information for configuring Blackbaud lists


import requests
import json
import time
import csv
import uuid		
import os
import argparse
import zipfile
import paramiko
import bbconfig as cfg    #configuration file

# SFTP Log file
paramiko.util.log_to_file('/tmp/paramiko.log')

def get_initial_token():
    """
    Execute process for user to authenticate and generate an OAUTH2
     token to the SKY API
     Mitch Hollberg (mhollberg@gmail.com /mhollberg@cfgreateratlanta.org)
    :return:
    """
    
    if (cfg.verbose_mode):
        print("Generating initial token.") 
    
    # step A - simulate a request from a browser on the authorize_url:
    # will return an authorization code after the user is
    # prompted for credentials.

    authorization_redirect_url = cfg.AUTHORIZE_URL + \
                                 '?response_type=code&client_id=' + \
                                 cfg.CLIENT_ID + '&redirect_uri=' \
                                 + cfg.CALLBACK_URI

    print("Paste the following url in a web browser and click Authorize. "
          "It will redirect you to a blank website with the url"
          " 'https://127.0.0.1/?code=xxxx'. Copy the value of the code (after the '=' sign). "
          "Paste that code into the prompt below.")
    print("---  " + authorization_redirect_url + "  ---")
    authorization_code = input('Paste code here: ')

    # STEP 2: Take initial token, retrieve access codes and floater token
    ref_token_getter = requests.post(
        url='https://oauth2.sky.blackbaud.com/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data={'grant_type': 'authorization_code',
              'code': authorization_code,
              'client_id': cfg.CLIENT_ID,
              'client_secret': cfg.CLIENT_SECRET,
              'redirect_uri': cfg.CALLBACK_URI}
    )

    tokens_dict = dict(json.loads(ref_token_getter.text))
    for key, value in tokens_dict.items():
        print(f'{key}: {value}')


    refresh_token = tokens_dict['refresh_token']
    access_token = tokens_dict['access_token']

    with open(cfg.TOKEN_FILE, 'w') as f:
        f.write(access_token)

    with open(cfg.REFRESH_TOKEN_FILE, 'w') as f:
        f.write(refresh_token)

    return ref_token_getter.status_code


def get_local_token(token_file=cfg.TOKEN_FILE):
    """
    Read the file storing the latest access token
    :return: value of current authentication token
    """
    with open(token_file, 'r') as f:
        current_token = f.readline()

    return current_token


def token_refresh(refresh_token_file=cfg.REFRESH_TOKEN_FILE,
                  token_file=cfg.TOKEN_FILE):
    """
    Generates a new OAUTH2 access token and refresh token using
    the current (unexpired) refresh token. Writes updated tokens
    to appropriate files for subsequent reference
    :param refresh_token_file: filepath of file storing refresh token
    :param token_file: filepath of file storing access token
    :return: Tuple containing (return_code, access_token, refresh_token)
    """
    if (cfg.verbose_mode):
        print("Refreshing token.") 

    with open(refresh_token_file, 'r') as f:
        refresh_token = f.readline()

    with open(cfg.TOKEN_FILE, 'r') as f:
        current_token = f.readline()

        ref_token_call = requests.post(
            url='https://oauth2.sky.blackbaud.com/token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'refresh_token',
                  'refresh_token': refresh_token,
                  'client_id': cfg.CLIENT_ID,
                  'client_secret': cfg.CLIENT_SECRET,
                  }
        )

    if (cfg.verbose_mode):
        print(f'Token Refresh call return code: {ref_token_call.status_code}')
    
    if (ref_token_call.status_code != 200):
        print(f'ERROR: {status}: response code is {ref_token_call.status_code}')
        exit()
 
    tokens_dict = dict(json.loads(ref_token_call.text))
    refresh_token = tokens_dict['refresh_token']
    access_token = tokens_dict['access_token']

    with open(token_file, 'w') as f:
        f.write(access_token)

    with open(refresh_token_file, 'w') as f:
        f.write(refresh_token)

    return (ref_token_call.status_code, access_token, refresh_token)


def getapi_bblegacylist(current_token, list_id):
    """
    Get Blackbaud Legacy List

    :param current_token:
    :param list_id:  Blackbaud list id
    :return: JSON Blackbaud Legacy List
    """

    url='https://api.sky.blackbaud.com/school/v1/legacy/lists/' + list_id
    params = {'HOST': 'api.sky.blackbaud.com'}

    status = 'Initial Value'

    if (cfg.verbose_mode):
        print("Getting Blackbaud Legacy List " + list_id + ".") 

    while status != 200 or url != '':
        time.sleep(.2)  # SKY API Rate limited to 5 calls/sec

        headers = {'Bb-Api-Subscription-Key': cfg.SUBSCRIPTION_KEY,
                   'Authorization': 'Bearer ' + current_token}

        response = requests.get(url=url,
                                params=params,
                                headers=headers)
        status = response.status_code


        if status == 400:
            # Print HTML repsonse and exit function with empty return
            print(f'ERROR: {status}: {response.text}')
            return df_out

        if status == 403:   # OUT OF API QUOTA - Quit
            # Print HTML repsonse and exit function with empty return
            print(f'ERROR: {status}: {response.text}')
            print(f'You\'re out of API Quota!')
            exit()
            return None

        if status != 200:
            if (cfg.verbose_mode):
                print("Invalid status.  Refresh token.") 
            refresh_status, current_token, _ = token_refresh()
            continue

        if status == 200:
            if (cfg.verbose_mode):
                print("Retrieving JSON Response.") 
            df_out = json.loads(response.text)
            return df_out


def create_list(jsondata):
    """
    Create Python List

    :param jasondata: Blackbaud Legacy List JSON
    :return: Python List
    """


    if (cfg.verbose_mode):
        print("Creating list from JSON Response.") 

    # put the data in a better format
    result = []
    jsondata = jsondata['rows']
    for line in jsondata:
        row = {}
        for entry in line['columns']:
            if 'value' in entry:
                row.update({entry['name'].strip() : entry['value'].strip()})
            else:
                row.update({entry['name'].strip() : ''})
        result.append(row)
    return result


def write_csv(bb_list, asm_csv, outfieldnames):
    """
    Write CSV File

    :param bb_list: Python List
    :param asm_csv:  Name of CSV File to Create
    :param outfieldnames: Fields to Include in CSV
    :return: JSON Blackbaud Legacy List
    """

    if (cfg.verbose_mode):
        print("Creating csv " + asm_csv + ".") 
        
    with open(asm_csv, 'w', encoding='utf-8') as outfile:
        csvwriter = csv.DictWriter(outfile, fieldnames=outfieldnames)
        csvwriter.writeheader()
				
        for row in bb_list:
		
            # rosters file does not have location id, but needs a random roster_id created
            if asm_csv != cfg.asm_rosters_csv:
                row['location_id'] = cfg.asm_location
            else:
                row['roster_id'] = str(uuid.uuid4())

            csvwriter.writerow(row)


def run():    
    ###### remove old files from previous run if they exist ##########
    old_files = [cfg.asm_students_csv, cfg.asm_staff_csv, cfg.asm_courses_csv, cfg.asm_classes_csv, cfg.asm_rosters_csv, cfg.asm_locations_csv, cfg.asm_zipfile]

    for old_file in old_files:
        try:
    	    if os.path.exists(old_file):
    	        if (cfg.verbose_mode):
                    print("Removing old file " + old_file + ".") 
                    os.remove(old_file)
        except OSError as e:
            sys.exit("error:  " + old_file + " cannot be removed") 

    # Authenticate and create token files on local machine
    #get_initial_token()   # uncomment to generate new token

    # Refresh tokens using stored tokens from "get_initial_token" call above
    token_refresh_status, current_token, refresh_token = token_refresh()

    ########## LOCATIONS ##########

    with open(cfg.asm_locations_csv, 'w', encoding='utf-8') as outfile:
        filewriter = csv.writer(outfile, delimiter=',')    
        filewriter.writerow(["location_id", "location_name"])
        filewriter.writerow([cfg.asm_location, cfg.asm_location_name])

    ########## STUDENTS ##########

    # required ASM output fields for students_csv
    bblist = getapi_bblegacylist(current_token=current_token, list_id=cfg.students_list)
    mylist = create_list(bblist)
    
    students_outfieldnames = ['person_id', 'person_number', 'first_name', 'middle_name', 'last_name', 'grade_level',  'email_address', 'sis_username', 'password_policy', 'location_id']
    write_csv(mylist, cfg.asm_students_csv, students_outfieldnames)


    ########## STAFF ##########

    bblist = getapi_bblegacylist(current_token=current_token, list_id=cfg.staff_list)
    mylist = create_list(bblist)

    # required ASM output fields for staff_csv
    staff_outfieldnames = ['person_id', 'person_number', 'first_name', 'middle_name', 'last_name', 'email_address', 'sis_username', 'location_id']
    write_csv(mylist, cfg.asm_staff_csv, staff_outfieldnames)

    ########## COURSES ##########

    bblist = getapi_bblegacylist(current_token=current_token, list_id=cfg.courses_list)
    mylist = create_list(bblist)

    # required ASM output fields for courses_csv
    courses_outfieldnames = ['course_id', 'course_number', 'course_name', 'location_id']
    write_csv(mylist, cfg.asm_courses_csv, courses_outfieldnames)


    ########## CLASSES ##########

    bblist = getapi_bblegacylist(current_token=current_token, list_id=cfg.classes_list)
    mylist = create_list(bblist)

    # required ASM output fields for classes_csv
    classes_outfieldnames = ['class_id', 'class_number', 'course_id', 'instructor_id', 'instructor_id_2', 'instructor_id_3', 'location_id']
    write_csv(mylist, cfg.asm_classes_csv, classes_outfieldnames)


    ########## ROSTERS ##########

    bblist = getapi_bblegacylist(current_token=current_token, list_id=cfg.rosters_list)
    mylist = create_list(bblist)

    # required ASM output fields for rosters_csv
    rosters_outfieldnames = ['roster_id', 'class_id', 'student_id']
    write_csv(mylist, cfg.asm_rosters_csv, rosters_outfieldnames)

    ###### compress files ##########

    archive_files = [cfg.asm_students_csv, cfg.asm_staff_csv, cfg.asm_courses_csv, cfg.asm_classes_csv, cfg.asm_rosters_csv, cfg.asm_locations_csv]

    if (cfg.verbose_mode):
        print("Checking archive files.") 

    # check that all archive files exist and are not zero size
    for archive_file in archive_files:
        try:
            if os.path.getsize(archive_file) == 0:
                sys.exit("error:  " + archive_file + " is empty")
            if archive_file != 'locations.csv' and os.path.getsize(archive_file) < 1000:
                sys.exit("error:  " + archive_file + " is too small")
        except OSError as e:
            sys.exit("error:  " + archive_file + " does not exist or cannot be read") 

    if (cfg.verbose_mode):
        print("Creating compressed archive.") 

    zipout = zipfile.ZipFile(cfg.asm_zipfile, "w")
    for filename in archive_files:
        zipout.write(filename, compress_type=zipfile.ZIP_DEFLATED)
    zipout.close()

    ###### send compressed file to ASM ##########

    if cfg.sendtoasm:
        if (cfg.verbose_mode):
            print("Uploading files to ASM.") 
        transport = paramiko.Transport((cfg.sftp_dest_host, cfg.sftp_dest_port))
        transport.connect(username = cfg.sftp_dest_username, password = cfg.sftp_dest_password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(cfg.asm_zipfile, cfg.asm_zipfile)
        sftp.close()
        transport.close()


##### run the program

# define the program description
text = 'This program will populate Apple School Manager students, staff, and rosters from Blackbaud.'

# setup parser
parser = argparse.ArgumentParser(description = text)
parser.add_argument("-V", "--version", help="show program version", action="store_true")
parser.add_argument("-a", "--authorize", help="generate a new Blackbaud API token (requires user interaction)", action="store_true")
parser.add_argument("-v", "--verbose", help="verbose mode", action="store_true")


# look for arguments
args = parser.parse_args()

# print the version
if args.version:
    print("bb2asm version 0.1")
    sys.exit(0)

# enable verbose mode
if args.verbose:
    cfg.verbose_mode = True

# generate new token    
if args.authorize:
    get_initial_token()

run()
