[Device42](http://www.device42.com/) is a comprehensive data center inventory management and IP Address management software that integrates centralized password management, impact charts and applications mappings with IT asset management.

This repository contains sample script to take Inventory information from a RackMonkey install and send it to Device42 appliance using the REST APIs.

## Assumptions
-----------------------------
    * The script assumes that you are running Rackmonkey v1.2.5-1
    * This has connector for MySQL DB, assuming you are using Mysql. You can change that to SQLlite or postgres, if that is what you are using.
    * This script works with Device42 v5.7.1.1394099009 and above

### Requirements
-----------------------------
    * python 2.7.x
    * MySQLdb (which you can install with sudo pip install MySQL-python

### Usage
-----------------------------
    * add D42 URL/credentials
    * add rackmonkey DB info/credentials
    * adjust any settings as set on the top
    * Run the script and enjoy!
    * If you have any questions - feel free to reach out to us at support at device42.com



*Detailed Instructions:*
[Migrating RackMonkey data to Device42](http://blog.device42.com/2014/03/migrating-rackmonkey-data-to-device42/)