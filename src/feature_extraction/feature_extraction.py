from data_download.clients.ripe_client import RIPEClient
import tempfile
import os
from pathlib import Path
import subprocess
import sys
import concurrent.futures

class BGPFeatureExtraction:

    def __init__(self,
                 logging=False,
                 debug=False,
                 features_cache_location=False,
                 max_concurrent_threads=1,
                 ):
        
        self.logging = logging
        self.debug = debug
        self.max_concurrent_threads = int(max_concurrent_threads)

        #Checking if logging has a valid value
        if not (self.logging==False or (hasattr(self.logging, 'basicConfig') and hasattr(self.logging.basicConfig, '__call__'))):
            raise Exception('The logging parameters need to be a valid logging object or False')

        # This attribute stores the tmp_object
        self.tmp = False

        # Mapping possible cache location passed
        if (features_cache_location):
            #To-do: check if the location exists and it is writeable
            self.work_dir = features_cache_location
        else:
            #Creating a unique temp dir (when cache feature is disabled)
            with tempfile.TemporaryDirectory(prefix=f"features_") as tmp_dirname:
                # If a tmp directory will be used it will be linked 
                # in this attribute to be cleaned at the end of the execution
                self.tmp = tmp_dirname
                self.work_dir = tmp_dirname
                self.log_info(f"created temporary directory: {tmp_dirname}")
                
        # Creating the work directory if not exists
        if not os.path.exists(self.work_dir):
            self.log_info("Creating the Features directory: " + self.work_dir)
            os.makedirs(self.work_dir)

    def log_info(self, msg):
        if self.logging: self.logging.info(msg)
        if self.debug: print(msg)
    
    def log_error(self, msg):
        if self.logging: self.logging.error(msg)
        if self.debug: print(msg)
        
    def log_warning(self, msg):
        if self.logging: self.logging.warning(msg)
        if self.debug: print(msg)

    def log_debug(self, msg):
        if self.logging: self.logging.debug(msg)
        if self.debug: print(msg)

    # def cleanup(self):
    #     if self.tmp:
    #         self.log_info(f"Cleanup the tmp dir at {self.tmp}")
    #         self.tmp.cleanup()

    def create_path_if_not_exists(self,path):
        try:
            if not os.path.exists(path):
                self.log_info('Creating dir: ' + path)
                path = Path(path)
                path.mkdir(parents=True, exist_ok=True)
            return True
        except:
            self.log_error('Failure when creating the dir: ' + path)
            return False

    def extract_features_from_file(self, file_path):

        file_path_out = file_path.replace('ascii', 'features').replace('.parse', '.features')

        #Creating dir if not exists
        head, tail = os.path.split(file_path_out)
        self.create_path_if_not_exists(head)

        path_csharp_tool = os.path.dirname(os.path.abspath(__file__))
        cmd = f"mono {path_csharp_tool}/ConsoleApplication1.exe {file_path} {file_path_out}"
        #print(f"executing the command: {cmd}")
        
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.PIPE, shell=True)
            # print(cmd)
            # print(output)
        except subprocess.CalledProcessError as e:
            self.log_error(
                'Error during extracting feature file: {}. return code: {}. stderr: {}. stdout: {}.'.format(
                    file_path,
                    e.returncode,
                    e.stderr.decode(sys.getfilesystemencoding()),
                    e.output.decode(sys.getfilesystemencoding()),
                    )
            )
            self.remove_parse_file(file_path)
            return False
            # print('stdout: {}'.format())

        self.remove_parse_file(file_path)

        #Checking if the path exists
        file_path_out = f"{file_path_out}_out.txt"
        if os.path.exists(file_path_out):
            return file_path_out
        else:
            self.log_error('File with extracted features was not found in: ' + file_path_out)            

    def extract_features_from_files(self, file_paths):

        if self.max_concurrent_threads > 0:
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_threads) as executor:
                    for result in executor.map(self.extract_features_from_file, file_paths):
                        yield result
            except Exception as err:
                self.log_error(f"Error during extracting features err={err}, {type(err)=}")

    def remove_parse_file(self, parse_filepath):
        self.log_info(f"Removing parse file {parse_filepath}")
        return os.remove(parse_filepath)  
        
