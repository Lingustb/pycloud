import logging

# Pylon imports.
from pylons import request
from pylons.controllers.util import abort

# Controller to derive from.
from pycloud.pycloud.model import Service, ServiceVM
from pycloud.pycloud.pylons.lib.base import BaseController

# Manager to handle running instances, and logging util.
from pycloud.pycloud.utils import timelog
from pycloud.pycloud.pylons.lib.util import asjson

log = logging.getLogger(__name__)


################################################################################################################
# Class that handles Service VM related HTTP requests to a Cloudlet.
################################################################################################################
class ServiceVMController(BaseController):

    ################################################################################################################    
    # Cleans up any open resources.
    ################################################################################################################ 
    def cleanup(self):
        pass
        
    ################################################################################################################
    # Called to start a Service VM.
    # - isolated: indicates if we want to run our own Service VM (true) or if we can share an existing one ("false")
    ################################################################################################################
    @asjson
    def GET_start(self):
        # Start the Service VM on a random port.
        print '\n*************************************************************************************************'        

        # Get variables.
        sid = request.params.get('serviceId', None)
        if not sid:
            # If we didnt get a valid one, just return an error message.
            abort(400, '400 Bad Request - must provide service id')
        else:
            timelog.TimeLog.stamp("Request received: start VM with service id " + sid)

            # Check the flags that indicates whether we could join an existing instance.
            join = request.params.get('join', False)

            service = Service.by_id(sid)
            if service:
                # Get a ServiceVM instance
                svm = service.get_vm_instance(join=join)
                try:
                    # Start the instance, if it works, save it and return the svm
                    if not svm.running:
                        svm.start()
                        svm.save()
                        # Send the response.
                        timelog.TimeLog.stamp("Sending response back to " + request.environ['REMOTE_ADDR'])
                        timelog.TimeLog.writeToFile()
                    return svm
                except Exception as e:
                    # If there was a problem starting the instance, return that there was an error.
                    print 'Error starting Service VM Instance: ' + str(e)
                    abort(500, '400 Bad Request - %s' % str(e))
            else:
                abort(400, '400 Bad Request - service for %s not found' % sid)

    ################################################################################################################
    # Called to stop a running instance of a Service VM.
    ################################################################################################################
    def GET_stop(self):
        # Check that we got an instance id.
        svm_id = request.params.get('instanceId', None)
        if not svm_id:
            # If we didnt get a valid one, just return an error message.
            abort(400, '400 Bad Request - must provide instance id')
        else:
            print '\n*************************************************************************************************'
            timelog.TimeLog.reset()
            timelog.TimeLog.stamp("Request received: stop VM with instance id " + svm_id)

            # Stop the Service VM.
            try:
                svm = ServiceVM.find_and_remove(svm_id)
                if not svm:
                    abort(400, '400 Bad Request - service for %s not found' % svm_id)
                else:
                    svm.destroy()
                    timelog.TimeLog.stamp("Sending response back to " + request.environ['REMOTE_ADDR'])
                    timelog.TimeLog.writeToFile()
                    return {}
            except Exception as e:
                # If there was a problem stopping the instance, return that there was an error.
                print 'Error stopping Service VM Instance: ' + str(e)
                abort(500, '500 Internal Server Error - %s' % str(e))
