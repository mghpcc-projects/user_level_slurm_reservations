"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

HIL Client Interface

August 2017, Tim Donahue	tpd001@gmail.com
"""

import urllib

from hil.client.client import Client, RequestsHTTPClient
from hil.client.base import FailedAPICallException

from hil_slurm_logging import log_info, log_debug, log_error
from hil_slurm_settings import HIL_ENDPOINT, HIL_USER, HIL_PW


def hil_client_connect(endpoint_ip, name, pw):
    '''
    '''
    hil_http_client = RequestsHTTPClient()
    hil_http_client.auth = (name, pw)

    return Client(endpoint_ip, hil_http_client)


def hil_client_close(hilc):
    pass

def check_hil_interface(hilc):
    pass

def hil_reserve_nodes(hilc, nodelist):
    '''
    Cause HIL nodes to move from the Slurm loaner project tot he HIL free poool.
    '''
    for node in nodelist:
        
    pass

def hil_free_nodes(hilc, nodelist):
    pass


def hil_init():
    hilc = hil_client_connect(HIL_ENDPOINT, HIL_USER, HIL_PW)
    


# EOF


    
