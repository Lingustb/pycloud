#!/usr/bin/env python
#       

# Used to check file existence and handle paths.
import os.path

# To delete folder contents and to move files.
import shutil

# To handle VMs.
from pycloud.pycloud.vm import runningvm

# To create Service VMs (from this same package).
import svm
import storedservicevm

# To get info about existing VMs (from this same package).
import svmrepository

################################################################################################################
# Representas a transient or temporary ServiceVM.
################################################################################################################
class ServiceVMInstance(object):
    
    # Prefix used to name Service VM instances.
    SERVICE_VM_INSTANCE_PREFIX = 'svm-instance'    
    
    # The id of this particular instance, which will be generate once it is started.
    instanceId = None
    
    # The id of the Service which this instance contains.
    serviceId = None
    
    # The external port in the host which will be mapped to the internal service port.
    serviceHostPort = None
    
    # The external port in the host which will be mapped to the internal SSH server port.
    sshHostPort = None
    
    # The path to the folder where the temporary folder for the transient VM should be stored.
    instancesRootFolder = None
    
    # The actual Service VM.
    serviceVM = None
    
    ################################################################################################################
    # Constructor.
    ################################################################################################################
    def __init__(self, instancesRootFolder):
        self.instancesRootFolder = instancesRootFolder       

    ################################################################################################################
    # Loads an SVM Instance object from a folder, assuming it has a VM currently running.
    # NOTE: currently this loaded instance will not store in the object the ports it has mapped. This could be 
    # retrieved from the in-memory XML descriptor, but that is not supported as of now. It won't have the service 
    # id stored yet, either.
    ################################################################################################################        
    def connectToExistingInstance(self, instanceId):
        self.instanceId = instanceId
        
        # Load information from the stored files.
        instanceStoredSVM = storedservicevm.StoredServiceVM(instanceId)
        instanceStoredSVM.loadFromFolder(self.getInstanceFolder())
        
        # Create a running VM object with the data we have (this won't be connected yet to any existing running VM).
        self.serviceVM = svm.ServiceVM(vmId=self.instanceId, 
                                       prefix=self.SERVICE_VM_INSTANCE_PREFIX, 
                                       diskImageFile=instanceStoredSVM.diskImageFilePath)
        
        # Connect to the existing VM.
        self.serviceVM.connectToRunningVM()
        
    ################################################################################################################  
    # Gets the folder where an instance will run.
    ################################################################################################################   
    def getInstanceFolder(self):
        instanceFolder = os.path.join(self.instancesRootFolder, str(self.instanceId))
        return instanceFolder        
        
    ################################################################################################################  
    # Starts a temporary instance of a Service VM, receives the Service ID, plus the external ports which will be 
    # mapped to this instance.
    ################################################################################################################   
    def createAndStart(self, cloudletConfig, serviceId, serviceHostPort, sshHostPort, showVNC=False):
        # Set internal variables.
        self.serviceId = serviceId
        self.serviceHostPort = serviceHostPort
        self.sshHostPort = sshHostPort
    
        # Get information about the VM to execute.
        serviceVmRepo = svmrepository.ServiceVMRepository(cloudletConfig)
        storedServiceVM = serviceVmRepo.findServiceVM(self.serviceId)
        if(storedServiceVM == None):
            raise svm.ServiceVMException("No valid VM for service id %s was found in the repository. " % self.serviceId)
        
        # Create a VM id for the running VM, and store it as our id.
        self.instanceId = runningvm.RunningVM.generateRandomId()
        
        # Now we create a temporary clone of the template ServiceVM, which will be our instance.
        # We don't want to store changes to the template Service VM. Therefore, we have to make a copy of the disk image and start the VM
        # with that disposable copy, in a temporary folder.
        print '\n*************************************************************************************************'        
        print "Copying Service VM files to temporary folder."
        clonedStoredVMFolderPath = os.path.join(self.instancesRootFolder, self.instanceId)
        clonedStoredServiceVM = storedServiceVM.cloneToFolder(clonedStoredVMFolderPath)        
        
        # Make the files readable and writable by all, so that libvirt can access them.
        clonedStoredServiceVM.unprotect()
        print "Service VM files copied to folder %s." % (clonedStoredServiceVM.folder)
        
        print '\n*************************************************************************************************'        
        print "Resuming VM."
        self.serviceVM = svm.ServiceVM(vmId=self.instanceId, prefix=self.SERVICE_VM_INSTANCE_PREFIX)
        self.serviceVM.startFromStoredSVM(storedVM=clonedStoredServiceVM,
                                          showVNC=showVNC,
                                          sshHostPort=self.sshHostPort,
                                          serviceHostPort=self.serviceHostPort)

        # Return our id.
        return self.instanceId
        
    ################################################################################################################  
    # Stops a running instance of a Service VM.
    ################################################################################################################  
    def stop(self):
        print "Stopping Service VM with instance id %s" % (self.instanceId)
        try:
            # Destroy the transient VM.
            print "Stopping VM with id %s" % (self.instanceId)
            self.serviceVM.destroy()
            print "VM instance with id %s was stopped and destroyed" % (self.instanceId)
        finally:
            # We get rid of the instance folder.
            instanceFolder = self.getInstanceFolder()
            if(os.path.exists(instanceFolder)):
                shutil.rmtree(instanceFolder)
                print "Temporary folder for instance of Server VM with id %s was removed" % (self.instanceId)
                
    ################################################################################################################
    # Opens an SSH session.
    ################################################################################################################       
    def openSSHConnection(self):
        self.serviceVM.openSSHConnection()        
        
    ################################################################################################################
    # Closes an SSH session.
    ################################################################################################################       
    def closeSSHConnection(self):
        self.serviceVM.closeSSHConnection()
    
    ################################################################################################################
    # Uploads a file through SFTP to a running VM.
    # NOTE: destFilePath has to be a full file path, not only a folder.
    ################################################################################################################       
    def uploadFile(self, sourceFilePath, destFilePath):
        self.serviceVM.uploadFile(sourceFilePath, destFilePath)
        
    ################################################################################################################
    # Sends a command through SSH to a running VM.
    ################################################################################################################       
    def executeCommand(self, command):       
        return self.serviceVM.executeCommand(command)