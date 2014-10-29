import logging
import json
import time
import os.path

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons import g

from webhelpers.html.grid import Grid
from webhelpers.html import HTML
from webhelpers.html import literal

from pycloud.pycloud.pylons.lib.base import BaseController
from pycloud.manager.lib.pages import InstancesPage
from pycloud.pycloud.pylons.lib import helpers as h
from pycloud.pycloud.model import Service, ServiceVM
from pycloud.pycloud.pylons.lib.util import asjson
from pycloud.pycloud.pylons.lib.util import dumps

log = logging.getLogger(__name__)

################################################################################################################
# Controller for the ServiceVMs Instances page.
################################################################################################################
class InstancesController(BaseController):

    JSON_OK = {"STATUS" : "OK" }
    JSON_NOT_OK = { "STATUS" : "NOT OK"}
    
    ############################################################################################################
    # Shows the list of running Service VM instances.
    ############################################################################################################
    def GET_index(self):
        # Mark the active tab.
        c.servicevms_active = 'active'

        svms = ServiceVM.find()

        grid_items = []
        for svm in svms:
            grid_items.append(
                {
                    'svm_id': svm['_id'],
                    'service_id': svm.service_id,
                    'service_external_port': svm.port,
                    'ssh_port': svm.ssh_port,
                    'vnc_port': svm.vnc_port,
                    #'folder': os.path.dirname(svm.vm_image.disk_image),
                    'action': 'Stop'
                }
            )

        # Create and format the grid.
        instancesGrid = Grid(grid_items, ['svm_id', 'service_id', 'service_external_port', 'ssh_port', 'vnc_port', 'action'])
        instancesGrid.column_formats["service_id"] = generate_service_id_link
        instancesGrid.column_formats["action"] = generate_action_buttons

        # Pass the grid and render the page.
        instancesPage = InstancesPage()
        instancesPage.instancesGrid = instancesGrid
        return instancesPage.render()
        
    ############################################################################################################
    # Opens a local VNC window to a running Service VM Instance.
    ############################################################################################################
    def GET_openVNC(self, id):
        try:            
            # Get the instance associated with this id.
            svm = ServiceVM.by_id(id)
            
            if not svm:
                # If we didn't get a valid id, just return an error message.
                print "Service VM id " + id + " was not found on the list of running instances."
                return dumps(self.JSON_NOT_OK)       
            
            # Try to start the VNC window (this will only work if done on the Cloudlet).
            svm.open_vnc(wait=False)
        except Exception as e:        
            # If there was a problem connecting through VNC, return that there was an error.
            print 'Error opening VNC window: ' + str(e);
            return dumps(self.JSON_NOT_OK)  
        
        # Everything went well.
        return dumps(self.JSON_OK)

    ############################################################################################################
    # Starts a new SVM instance of the Service.
    ############################################################################################################
    @asjson
    def GET_startInstance(self, id):
        # Look for the service with this id
        service = Service.by_id(id)
        if service:
            clone_full_image = False
            if request.params.get('clone_full_image'):
                clone_full_image = True

            # Get a ServiceVM instance
            svm = service.get_vm_instance(clone_full_image=clone_full_image)
            try:
                # Start the instance, if it works, save it and return ok
                svm.start()
                svm.save()
                return {"STATUS": "OK", "SVM_ID": svm._id, "VNC_PORT": svm.vnc_port}
            except Exception as e:
                # If there was a problem starting the instance, return that there was an error.
                print 'Error starting Service VM Instance: ' + str(e)
                return self.JSON_NOT_OK
        else:
            error = self.JSON_NOT_OK
            error['message'] = 'Service {} not found.'.format(id)
            return error

    ############################################################################################################
    # Stops an existing instance.
    ############################################################################################################
    def GET_stopInstance(self, id):
        try:    
            # Stop an existing instance with the given ID.
            svm = ServiceVM.find_and_remove(id)
            svm.destroy()
        except Exception as e:
            # If there was a problem stopping the instance, return that there was an error.
            print 'Error stopping Service VM Instance: ' + str(e)
            return dumps(self.JSON_NOT_OK)               
        
        # Everything went well.
        return dumps(self.JSON_OK)

    ############################################################################################################
    # Command to migrate a machine.
    ############################################################################################################
    def GET_migrateInstance(self, id):
        import libvirt
        local_uri ='qemu:///session'
        remote_uri = 'qemu://twister/session'
        stratus = libvirt.open(local_uri)
        twister = libvirt.open(remote_uri)
        print 'Stratus: ' + str(stratus)
        print 'Twister: ' + str(twister)

        print id
        vm = stratus.lookupByUUIDString(id)
        # svm = ServiceVM.Service.by_id(id)
        print 'VM found: ' + str(vm)

        # We first pause the VM.
        # svm.pause()
        result = vm.suspend()
        if result == -1:
            raise Exception("Cannot pause VM: %s", str(id))

        # Transfer the disk image file.

        # Prepare basic flags.
        # svm.migrate()
        flags = libvirt.VIR_MIGRATE_NON_SHARED_DISK | libvirt.VIR_MIGRATE_PAUSED
        bandwidth = 0

        # Set flags that depend on migration type.
        p2p = False
        if p2p:
            flags = flags | libvirt.VIR_MIGRATE_PEER2PEER
            uri = 'tcp://twister'
        else:
            uri = remote_uri

        # Migrate the state and memory.
        vm.migrate(twister, flags, id, uri, bandwidth)

        return 'OK!'
    
    ############################################################################################################
    # Returns a list of running svms.
    ############################################################################################################    
    @asjson    
    def GET_svmList(self):
        try:    
            # Get the list of running instances.
            svm_list = ServiceVM.find()
            return svm_list
        except Exception as e:
            # If there was a problem stopping the instance, return that there was an error.
            print 'Error getting list of instance changes: ' + str(e);
            return self.JSON_NOT_OK

############################################################################################################
# Helper function to generate a link for the service id to the service details.
############################################################################################################        
def generate_service_id_link(col_num, i, item):
    editServiceURL = h.url_for(controller='modify', action='index', id=item["service_id"])
    
    return HTML.td(HTML.a(item["service_id"], href=editServiceURL))   

############################################################################################################
# Helper function to generate actions for the service vms (stop and vnc buttons).
############################################################################################################        
def generate_action_buttons(col_num, i, item):
    # Button to stop an instance.
    stopUrl = h.url_for(controller='instances', action='stopInstance', id=item["svm_id"])
    stopButtonHtml = HTML.button("Stop", onclick=h.literal("stopSVM('"+ stopUrl +"')"), class_="btn btn-primary btn")

    # Button to open VNC window.
    vncUrl = h.url_for(controller='instances', action='openVNC', id=item["svm_id"])
    vncButtonHtml = HTML.button("Open VNC (on server)", onclick=h.literal("openVNC('"+ vncUrl +"')"), class_="btn btn-primary btn")

    # Button to migrate.
    migrateUrl = h.url_for(controller='instances', action='migrateInstance', id=item["svm_id"])
    migrateButtonHtml = HTML.button("Migrate", onclick=h.literal("window.location.href='" + migrateUrl + "'"), class_="btn btn-primary btn")

    # Render the buttons with the Ajax code to stop the SVM.    
    return HTML.td(stopButtonHtml + literal("&nbsp;") + vncButtonHtml + literal("&nbsp;") + migrateButtonHtml)
