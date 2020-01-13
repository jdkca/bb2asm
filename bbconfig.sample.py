from pathlib import Path

######## CONFIGURATION ########

# Look here https://developer.blackbaud.com/apps/ to get following codes
CLIENT_ID = 'YOUR_APPLICATION_ID'  # application ID
CLIENT_SECRET = 'YOUR_APPLICATION_SECRET'  # application secret
SUBSCRIPTION_KEY = r'YOUR_PRIMARY_ACCESS_KEY'  # primary access key

# We'll store our tokens in local files; specify file locations below
TOKEN_FILE = Path(f'/var/www/scripts/bb2asm/SKYApi_Token.txt')
REFRESH_TOKEN_FILE = Path(f'/var/www/scripts/bb2asm/SKYApi_Refresh_Token.txt')

# List IDs from Blackbaud
staff_list = '86478'
students_list = '86476'
classes_list = '86475'
courses_list = '86599'
rosters_list = '86497'

# send processed files to Apple School Manager sftp server
sendtoasm = True

# Apple School Manager Location ID and Name
asm_location = 1
asm_location_name = 'SFTP'

# ASM destination sftp information (configure if sendtoasm is True)
sftp_dest_host = "upload.appleschoolcontent.com"
sftp_dest_port = 22
sftp_dest_username = "YOUR_USERNAME@sftp.apple.com"
sftp_dest_password = "YOUR_PASSWORD"

# ASM Destination CSV Files 
asm_locations_csv = 'locations.csv'
asm_students_csv = 'students.csv'
asm_staff_csv = 'staff.csv'
asm_courses_csv = 'courses.csv'
asm_classes_csv = 'classes.csv'
asm_rosters_csv = 'rosters.csv'
asm_locations_csv = 'locations.csv'
asm_zipfile = 'ASM_CSV_Templates.zip'

# You probably will not need to change these
CALLBACK_URI = r'https://127.0.0.1'
AUTHORIZE_URL = "https://oauth2.sky.blackbaud.com/authorization"
TOKEN_URL = "https://oauth2.sky.blackbaud.com/token"

AUTHORIZATION = f'Basic {CLIENT_ID}:{CLIENT_SECRET}'

# verbose mode is disabled by default
verbose_mode = False

######## END CONFIGURATION ########

