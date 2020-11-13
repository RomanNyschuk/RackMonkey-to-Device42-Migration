#!/usr/bin/env python
"""
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

#############################################################################################################
# v1.0.0 of python script that connects to rackmonkey DB and migrates data to Device42 appliance using APIs
# This is for mysql based installation. Should be similar for postgres or sqlite based installations.
# Just change the DB connector for other DB types
# Required MySQLdb to be installed. Refer to README for further instructions
#############################################################################################################

import json
import csv
import requests
from requests.auth import HTTPBasicAuth

import pymysql as sql


D42_API_URL = 'https://D42_IP_or_FQDN'           # make sure to NOT to end in /
D42_USERNAME = 'D42USER'
D42_PASSWORD = 'D42PASS'

host = 'localhost'    # Hostname for RackMonkey DB. This and values below should be available in Rackmonkey config file
user = 'rackmonkey'   # Username to connect to DB
passwd = ''           # Password to connect to DB
dbname = 'rackmonkey' # DB Name

DEBUG = False

ADD_HIDDEN_RACKS = False
SEND_ROW_POS_FOR_RACK = False
HARDWARE_MODELS_ARE_ALL_RACKABLE = True
APPEND_DOMAIN_NAME_TO_DEVICE_NAME = False
ADD_ROLE_AS_CUSTOM_KEY = True
CSV_ERRORS_FILE_NAME = 'rmerrors.csv'

db = sql.connect(host=host, port=3306, db=dbname,
                 user=user, password=passwd)


def post(params, what, API_METHOD='post'):
    if what == 'device': THE_URL = D42_API_URL + '/api/device/'
    elif what == 'ip': THE_URL = D42_API_URL + '/api/ip/'
    else: THE_URL = D42_API_URL + '/api/1.0/' + what + '/'

    auth = HTTPBasicAuth(D42_USERNAME, D42_PASSWORD)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    if DEBUG: print('---REQUEST---',THE_URL)
    if DEBUG: print(headers)
    if DEBUG: print(params)
    try:
        if API_METHOD == 'put':
            r = requests.put(THE_URL, data=params, headers=headers, auth=auth, verify=False)
        else:
            r = requests.post(THE_URL, data=params, headers=headers, auth=auth, verify=False)

        if r.status_code == 200:
            msg = json.loads(str(r.text))
            return True, msg
        else:
            return False, r.status_code
    except Exception as e:
        if DEBUG: print(str(e))
        return False, str(e)

def get_table_data(table):
    the_table = []
    the_cols = []
    colunas=db.cursor()
    colunas.execute('DESCRIBE %s' % table)
    for col in colunas.fetchall():
        the_cols.append(col[0])
    dados=db.cursor()
    sql = 'SELECT %s FROM %s'
    dados.execute(sql % (','.join(the_cols), table))
    item = {}
    for row in dados.fetchall():
        item = {}
        for i in range(0,len(row)):
            item[the_cols[i]] = str(row[i]) #todo add try/except around it?
        the_table.append(item)
    return the_table

def export():
    fname = open(CSV_ERRORS_FILE_NAME, 'w')
    f=csv.writer(fname)
    the_building_object = {}
    the_room_object = {}
    the_row_object = {}
    the_rack_object = {}
    the_org_object = {}
    the_customer_object = {}
    the_service_object = {}
    the_os_object = {}
    the_hardware_object = {}
    the_domain_object = {}
    the_role_object = {}
    the_device_object = {}
    for table in ['building', 'room', 'row', 'rack', 'org', 'service', 'os', 'hardware','domain','role', 'device' ]:
        rm_data = get_table_data(table)
        if table == 'building':
            for row in  rm_data:
                added, msg = post(row, 'buildings')
                if added:
                    the_building_object[row['id']] =  msg['msg'][1]
                else: f.writerow(['add building failed', row, msg])

        elif table == 'room':
            for row in rm_data:
                row['building_id'] = the_building_object[row['building']]
                row.__delitem__('building')
                added, msg = post(row, 'rooms')
                if added:
                    the_room_object[row['id']] =  msg['msg'][1]
                else: f.writerow(['add room failed', row, msg])

        elif table == 'row': #Need to use this to get rack to room mappaing from rackmonkey
            for row in rm_data:
                the_row_object[row['id']] = the_room_object[row['room']]

        elif table == 'rack':
            for row in rm_data:
                if not ADD_HIDDEN_RACKS and row['hidden_rack'] == '1': continue
                row['room_id'] = the_row_object[row['row']]
                row.__delitem__('row')
                if SEND_ROW_POS_FOR_RACK: row['row'] = row['row_pos']
                if row['numbering_direction'] == '1': row['numbering_start_from_bottom'] = 'no'
                row['first_number'] = 1 #TODO add link to KB article here
                row['number_middle'] = 'yes'
                added, msg = post(row, 'racks')
                if added:
                    the_rack_object[row['id']] =  msg['msg'][1]
                else: f.writerow(['add rack failed', row, msg])

        elif table == 'org': #RM org will be split into customer and vendor objects in D42 depending on customer & HW/SW manfufacturer flag in RM
            for row in rm_data:
                if row['customer'] == '1':
                    added, msg = post(row, 'customers')
                    if added:
                        the_customer_object[row['id']] =  msg['msg'][1]
                    else: f.writerow(['add customer failed', row, msg])
                if row['software'] == '1' or row['hardware'] == '1': #not use elif because an org in RM can be all 3 things
                    added, msg = post(row, 'vendors')
                    if added:
                        the_org_object[row['id']] =  msg['msg'][2]  #store name
                    else: f.writerow(['add vendor failed', row, msg])

        elif table == 'service':
            for row in rm_data:
                added, msg = post(row, 'service_level')
                if added:
                    the_service_object[row['id']] = msg['msg'][2]  #store name
                else: f.writerow(['add service failed', row, msg])

        elif table == 'os':
            for row in rm_data:
                added, msg = post(row, 'operatingsystems')
                if added:
                    the_os_object[row['id']] = msg['msg'][2] #store  name
                else: f.writerow(['add os failed', row, msg])

        elif table == 'hardware':
            for row in rm_data:
                row['manufacturer'] = the_org_object[row['manufacturer']]
                if HARDWARE_MODELS_ARE_ALL_RACKABLE: row['type'] = 1
                added, msg = post(row, 'hardwares')
                if added:
                    the_hardware_object[row['id']] = msg['msg'][2] #store  name
                else: f.writerow(['add hardware failed', row, msg])

        elif table == 'domain' and APPEND_DOMAIN_NAME_TO_DEVICE_NAME:
            for row in rm_data:
                the_domain_object[row['id']] = row['name']

        elif table == 'role' and ADD_ROLE_AS_CUSTOM_KEY:
            for row in rm_data:
                 the_role_object[row['id']] = {'name': row['name'], 'notes': row['notes']} #store the dict for notes

        elif table == 'device':
            for row in rm_data:
                if APPEND_DOMAIN_NAME_TO_DEVICE_NAME:
                    row['name'] += '.' + the_domain_object[row['domain']]
                if row['in_service'] ==  '1': row['in_service'] = 'yes'
                elif row['in_service'] ==  '0': row['in_service'] = 'no'
                row['customer_id'] = the_customer_object[row['customer']]
                row.__delitem__('customer')
                if row['custom_info'] and row['custom_info'] != ''and row['custom_info'] != 'None': row['notes'] = row['notes'] + '\n' + row['custom_info']
                row['service_level'] = the_service_object[row['service']]
                row['os'] = the_os_object[row['os']]
                row['osver'] = row['os_version']
                row['hardware'] = the_hardware_object[row['hardware']]
                added, msg = post(row, 'device')
                if added:
                    the_device_object[row['id']] = msg['msg'][2] #store  name
                    if row['rack_pos'] and row['rack_pos'] != 'None' and row['rack_pos'] != '':
                        if row['rack_pos'] != '0':  #Starting position 0 in rackmonkey means the device is no longer racked.
                            devrackargs = {'device': msg['msg'][2], 'rack_id': the_rack_object[row['rack']]}
                            #if row['rack_pos'] == '0': devrackargs.update({'start_at': 'auto'})
                            devrackargs.update({'start_at': int(row['rack_pos'])}) #taking out -1
                            devrackadded, devrackmsg = post(devrackargs, 'device/rack')
                            if not devrackadded:
                                f.writerow(['add device to rack failed', devrackargs, devrackmsg])
                    if ADD_ROLE_AS_CUSTOM_KEY:
                        roleargs = {'name': msg['msg'][2],'key': 'role', 'value': the_role_object[row['role']]['name'], 'notes':the_role_object[row['role']]['notes'] }
                        roladded, rolemsg = post(roleargs, 'device/custom_field', 'put')
                        if not roladded: f.writerow(['add custom key role failed', roleargs, rolemsg])
                else: f.writerow(['add device failed', row, msg])


if __name__ == "__main__":
    export()