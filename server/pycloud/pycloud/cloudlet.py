__author__ = 'jdroot'

from pymongo import Connection
from pymongo.errors import ConnectionFailure
import psutil
import os
import shutil
from pycloud.pycloud.utils import portmanager
from pycloud.pycloud.vm.vmutils import destroy_all_vms
import pycloud.pycloud.mongo.model as model
import sys


# Singleton object to maintain intra- and inter-app variables.
_g_singletonCloudlet = None

################################################################################################################
# Creates the Cloudlet singleton, or gets an instance of it if it had been already created.
################################################################################################################
def get_cloudlet_instance(config=None):
    # Only create it if we don't have a reference already.
    global _g_singletonCloudlet
    if not _g_singletonCloudlet:
        print 'Creating Cloudlet singleton.'
        _g_singletonCloudlet = Cloudlet(config)

    return _g_singletonCloudlet

################################################################################################################
# Singleton that will contain common resources: config values, db connections, common managers.
################################################################################################################
class Cloudlet(object):

    ################################################################################################################
    # Constructor, should be called only once, independent on how many apps there are.
    ################################################################################################################    
    def __init__(self, config, *args, **kwargs):

        sys.stdout = Tee('pycloud.log', 'w')

        print 'Loading cloudlet configuration...'

        # DB information.
        host = config['pycloud.mongo.host']
        port = int(config['pycloud.mongo.port'])
        dbName = config['pycloud.mongo.db']

        try:
            self.conn = Connection(host, port)
        except ConnectionFailure as error:
            print error
            raise Exception('Unable to connect to MongoDB')

        self.db = self.conn[dbName]

        # Get HTTP server info.
        self.http_port = config['port']
            
        # Get information about folders to be used.
        self.svmCache = config['pycloud.servicevm.cache']
        self.svmInstancesFolder = config['pycloud.servicevm.instances_folder']
        self.appFolder = config['pycloud.push.app_folder']
        
        # Load the templates to be used when creating VMs.
        self.newVmFolder = config['pycloud.servicevm.new_folder']        
        self.newVmXml = config['pycloud.servicevm.xml_template']

        # New config params
        self.service_cache = config['pycloud.servicevm.cache']

        # Export
        self.export_path = config['pycloud.export.default']

        self.migration_enabled = config['pycloud.migration.enabled']
        self.migration_enabled = self.migration_enabled.upper() in ['T', 'TRUE', 'Y', 'YES']

        self.bridge_adapter = config['pycloud.migration.adapter']
        #self.nmap = config['pycloud.migration.nmap']

        print 'cloudlet created.'

    @staticmethod
    def system_information():
        return Cloudlet_Metadata()

    def cleanup_system(self):
        destroy_all_vms()
        self._clean_temp_folder(self.svmInstancesFolder)
        self._clean_temp_folder(self.newVmFolder)
        self._remove_service_vms()
        portmanager.PortManager.clearPorts()
        if not os.path.exists(self.export_path):
            os.makedirs(self.export_path)
        if not os.path.exists(self.appFolder):
            os.makedirs(self.appFolder)

    def _clean_temp_folder(self, folder):
        print 'Cleaning up \'%s\'' % folder
        if os.path.exists(folder):
            print '\tDeleting all files in \'%s\'' % folder
            shutil.rmtree(folder)
        if not os.path.exists(folder):
            print '\tMaking folder \'%s\'' % folder
            os.makedirs(folder)
        print 'Done cleaning up \'%s\'' % folder

    def _remove_service_vms(self):
        from pycloud.pycloud.model import ServiceVM
        ServiceVM._collection.drop()


class Cpu_Info(model.AttrDict):

    def __init__(self):
        self.max_cores = psutil.cpu_count()
        self.usage = psutil.cpu_percent(interval=0.1)

        cpu_info = cpuinfo()
        self.speed = cpu_info['cpu MHz']
        self.cache = int(cpu_info['cache size'].split()[0])    # In KBs, per core.

class Memory_Info(model.AttrDict):

    def __init__(self):
        mem = psutil.virtual_memory()
        self.max_memory = mem.total
        self.free_memory = mem.free


class Cloudlet_Metadata(model.AttrDict):

    def __init__(self):
        self.memory_info = Memory_Info()
        self.cpu_info = Cpu_Info()


class Tee(object):

    def __init__(self, name, mode):
        self.file = open(name, mode)
        self.stdout = sys.stdout

    def __del__(self):
        self.file.close()

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)


from collections import OrderedDict

##########################################################################################
# Returns info about the first processor. Assumes if multiprocessor, all cores are equal.
##########################################################################################
def cpuinfo():
    procinfo = OrderedDict()

    with open('/proc/cpuinfo') as f:
        for line in f:
            if not line.strip():
                # End of one processor
                break
            else:
                if len(line.split(':')) == 2:
                    procinfo[line.split(':')[0].strip()] = line.split(':')[1].strip()
                else:
                    procinfo[line.split(':')[0].strip()] = ''

    return procinfo